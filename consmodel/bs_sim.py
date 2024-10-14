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
            for key, df_tmp in self.results.iterrows():
                # we have some consumption
                if df_tmp.p > 0:
                    # if battery is not empty
                    if self.current_e_kwh > 0:
                        if self.current_e_kwh - 0.25 * df_tmp.p > 0:
                            self.discharge_amount = float(
                                min(df_tmp.p, self.max_discharge_p_kw))
                        # Battery does not have enought energy to
                        # discharge at full power for the next 15 min
                        else:
                            self.discharge_amount = float(
                                min(self.max_discharge_p_kw,
                                    4 * self.current_e_kwh))
                        self.discharge(self.discharge_amount, 0.25)
                        self.results.loc[
                            key, "battery_plus"] = self.discharge_amount
                    else:
                        # we have an empty battery
                        pass
                # we have some production
                else:
                    # we can charge the battery at full capacity
                    if (self.current_e_kwh - 0.25 * df_tmp.p) < self.max_e_kwh:
                        self.charge_amount = min(df_tmp.p * (-1),
                                                 self.max_charge_p_kw)
                    else:
                        self.charge_amount = min(
                            4 * (self.max_e_kwh - self.current_e_kwh),
                            self.max_charge_p_kw)
                    self.charge(self.charge_amount, 0.25)
                    self.results.loc[key,
                                     "battery_minus"] = -self.charge_amount
                lst.append(self.current_e_kwh)
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
        elif control_type == "MT_VT_shifting":
            # run the simulation where all the energy is transfered from VT to MT (a single cycle)
            # MT = from 22 to 6 and VT = from 6 to 22
            for key, df_tmp in self.results.iterrows():
                hour = (key - pd.Timedelta(1, "min")).hour
                if hour <= 5 or hour >= 22:
                    self.charge_amount = float(
                        min(self._max_e_kwh / 8,
                            (self._max_e_kwh - self.current_e_kwh) * 4,
                            self.max_charge_p_kw))
                    self.charge(self.charge_amount, 0.25)
                    self.discharge_amount = 0.
                    self.results.loc[key, "battery_minus"] = -self.charge_amount
                else:
                    self.discharge_amount = float(
                        min(self._max_e_kwh / 16,
                            (self.current_e_kwh) * 4, self.max_discharge_p_kw))
                    self.discharge(self.discharge_amount, 0.25)
                    self.charge_amount = 0.
                    self.results.loc[key, "battery_plus"] = self.discharge_amount
                lst.append(self.current_e_kwh)


        elif control_type == "5Tariff_manoeuvering":
            for key, df_tmp in self.results.iterrows():
                hour = (key - pd.Timedelta(1, "min")).hour
                if hour <= 5 or hour >= 22:
                    n_hours = 8
                    self.charge_amount = float(
                        min(self._max_e_kwh / n_hours,
                            (self._max_e_kwh - self.current_e_kwh) * 4,
                            self.max_charge_p_kw))
                    self.discharge_amount = 0.
                elif hour >= 7 and hour <= 13:
                    n_hours = 7
                    self.discharge_amount = float(
                        min(self._max_e_kwh / n_hours,
                            (self.current_e_kwh) * 4, self.max_discharge_p_kw))
                    self.charge_amount = 0.
                elif hour in [14, 15]:
                    n_hours = 2
                    self.charge_amount = float(
                        min(self._max_e_kwh / n_hours,
                            (self._max_e_kwh - self.current_e_kwh) * 4,
                            self.max_charge_p_kw))
                    self.discharge_amount = 0.
                elif hour >= 16 and hour <= 19:
                    n_hours = 4
                    self.discharge_amount = float(
                        min(self._max_e_kwh / n_hours,
                            (self.current_e_kwh) * 4, self.max_discharge_p_kw))
                    self.charge_amount = 0.
                else:
                    self.discharge_amount = 0.
                    self.charge_amount = 0.
                self.charge(self.charge_amount, 0.25)
                self.discharge(self.discharge_amount, 0.25)
                lst.append(self.current_e_kwh)
                self.results.loc[key, "battery_plus"] = self.discharge_amount
                self.results.loc[key, "battery_minus"] = -self.charge_amount

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

    def is_p_limit_posible(self, p_limit):
        """
        Function calculates the optimal limit of the maximum power
        """
        for _, df_tmp in self.results.iterrows():
            # lower the peak
            if df_tmp.p > p_limit:
                # if battery is not empty
                if self.current_e_kwh >= 0:
                    if df_tmp.p - p_limit > self.max_discharge_p_kw:
                        # not enough max output
                        return -1
                    # Lower te peak till p_limit
                    needed_output = float(df_tmp.p - p_limit)
                    if self.current_e_kwh < needed_output * 0.25:
                        # not enough energy
                        return -1
                    self.discharge_amount = needed_output
                    self.discharge(self.discharge_amount, 0.25)
                else:
                    # we have an empty battery
                    return -1
            else:
                # excess power to charge the battery
                diff = p_limit - df_tmp.p
                self.charge_amount = float(min(diff, self.max_charge_p_kw))
                if self.current_e_kwh < self.max_e_kwh:
                    if self.current_e_kwh + self.charge_amount * 0.25 > self.max_e_kwh:
                        self.charge_amount = float(self.max_e_kwh -
                                                   self.current_e_kwh) * 4
                    self.charge(self.charge_amount, 0.25)
                else:
                    pass
        return 1

    def get_min_p_lim(self):
        """
        Function calculates the optimal limit of the maximum power
        """
        max_bound = self.results.p.max()
        function = self.is_p_limit_posible
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

    def are_p_limits_posible(self, p_limits, max_soc = 1., month_df = None):
        """
        etermine if the p_limits are possible to achieve with the battery
        Args:
        --------
        batt: BatteryStorage object
        p_limits: list of floats, limit powers for every block
        """
        if month_df is None:
            df = self.results
        else:
            df = month_df
        self.hard_reset()
        for _, df_tmp in df.iterrows():
            # lower the peak
            p_limit = p_limits[int(df_tmp.block)-1]
            if df_tmp.p > p_limit:
                # if battery is not empty
                if self.current_e_kwh >= 0:
                    if df_tmp.p - p_limit > self.max_discharge_p_kw:
                        # not enough max output
                        return -1
                    # Lower te peak till p_limit
                    needed_output = float(df_tmp.p - p_limit)
                    if self.current_e_kwh < needed_output * 0.25:
                        # not enough energy
                        return -1
                    self.discharge_amount = needed_output
                    self.discharge(self.discharge_amount, 0.25)
                else:
                    # we have an empty battery
                    return -1
            else:
                # excess power to charge the battery
                diff = p_limit - df_tmp.p
                self.charge_amount = float(min(diff, self.max_charge_p_kw))
                if self.current_e_kwh < self.max_e_kwh*max_soc:
                    if self.current_e_kwh + self.charge_amount * 0.25 > self.max_e_kwh*max_soc:
                        self.charge_amount = float(self.max_e_kwh*max_soc -
                                                   self.current_e_kwh) * 4
                    self.charge(self.charge_amount, 0.25)
                else:
                    pass
        return 1

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
        """With already calculated p_limits, simulates the battery behaviour.
        self.results["p_limit"] must be already defined"""
        lst = []
        self.hard_reset()
        for key, df_tmp in self.results.iterrows():
            p_limit = df_tmp.p_limit
            if df_tmp.p > p_limit:
                if self.current_e_kwh > 0:
                    # if battery is not empty
                    self.discharge_amount = float(
                        min(df_tmp.p - p_limit, self.max_discharge_p_kw))
                    if self.current_e_kwh < self.discharge_amount * 0.25:
                        self.discharge_amount = self.current_e_kwh * 4
                    self.discharge(self.discharge_amount, 0.25)
                    self.results.loc[
                        key, "battery_plus"] = self.discharge_amount
                else:
                    # we have an empty battery
                    pass
            # charging battery
            else:
                excess_power = p_limit - df_tmp.p
                if self.current_e_kwh < self._max_e_kwh:
                    self.charge_amount = min(excess_power,
                                             self.max_charge_p_kw)
                    if self.current_e_kwh + self.charge_amount * 0.25 > self._max_e_kwh:
                        self.charge_amount = (self.max_e_kwh -
                                              self.current_e_kwh) * 4
                    self.results.loc[key,
                                     "battery_minus"] = -self.charge_amount
                    self.charge(self.charge_amount, 0.25)
                else:
                    # we have a full battery
                    pass
            lst.append(self.current_e_kwh)
        return lst
    

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from tariffsys import Settlement
    from copy import deepcopy

    bs = BS(0, 0, 0, max_charge_p_kw=2000, max_discharge_p_kw=2000, max_e_kwh=4000)
    p_kw = pd.read_csv("/Users/blazdobravec/Documents/WORK/EKSTERNI-PROJEKTI/Kalkulator_GE/ostalo/xyz.csv", parse_dates=["date_time"])
    # Test MT_VT_shifting
    # set date_time to be index in bs.results
    p_kw.set_index("date_time", inplace=True)
    bs.simulate(p_kw, control_type="MT_VT_shifting")
    # plot p and p_after
    # set date_time to be index in bs.results
    # bs.results.set_index("date_time", inplace=True)
    plt.plot(bs.results.p_after[1000:1400])
    plt.plot(bs.results.p[1000:1400])
    # plot soc
    plt.plot(bs.results.var_bat[1000:1400])
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
