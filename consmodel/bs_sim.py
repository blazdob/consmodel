"""
Module Docstring

This module contains the BS class.
"""

import warnings
from scipy import optimize
import pandas as pd
import numpy as np
from consmodel.utils.st_types import StorageType
from consmodel.base_model import BaseModel
from consmodel.utils import individual_tariff_times, extract_first_date_of_month


from numba import njit


@njit
def jit_are_p_limits_possible(p_array, block_array, p_limits, current_e, max_charge, max_discharge, max_e, dt):
    n = p_array.shape[0]
    # Initialize a variable to hold the battery state (you may want an array if you need the entire state history)
    for i in range(n):
        # Get the relevant p_limit for this row (e.g., based on block)
        current_p_limit = p_limits[int(block_array[i]) - 1]
        if p_array[i] > current_p_limit:
            if current_e >= 0:
                if p_array[i] - current_p_limit > max_discharge:
                    return -1
                needed_output = p_array[i] - current_p_limit
                if current_e < needed_output * dt:
                    return -1
                current_e -= needed_output * dt
            else:
                return -1
        else:
            diff = current_p_limit - p_array[i]
            charge_amount = diff if diff < max_charge else max_charge
            if current_e < max_e:
                if current_e + charge_amount * dt > max_e:
                    charge_amount = (max_e - current_e) / dt
                current_e += charge_amount * dt
    return 1

from numba import njit
import numpy as np

@njit
def jit_is_p_limit_possible(p_array, p_limit, current_e, max_charge, max_discharge, max_e, dt):
    """
    Determine if a single p_limit is possible, updating current_e along the way.
    Returns 1 if possible, otherwise -1.
    """
    n = p_array.shape[0]
    for i in range(n):
        if p_array[i] > p_limit:
            # battery must discharge
            if current_e >= 0:
                if p_array[i] - p_limit > max_discharge:
                    return -1
                needed_output = p_array[i] - p_limit
                if current_e < needed_output * dt:
                    return -1
                current_e -= needed_output * dt
            else:
                return -1
        else:
            # battery can be charged
            diff = p_limit - p_array[i]
            # choose the smaller of the available difference or max_charge
            charge_amount = diff if diff < max_charge else max_charge
            if current_e < max_e:
                if current_e + charge_amount * dt > max_e:
                    charge_amount = (max_e - current_e) / dt
                current_e += charge_amount * dt
    return 1

from numba import njit
import numpy as np

@njit
def jit_simulate_p_limit(p_array, p_limit_array, dt, init_e, max_e, max_charge, max_discharge):
    """
    Simulate battery behavior over a time series for p_limit control.
    
    Parameters:
      p_array       : 1D array of power values (kW) at each timestep.
                      Positive values mean consumption.
      p_limit_array : 1D array of p_limit values for each timestep.
      dt            : Time step in hours (e.g. 0.25 for 15 minutes).
      init_e        : Initial battery energy (kWh).
      max_e         : Maximum battery capacity (kWh).
      max_charge    : Maximum charging power (kW).
      max_discharge : Maximum discharging power (kW).
      
    Returns:
      battery_plus  : 1D array of discharge amounts (kW) at each timestep.
      battery_minus : 1D array of charge amounts (kW) at each timestep.
                      (Stored as positive values; caller can add sign if needed.)
      energy_state  : 1D array of battery energy (kWh) after each timestep.
    """
    n = p_array.shape[0]
    battery_plus = np.zeros(n)
    battery_minus = np.zeros(n)
    energy_state = np.empty(n)
    current_e = init_e
    
    for i in range(n):
        if p_array[i] > p_limit_array[i]:
            # Discharging scenario (consumption exceeds limit)
            if current_e > 0:
                # Determine how much we can discharge this timestep.
                discharge_amount = p_array[i] - p_limit_array[i]
                if discharge_amount > max_discharge:
                    discharge_amount = max_discharge
                # If battery doesn't have enough energy for full discharge:
                if current_e < discharge_amount * dt:
                    discharge_amount = current_e / dt  # equivalent to current_e * (1/dt)
                current_e -= discharge_amount * dt
                battery_plus[i] = discharge_amount
            else:
                battery_plus[i] = 0.0
        else:
            # Charging scenario (available production exceeds consumption)
            excess_power = p_limit_array[i] - p_array[i]
            if current_e < max_e:
                charge_amount = excess_power
                if charge_amount > max_charge:
                    charge_amount = max_charge
                # Prevent overcharging:
                if current_e + charge_amount * dt > max_e:
                    charge_amount = (max_e - current_e) / dt
                current_e += charge_amount * dt
                battery_minus[i] = charge_amount
            else:
                battery_minus[i] = 0.0
        energy_state[i] = current_e
    return battery_plus, battery_minus, energy_state

@njit
def jit_simulate_MT_VT_shift(hours, dt, init_e, max_e, max_charge, max_discharge):
    """
    Simulate the battery behavior for MT/VT shifting.
    
    For hours <= 5 or >= 22 (i.e. nighttime) the battery charges:
      charge_amount = min( max_e/8, (max_e - current_e)*4, max_charge )
      current_e is increased by (charge_amount * dt)
      
    For hours between 6 and 21 (daytime) the battery discharges:
      discharge_amount = min( max_e/16, (current_e)*4, max_discharge )
      current_e is decreased by (discharge_amount * dt)
      
    Parameters:
      hours       : 1D NumPy array of hour values for each timestep.
      dt          : Time step in hours (e.g. 0.25 for 15 minutes).
      init_e      : Initial battery energy (kWh).
      max_e       : Maximum battery capacity (kWh).
      max_charge  : Maximum charging power (kW).
      max_discharge: Maximum discharging power (kW).
      
    Returns:
      battery_plus  : Array of discharge amounts (kW) at each timestep.
      battery_minus : Array of charge amounts (kW) at each timestep.
                      (Positive values; caller may assign a negative sign as needed.)
      energy_state  : Array of battery energy (kWh) after each timestep.
    """
    n = hours.shape[0]
    battery_plus = np.zeros(n)
    battery_minus = np.zeros(n)
    energy_state = np.empty(n)
    current_e = init_e

    for i in range(n):
        hr = hours[i]
        if hr <= 5 or hr >= 22:
            # Nighttime: charge the battery
            # Compute candidate charge: max_e/8 and (max_e - current_e)*4
            charge_amt = max_e / 8
            cand = (max_e - current_e) * 4
            if cand < charge_amt:
                charge_amt = cand
            if max_charge < charge_amt:
                charge_amt = max_charge
            current_e = current_e + charge_amt * dt
            battery_minus[i] = charge_amt
        else:
            # Daytime: discharge the battery
            discharge_amt = max_e / 16
            cand = current_e * 4
            if cand < discharge_amt:
                discharge_amt = cand
            if max_discharge < discharge_amt:
                discharge_amt = max_discharge
            current_e = current_e - discharge_amt * dt
            battery_plus[i] = discharge_amt
        energy_state[i] = current_e
    return battery_plus, battery_minus, energy_state

@njit
def jit_simulate_5tariff(hours, dt, init_e, max_e, max_charge, max_discharge):
    """
    Simulate battery behavior for the 5Tariff_manoeuvering control strategy.
    
    For hours <= 5 or >= 22:
      n_hours = 8, so candidate charge = min(max_e/8, (max_e - current_e)*4, max_charge)
    For hours between 7 and 13:
      n_hours = 7, so candidate discharge = min(max_e/7, current_e*4, max_discharge)
    For hours 14 or 15:
      n_hours = 2, so candidate charge = min(max_e/2, (max_e - current_e)*4, max_charge)
    For hours between 16 and 19:
      n_hours = 4, so candidate discharge = min(max_e/4, current_e*4, max_discharge)
    Otherwise (e.g. between 5 and 7, or 20–21):
      no battery operation is performed.
      
    Parameters:
      hours      : 1D array of integer hour values for each timestep.
      dt         : Time step in hours (e.g. 0.25 for 15 minutes).
      init_e     : Initial battery energy (kWh).
      max_e      : Maximum battery capacity (kWh).
      max_charge : Maximum charging power (kW).
      max_discharge: Maximum discharging power (kW).
      
    Returns:
      battery_plus  : Array of discharge amounts (kW) at each timestep.
      battery_minus : Array of charge amounts (kW) at each timestep.
                      (Positive numbers; caller should negate for storage if needed.)
      energy_state  : Array of battery energy (kWh) after each timestep.
    """
    n = hours.shape[0]
    battery_plus = np.zeros(n)
    battery_minus = np.zeros(n)
    energy_state = np.empty(n)
    current_e = init_e

    for i in range(n):
        hr = hours[i]
        if hr <= 5 or hr >= 22:
            # Nighttime: charge the battery
            n_hours = 8.0
            charge_amt = max_e / n_hours
            # Adjust charge candidate by available headroom:
            available = (max_e - current_e) * 4.0
            if available < charge_amt:
                charge_amt = available
            if max_charge < charge_amt:
                charge_amt = max_charge
            # Update battery state:
            current_e = current_e + charge_amt * dt
            battery_minus[i] = charge_amt
        elif hr >= 7 and hr <= 13:
            # Morning: discharge the battery
            n_hours = 7.0
            discharge_amt = max_e / n_hours
            available = current_e * 4.0
            if available < discharge_amt:
                discharge_amt = available
            if max_discharge < discharge_amt:
                discharge_amt = max_discharge
            current_e = current_e - discharge_amt * dt
            battery_plus[i] = discharge_amt
        elif hr == 14 or hr == 15:
            # Early afternoon: charge the battery
            n_hours = 2.0
            charge_amt = max_e / n_hours
            available = (max_e - current_e) * 4.0
            if available < charge_amt:
                charge_amt = available
            if max_charge < charge_amt:
                charge_amt = max_charge
            current_e = current_e + charge_amt * dt
            battery_minus[i] = charge_amt
        elif hr >= 16 and hr <= 19:
            # Late afternoon: discharge the battery
            n_hours = 4.0
            discharge_amt = max_e / n_hours
            available = current_e * 4.0
            if available < discharge_amt:
                discharge_amt = available
            if max_discharge < discharge_amt:
                discharge_amt = max_discharge
            current_e = current_e - discharge_amt * dt
            battery_plus[i] = discharge_amt
        else:
            # For other hours (e.g., between 5 and 7, or 20-21), do nothing.
            pass

        energy_state[i] = current_e
    return battery_plus, battery_minus, energy_state

@njit
def jit_simulate_production_saving(p_array, dt, init_e, max_e, max_charge, max_discharge):
    """
    Simulate battery behavior for production saving control.
    
    Parameters:
      p_array    : 1D array of power values (kW) at each timestep.
                   (Positive values represent consumption.)
      dt         : Time step in hours.
      init_e     : Initial battery energy (kWh).
      max_e      : Maximum battery capacity (kWh).
      max_charge : Maximum charging power (kW).
      max_discharge: Maximum discharging power (kW).
    
    Returns:
      battery_plus  : Array of discharge amounts (kW) at each timestep.
      battery_minus : Array of charge amounts (kW) at each timestep.
                      (Positive values; production saving stores charging as a negative effect.)
      energy_state  : Array of battery energy (kWh) after each timestep.
    """
    n = p_array.shape[0]
    battery_plus = np.zeros(n)
    battery_minus = np.zeros(n)
    energy_state = np.empty(n)
    current_e = init_e
    
    for i in range(n):
        p = p_array[i]
        if p > 0:
            # Consumption: discharge battery
            if current_e > 0:
                # If enough energy for full discharge:
                if current_e - dt * p > 0:
                    discharge_amt = p if p < max_discharge else max_discharge
                else:
                    discharge_amt = max_discharge if max_discharge < 4 * current_e else 4 * current_e
                current_e = current_e - discharge_amt * dt
                battery_plus[i] = discharge_amt
            else:
                battery_plus[i] = 0.0
        else:
            # Production: p is negative; charge battery
            available_power = -p
            if current_e + dt * available_power < max_e:
                charge_amt = available_power if available_power < max_charge else max_charge
            else:
                charge_amt = (max_e - current_e) / dt
                if charge_amt > max_charge:
                    charge_amt = max_charge
            current_e = current_e + charge_amt * dt
            battery_minus[i] = charge_amt
        energy_state[i] = current_e
    return battery_plus, battery_minus, energy_state

class BS(BaseModel):
    """
    Class to represent a battery.

    Attributes
    ----------
    index : int
        Unique identifier.
    name : str
        Name of the battery.
    st_type : str
        Storage type.
    max_charge_p_kw : float
        Maximum charging power in kW.
    max_discharge_p_kw : float
        Maximum discharging power in kW.
    max_e_kwh : float
        Maximum energy in kWh.
    soc : float
        State of charge.

    Methods
    -------
    charge(p_kw, dt)
        Charge the battery.
    discharge(p_kw, dt)
        Discharge the battery.
    """

    def __init__(
        self,
        lat,
        lon,
        alt,
        index: int = 0,
        name: str = "BS_default",
        tz: str = None,
        use_utc: bool = False,
        st_type: str = None,
        max_charge_p_kw: float = 1.,
        max_discharge_p_kw: float = 1.,
        max_e_kwh: float = 1.,
        soc: float = 1.,
        freq: str = "15min",
    ):
        super().__init__(index, lat, lon, alt, name, tz, use_utc, freq)

        if st_type is None:
            self._index = index
            self._name = name
            self._max_e_kwh = float(max_e_kwh)
            self._max_charge_p_kw = float(max_charge_p_kw)
            if max_discharge_p_kw is None:
                self.max_discharge_p_kw = float(max_charge_p_kw)
            else:
                self.max_discharge_p_kw = float(max_discharge_p_kw)
        else:
            storage_type = StorageType(st_type)
            self._index = index
            self._name = storage_type.name
            self._max_charge_p_kw = storage_type.max_charge_p_kw
            self._max_discharge_p_kw = storage_type.max_discharge_p_kw
            self._max_e_kwh = storage_type.max_e_kwh

        self._soc = soc
        self._current_p_kw = 0
        self._current_e_kwh = self.max_e_kwh * soc

        self.charge_amount = 0.
        self.discharge_amount = 0.
        self.curr_limit = 0.
        self.p_limits = []

    def __repr__(self):
        return f"BS model(index={self.index}, name={self.name})"

    def __str__(self):
        return f"BS model(index={self.index}, name={self.name})"

    # Properties
    @property
    def index(self):
        return self._index

    @property
    def name(self):
        return self._name

    @property
    def max_charge_p_kw(self):
        return self._max_charge_p_kw

    @property
    def max_discharge_p_kw(self):
        return self._max_discharge_p_kw

    @property
    def max_e_kwh(self):
        return self._max_e_kwh

    @property
    def soc(self):
        return self._soc

    @property
    def current_p_kw(self):
        return self._current_p_kw

    @property
    def current_e_kwh(self):
        return self._current_e_kwh

    #__________________________________________________________________________
    # Setters
    #__________________________________________________________________________

    @index.setter
    def index(self, index):
        self._index = index

    @name.setter
    def name(self, name):
        self._name = name

    @soc.setter
    def soc(self, soc):
        if not isinstance(soc, float):
            raise TypeError("SOC has to be a float.")
        if soc < 0 or soc > 1:
            raise ValueError("SOC has to be between 0 and 1.")
        self._soc = soc

    @max_charge_p_kw.setter
    def max_charge_p_kw(self, max_charge_p_kw):
        if not isinstance(max_charge_p_kw, float):
            raise TypeError("Max_charge_p_kw has to be a float.")
        if max_charge_p_kw < 0:
            raise ValueError("Max_charge_p_kw has to be positive.")
        self._max_charge_p_kw = max_charge_p_kw

    @max_discharge_p_kw.setter
    def max_discharge_p_kw(self, max_discharge_p_kw):
        # has to be positive
        if not isinstance(max_discharge_p_kw, float):
            raise TypeError("Max_discharge_p_kw has to be a float.")
        if max_discharge_p_kw < 0:
            raise ValueError("Max_discharge_p_kw has to be positive.")
        self._max_discharge_p_kw = max_discharge_p_kw

    @max_e_kwh.setter
    def max_e_kwh(self, max_e_kwh):
        if not isinstance(max_e_kwh, float):
            raise TypeError("Max_e_kwh has to be a float.")
        if max_e_kwh <= 0:
            raise ValueError("Max_e_kwh has to be positive.")
        self._max_e_kwh = max_e_kwh

    @current_p_kw.setter
    def current_p_kw(self, current_p_kw):
        if not isinstance(current_p_kw, float):
            raise TypeError("Current_p_kw has to be a float.")
        if current_p_kw < -self.max_discharge_p_kw or current_p_kw > self.max_charge_p_kw:
            raise ValueError(
                f"Current_p_kw must be between -{self.max_discharge_p_kw} and {self.max_charge_p_kw}."
            )
        self._current_p_kw = current_p_kw

    @current_e_kwh.setter
    def current_e_kwh(self, current_e_kwh):
        if not isinstance(current_e_kwh, float):
            raise TypeError("current_e_kwh has to be a float.")
        if current_e_kwh < 0 or current_e_kwh > self.max_e_kwh:
            raise ValueError(
                f"current_e_kwh must be between 0 and {self.max_e_kwh}.")
        self._current_e_kwh = current_e_kwh

    #__________________________________________________________________________
    # Methods
    #__________________________________________________________________________

    def __repr__(self):
        return f"Battery(index={self.index}, name={self.name}, max_charge_p_kw={self.max_charge_p_kw}, max_discharge_p_kw={self.max_discharge_p_kw}, max_e_kwh={self.max_e_kwh}, soc={self.soc}, current_p_kw={self.current_p_kw}, remaining_e_kwh={self.current_e_kwh})"

    def charge(self, p_kw: float, dt: float):
        """
        Charge the battery.

        Parameters
        ----------
        p_kw : float
            Power in kW.
        dt : float
            Time in hours.
        """
        if self.current_e_kwh + (p_kw * dt) <= self.max_e_kwh:
            self.current_p_kw = p_kw
            self.current_e_kwh += p_kw * dt
        else:
            # give a warning that the battery can not be charged more
            try:
                self.current_p_kw = (self.max_e_kwh - self.current_e_kwh) / dt
            except ZeroDivisionError:
                # Handle division by zero error here
                self.current_p_kw = 0.
            self.current_e_kwh = self.max_e_kwh
            # raise warning
            warnings.warn(
                "Battery can not be charged for {} kW for {} hours as it has reached full capacity. \n The battery has been charged to full capacity"
                .format(p_kw, dt))
        self.soc = self.current_e_kwh / self.max_e_kwh

    def discharge(self, p_kw: float, dt: float):
        """
        Discharge the battery.

        Parameters
        ----------
        p_kw : float
            Power in kW.
        dt : float
            Time in hours.
        """
        if self.current_e_kwh - p_kw * dt >= 0:
            self.current_p_kw = p_kw
            self.current_e_kwh -= p_kw * dt
        else:
            # give a warning that the battery can not be discharged more
            self.current_p_kw = self.current_e_kwh / dt
            self.current_e_kwh = 0.
            # raise warning
            warnings.warn(
                f"Battery can not be discharged for {p_kw} kW for {dt} hours as it has reached empty capacity. \n The battery has been discharged to empty capacity"
            )
        self.soc = self.current_e_kwh / self.max_e_kwh

    def model(self,
              control_type: str = "production_saving",
              p_kw: pd.DataFrame = None):
        """
        Model the controller and run it.

        Parameters
        ----------
        control_type : str
            control_type of simulation, where options are "production_saving", block_power_reduction and "installed_power".
        p_kw : pd.DataFrame
            Power in kW in 15 min intervals where the index is the timestamp.
            in a format:
            |      Timestamp      |     p      |
            |---------------------|------------|
            | 2020-01-01 00:00:00 |    0.0     |
            | 2020-01-01 00:15:00 |    0.0     |
            |         ...         |    ...     |
        """
        if p_kw is None:
            raise ValueError(
                "We need a timeseries data to simulate the battery.")
        lst = []
        self.results = p_kw
        self.results["battery_plus"] = 0.
        self.results["battery_minus"] = 0.
        if control_type == "production_saving":
            dt = 0.25  # 15-minute interval in hours
            p_array = self.results["p"].values.astype(np.float64)
            init_e = self.current_e_kwh
            battery_plus, battery_minus, energy_state = jit_simulate_production_saving(
                p_array, dt, init_e, self.max_e_kwh,
                self.max_charge_p_kw, self.max_discharge_p_kw
            )
            self.results["battery_plus"] = battery_plus
            # Note: production saving typically subtracts charging (so store negative)
            self.results["battery_minus"] = -battery_minus
            self.results["p_after"] = self.results["p"] - battery_plus - (-battery_minus)
            self.results["var_bat"] = energy_state
            self.current_e_kwh = energy_state[-1]
            lst = list(energy_state)
        elif control_type == "installed_power":
            p_limit = round(self.get_min_p_lim(), 1)
            self.results["p_limit"] = p_limit
            self.curr_limit = p_limit
            lst = self.simulate_p_limit()
        elif control_type == "block_power_reduction":
            # Find installed power limits for every block      
            dates = np.array(list(self.results.index))
            tariffs = individual_tariff_times(dates)
            blocks = np.argmax(tariffs, axis=0) + 1 
            self.results["block"] = blocks
            self.p_limits = self.find_p_limits()
            self.results["p_limit"] = 0
            for block in range(1, 6):
                self.results.loc[self.results.block == block, "p_limit"] = self.p_limits[block-1]
            lst = self.simulate_p_limit()
        elif control_type == "monthly_block_power_reduction":
            dates = np.array(list(self.results.index))
            tariffs = individual_tariff_times(dates)
            blocks = np.argmax(tariffs, axis=0) + 1 
            self.results["block"] = blocks
            first_dates = extract_first_date_of_month(self.results)
            self.results["p_limit"] = 0
            for date in first_dates:
                month_df = self.results[(((self.results.index- pd.Timedelta(minutes= 15)).month ) == date.month) & ((self.results.index- pd.Timedelta(minutes= 15)).year == date.year)]
                self.p_limits = self.find_p_limits(month_df = month_df)               
                for block in range(1, 6):
                    self.results.loc[((self.results.index- pd.Timedelta(minutes=15)).month == date.month) & ((self.results.index- pd.Timedelta(minutes=15)).year == date.year) & (self.results.block == block), "p_limit"] = self.p_limits[block-1]
            lst = self.simulate_p_limit()
        if control_type == "MT_VT_shifting":
            dt = 0.25  # time step in hours
            # Extract hour values from the index; subtract 1 minute as in your original code.
            # We assume the index contains Timestamps.
            hours = np.array([(ts - pd.Timedelta(minutes=1)).hour for ts in self.results.index], dtype=np.int32)
            
            # Call the jitted function using the current battery state and parameters.
            battery_plus, battery_minus, energy_state = jit_simulate_MT_VT_shift(
                hours,
                dt,
                self.current_e_kwh,       # initial energy state
                self.max_e_kwh,           # max battery capacity
                self.max_charge_p_kw,     # max charging power
                self.max_discharge_p_kw   # max discharging power
            )
            # Update results:
            # In the original code, charging is recorded as battery_minus (and stored with a negative sign).
            self.results["battery_plus"] = battery_plus
            self.results["battery_minus"] = -battery_minus
            # Reconstruct p_after as in your original logic.
            self.results["p_after"] = self.results["p"] - battery_plus - (-battery_minus)
            self.results["var_bat"] = energy_state
            # Update current battery energy
            self.current_e_kwh = energy_state[-1]
            lst = list(energy_state)

        elif control_type == "5Tariff_manoeuvering":
            dt = 0.25  # 15-minute interval in hours
            # Extract hour values from the index.
            hours = np.array([(ts - pd.Timedelta(minutes=1)).hour for ts in self.results.index], dtype=np.int32)
            init_e = self.current_e_kwh
            battery_plus, battery_minus, energy_state = jit_simulate_5tariff(
                hours, dt, init_e, self.max_e_kwh,
                self.max_charge_p_kw, self.max_discharge_p_kw
            )
            self.results["battery_plus"] = battery_plus
            # In this branch, we record charging as negative.
            self.results["battery_minus"] = -battery_minus
            self.results["p_after"] = self.results["p"] - battery_plus - (-battery_minus)
            self.results["var_bat"] = energy_state
            self.current_e_kwh = energy_state[-1]
            lst = list(energy_state)

        self.results[
            "p_after"] = self.results.p - self.results.battery_plus - self.results.battery_minus
        self.results["var_bat"] = lst
        return self.results

    def simulate(
        self,
        p_kw: pd.DataFrame = None,
        control_type: str = "production_saving",
    ):
        self.hard_reset()
        self.model(control_type=control_type, p_kw=p_kw)
        self.timeseries = self.results["p_after"]
        return self.timeseries
    
    def is_p_limit_possible(self, p_limit):
        """
        Determine if the given p_limit is possible.
        Converts self.results["p"] to a NumPy array and calls the jitted function.
        """
        # Ensure self.results is available; you might want to check or set it before calling this.
        p_array = self.results["p"].values
        dt = 0.25  # 15 minutes expressed in hours
        # Call the jitted function
        result = jit_is_p_limit_possible(
            p_array,
            p_limit,
            self.current_e_kwh,
            self.max_charge_p_kw,
            self.max_discharge_p_kw,
            self.max_e_kwh,
            dt
        )
        return result

    def get_min_p_lim(self):
        """
        Function calculates the optimal limit of the maximum power
        """
        max_bound = self.results.p.max()
        function = self.is_p_limit_possible
        root = optimize.bisect(function,
                               max_bound - self.max_discharge_p_kw - 1,
                               max_bound,
                               xtol=0.05)
        return root

    def soft_reset(self):
        """
        Soft reset the battery.
        """
        self.current_p_kw = 0.
        self.current_e_kwh = self.max_e_kwh * self.soc

    def hard_reset(self):
        """
        Hard reset the battery.
        """
        self.current_p_kw = 0.
        self.current_e_kwh = self.max_e_kwh
        self.soc = 1.

    def change_battery(self,
                       max_e_kwh: float,
                       max_charge_p_kw: float,
                       max_discharge_p_kw: float = None,
                       st_type: str = None):
        """
        Change the battery size and params.

        Parameters
        ----------
        max_e_kwh : float
            Maximum energy in kWh.
        max_charge_p_kw : float
            Maximum power in kW.
        max_discharge_p_kw : float
            Maximum power in kW.
        st_type : str
            Storage type.
        """
        if st_type is None:
            self.max_e_kwh = float(max_e_kwh)
            self.max_charge_p_kw = float(max_charge_p_kw)
            if max_discharge_p_kw is None:
                self.max_discharge_p_kw = float(max_charge_p_kw)
            else:
                self.max_discharge_p_kw = float(max_discharge_p_kw)
        else:
            storage_type = StorageType(st_type)
            self.max_e_kwh = storage_type.max_e_kwh
            self.max_charge_p_kw = storage_type.max_charge_p_kw
            self.max_discharge_p_kw = storage_type.max_discharge_p_kw
            self.name = storage_type.name
        self.hard_reset()

    def change_battery_by_type(self, st_type: str):
        """
        Change the battery by type.

        Parameters
        ----------
        st_type : str
            Storage type.
        """
        storage_type = StorageType(st_type)
        self.max_e_kwh = storage_type.max_e_kwh
        self.max_charge_p_kw = storage_type.max_charge_p_kw
        self.max_discharge_p_kw = storage_type.max_discharge_p_kw
        self.name = storage_type.name
        self.hard_reset()
    
    def are_p_limits_posible(self, p_limits, max_soc=1., month_df=None):
        if month_df is None:
            df = self.results
        else:
            df = month_df
        self.hard_reset()
        
        p_array = df["p"].values
        block_array = df["block"].values  # assuming this exists
        dt = 0.25  # time step in hours

        # Call the JIT function with the required parameters
        result = jit_are_p_limits_possible(
            p_array,
            block_array,
            np.array(p_limits),
            self.current_e_kwh,
            self.max_charge_p_kw,
            self.max_discharge_p_kw,
            self.max_e_kwh * max_soc,
            dt
        )
        return result


    def find_block_p_limit(self, p_limits, block, p_limits_orig= None, month_df = None):

        max_bound = p_limits[block-1]
        if p_limits_orig is None:
            p_limits_orig = p_limits
        
        min_bound = p_limits_orig[block-1]- self.max_discharge_p_kw-1
        if block == 1:
            function = lambda x: self.are_p_limits_posible([x if i == block - 1 else p_limits[i] for i in range(5)], max_soc=0.95, month_df = month_df)
        else:
            function = lambda x: self.are_p_limits_posible([x if i == block - 1 else p_limits[i] for i in range(5)], month_df = month_df)
        root = optimize.bisect(function,
                               min_bound,
                               max_bound,
                               xtol=0.05)
        return root
    
    def get_max_p_limits(self, month_df = None):
        """
        Get the maximum possible p_limits for the battery.
        Args:
        --------
        batt: BatteryStorage object
        month_df: pd.DataFrame, dataframe with month data for month block power reduction

        Returns:
        --------
        p_limits: list of floats, limit powers for every block, considering the fact that the powers in the higher blocks must not be lower than in the lower ones.
        p_limits_orig: list of floats, limit powers for every block, without considering the fact that the powers in the higher blocks must not be lower than in the lower ones.
        """
        if month_df is None:
            df = self.results
        else:
            df = month_df
        for block in df["block"].unique():
            p_limits = df[df["block"] == block]["p"].max()

        p_limits = [df[df["block"] == block]["p"].max() for block in range(1, 6)]
        #replace nan with 0
        p_limits_orig = [0 if np.isnan(x) else x for x in p_limits]

        p_limits = p_limits_orig.copy()
        current_max = 0
        for i in range(5):
            if p_limits[i] < current_max:
                p_limits[i] = current_max
            else:
                current_max = p_limits[i]
        return p_limits, p_limits_orig
    
    def find_p_limits(self, month_df = None):
        """
        Find the optimal p_limits for the battery
        Args:
        --------
        batt: BatteryStorage object
        month_df: pd.DataFrame, dataframe with month data for month block power reduction
        Returns:
        --------
        p_limits: list of floats, limit powers for every block
        --------
        First, we calculate to what extent we can reduce the power consumption in the 
        first block without increasing the power in the other blocks. 
        Then, considering the calculated power in the first block, 
        we calculate the power for the second block. We repeat this process for all five blocks

        """
        p_limits, p_limits_orig = self.get_max_p_limits(month_df = month_df)
        if month_df is None:
            df = self.results
        else:
            df = month_df
        for block in range(1, 6):
            if block == 1:
                if len(df[df["block"] == block]) > 0:                    
                    p_limit = round(self.find_block_p_limit(p_limits, block, p_limits_orig, month_df = month_df) + 0.1, 1)
                    p_limits[0] = p_limit
                else:
                    p_limits[0] = 0
            else:
                p_limits_min = p_limits.copy()
                p_limits_min[block-1] = p_limits[block-2]
                # If it is possible, that p_limit is the same as in the previous block we take it
                if self.are_p_limits_posible(p_limits_min, month_df= month_df) == 1:
                    p_limits[block-1] = p_limits[block-2]
                else:
                    p_limit = round(self.find_block_p_limit(p_limits, block, p_limits_orig, month_df=month_df) + 0.1, 1)
                    p_limits[block-1] = p_limit

        return p_limits
    
    def simulate_p_limit(self):
        """
        With already calculated p_limits, simulates the battery behavior.
        Assumes self.results["p_limit"] is already defined.
        """
        dt = 0.25  # 15-minute interval in hours
        # Convert DataFrame columns to NumPy arrays:
        p_array = self.results["p"].values.astype(np.float64)
        p_limit_array = self.results["p_limit"].values.astype(np.float64)
        
        # Call the JIT function using the current battery state and parameters.
        battery_plus, battery_minus, energy_state = jit_simulate_p_limit(
            p_array,
            p_limit_array,
            dt,
            self.current_e_kwh,   # initial energy state
            self.max_e_kwh,       # maximum battery capacity
            self.max_charge_p_kw, # maximum charging power
            self.max_discharge_p_kw  # maximum discharging power
        )
        
        # Store results in the DataFrame.
        self.results["battery_plus"] = battery_plus
        # In your original code, battery_minus was stored as negative.
        # We computed positive charge amounts, so we store the negative value.
        self.results["battery_minus"] = -battery_minus
        # Compute p_after similar to your original logic.
        self.results["p_after"] = self.results["p"] - battery_plus - (-battery_minus)
        self.results["var_bat"] = energy_state
        
        # Optionally, update the current battery state.
        self.current_e_kwh = energy_state[-1]
        
        # Return energy state as a list (or as an array if preferred).
        return list(energy_state)
    

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from tariffsys import Settlement
    from copy import deepcopy
    import time
    bs = BS(0, 0, 0, max_charge_p_kw=2000, max_discharge_p_kw=2000, max_e_kwh=4000)
    p_kw = pd.read_csv("/Users/blazdobravec/Documents/WORK/EKSTERNI-PROJEKTI/Kalkulator_GE/ostalo/xyz.csv", parse_dates=["date_time"])
    # Test control
    p_kw.set_index("date_time", inplace=True)
    start = time.time()
    bs.simulate(p_kw, control_type="production_saving")
    print("Elapsed time:", time.time
          () - start)
    # plot p and p_after
    # set date_time to be index in bs.results

    plt.plot(bs.results.p_after)
    plt.plot(bs.results.p)
    # plot soc
    plt.plot(bs.results.var_bat)
    plt.legend(["p_after", "p", "soc"])
    plt.show()

    operating_hours = 2501 if 1 else 1

    tech_df = pd.DataFrame({
        "smm": [0],
        "num_phases": [3],
        "connected_power": [p_kw['p'].max()],
        "consumer_type": [1],
        "consumer_type_id": [4],
        "reduced_network_fee": [0],
        "operating_hours": [operating_hours],
        "reduced_ove_spte": [0],
        "connection_scheme": [0],
        "community_consumption": [0],
        "community_production": [0],
        "storage": [0],
        "billing_power": [p_kw['p'].max()],
        "num_tariffs": [2],
        "connection_type_id": [5 if 1 else 1]
    })
    s = Settlement()

    s.calculate_settlement(smm=0, timeseries_data=p_kw, load_manually=True, tech_data=tech_df)
    print("before:", s.output["ts_results"])
    e_mt_original = sum(s.output["ts_results"]["e_mt"])
    e_vt_original = sum(s.output["ts_results"]["e_vt"])
    df_after = deepcopy(bs.results)
    df_after["p"] = df_after["p_after"]
    s.calculate_settlement(smm=0, timeseries_data=df_after, load_manually=True, tech_data=tech_df)
    print("after:", s.output["ts_results"])
    e_mt_after = sum(s.output["ts_results"]["e_mt"])
    e_vt_after = sum(s.output["ts_results"]["e_vt"])

    print("mt_diff:", e_mt_original - e_mt_after)
    print("vt_diff:", e_vt_original - e_vt_after)
    # calculate savings on (e_mt + e_vt) between the two scenarios
    savings = (e_mt_original * 0.13 + e_vt_original * 0.18) - (e_mt_after * 0.13 + e_vt_after * 0.18)
    print("savings:", savings)
