"""
Module Docstring

This module contains the ConsumerModel class. This class joins the subclasses, based on the consumer type, into a single class.
"""

from consmodel.base_model import BaseModel
from consmodel.bs_sim import BS
from consmodel.hp_sim import HP
from consmodel.pv_sim import PV

import pandas as pd
import warnings
from datetime import datetime

class ConsumerModel(BaseModel):
    """
    Class to represent a modelled Consumer object.

    Attributes
    ----------
    index : int
        Unique identifier of the consumer.
    name : str
        Name of the consumer.
    tz : str
        Time zone of the consumer.
    use_utc : bool
        Flag to indicate if UTC should be used as time zone.
    lat : float
        Latitude of the consumer.
    lon : float 
        Longitude of the consumer.
    alt : float
        Altitude of the consumer.
    
    Methods
    -------
    simulate()
        Simulate the consumer.
    model()
        Apply the consumer submodels anc create the results.
    """

    def __init__(self,
                 lat,
                 lon,
                 alt,
                 index: int = 0,
                 name: str = "ConsumerModel_default",
                 tz: str = None,
                 use_utc: bool = False,
                 freq: str = "15min",):
        super().__init__(index, lat, lon, alt, name, tz, use_utc, freq)
        self.elements = {"bs": None, "hp": None, "pv": None, "ev": None}

    def simulate(self,
                 has_generic_consumption: bool = True,
                 has_pv: bool = False,
                 has_heatpump: bool = False,
                 has_ev: bool = False,
                 has_battery: bool = False,
                 #time params
                 start: datetime = None,
                 end: datetime = None,
                 year: int = None,
                 freq: str = "15min",
                 #PV params
                 pv_size: float = 1.,
                 model: str = "ineichen", # "ineichen", "haurwitz", "simplified_solis"
                 consider_cloud_cover: bool = True,
                 tilt: int = 35,
                 orient: int = 180,
                 #HP params
                 wanted_temp: float = 20,
                 hp_st_type: str = "Outdoor Air / Water (regulated)",
                 #EV params
                 #BS params
                 bs_st_type: str = "10kWh_5kW",
                 control_type: str = "installed_power",
                 max_charge_p_kw: float = 1.,
                 max_discharge_p_kw: float = 1.,
                 max_e_kwh: float = 1.,
                 soc: float = 1.,
                 ):
        """
        Simulate the consumer.

        Parameters
        ----------
        has_generic_consumption : bool
            Flag to indicate if the consumer has a generic consumption model.
        has_pv : bool
            Flag to indicate if the consumer has a PV system.
        has_heatpump : bool
            Flag to indicate if the consumer has a heat pump.
        has_ev : bool
            Flag to indicate if the consumer has an EV.
        has_battery : bool
            Flag to indicate if the consumer has a battery.
        start : datetime
            Start of the simulation.
        end : datetime
            End of the simulation.
        year : int
            Year of the simulation.
        freq : str
            Frequency of the simulation.

        pv_size : float
            Size of the PV system.
        model : str
            Model for the PV simulation.
        consider_cloud_cover : bool
            Flag to indicate if the cloud cover should be considered.
        tilt : int
            Tilt of the PV system.
        orient : int
            Orientation of the PV system.

        wanted_temp : float
            Wanted temperature of the heat pump.
        hp_st_type : str
            Heat pump type.

        bs_st_type : str    
            Battery storage type.
        control_type : str
            Control type of the battery storage.
        

        Returns
        -------
        timeseries : pandas.Series
            Timeseries of the consumer.
        """
        if freq is not None:
            self.freq = freq
        # first simulate bare consumer
        self.initialize(has_battery=has_battery,
                        has_heatpump=has_heatpump,
                        has_pv=has_pv,
                        has_ev=has_ev,
                        bs_st_type=bs_st_type,
                        max_charge_p_kw=max_charge_p_kw,
                        max_discharge_p_kw=max_discharge_p_kw,
                        max_e_kwh=max_e_kwh,
                        soc=soc,
                        hp_st_type=hp_st_type,)
        self.model(has_generic_consumption=has_generic_consumption,
                   start=start,
                   end=end,
                   freq=freq,
                   year=year,)
        # then simulate the submodels and add the results (in the following order: PV, HP, EV, ... , BS)
        if has_pv:
            self.pv.simulate(pv_size=pv_size,
                             year=year,
                             start=start,
                             end=end,
                             freq=freq,
                             model=model,
                             consider_cloud_cover=consider_cloud_cover,
                             tilt=tilt,
                             orient=orient,)
            self.results["p_pv"] = self.pv.results["p"]
            self.results["p"] -= self.results["p_pv"]
        if has_heatpump:
            self.hp.simulate(wanted_temp=wanted_temp,
                             start=start,
                             end=end,
                             year=year,
                             freq=freq,
                             hp_type=hp_st_type,)
            self.results["p_hp"] = self.hp.results["p"]
            self.results["p"] += self.hp.results["p"]
        if has_ev:
            warnings.warn("EV not implemented yet.")
        if has_battery:
            self.bs.simulate(control_type=control_type,
                             p_kw=self.results.copy())
            self.results["p_bs"] = self.bs.results["p_after"]
            self.results["p"] = self.bs.results["p_after"]
        
        self.timeseries = self.results["p"]
        return self.timeseries
    
    def initialize(self,
              has_pv: bool = False,
              has_heatpump: bool = False,
              has_ev: bool = False,
              has_battery: bool = False,
              #BS params
              bs_st_type: str = "10kWh_5kW",
              max_charge_p_kw: float = 1.,
              max_discharge_p_kw: float = 1.,
              max_e_kwh: float = 1.,
              soc: float = 1.,
              #HP params
              hp_st_type: str = "Outdoor Air / Water (regulated)",
              ):
        """
        Initialize the consumer.

        Parameters
        ----------
        has_pv : bool
            Flag to indicate if the consumer has a PV system.
        has_heatpump : bool
            Flag to indicate if the consumer has a heat pump.
        has_ev : bool
            Flag to indicate if the consumer has an EV.
        has_battery : bool
            Flag to indicate if the consumer has a battery.
        bs_st_type : str
            Battery storage type.
        max_charge_p_kw : float
            Maximum charging power of the battery storage.
        max_discharge_p_kw : float
            Maximum discharging power of the battery storage.
        max_e_kwh : float   
            Maximum energy of the battery storage.
        soc : float
            State of charge of the battery storage.
        hp_st_type : str
            Heat pump type.

        Returns
        -------
        None
        """
        self.results["p"] = 0
        if has_battery:
            self.bs = BS(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         freq=self.freq,
                         name=self.name + "_BS",
                         st_type=bs_st_type,
                         tz=self.tz,
                         use_utc=self.use_utc,
                         max_charge_p_kw=max_charge_p_kw,
                         max_discharge_p_kw=max_discharge_p_kw,
                         max_e_kwh=max_e_kwh,
                         soc=soc,)
            self.elements["bs"] = self.bs
        if has_heatpump:
            self.hp = HP(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         tz=self.tz,
                         use_utc=self.use_utc,
                         freq=self.freq,
                         name=self.name + "_HP",
                         st_type=hp_st_type,
                         )
            self.elements["hp"] = self.hp
        if has_pv:
            self.pv = PV(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         name=self.name + "_PV",
                         tz=self.tz,
                         use_utc=self.use_utc,
                         freq=self.freq,)
            self.elements["pv"] = self.pv
        if has_ev:
            warnings.warn("EV not implemented yet.")

    def model(self,
              has_generic_consumption: bool = False,
              start: datetime = None,
              end: datetime = None,
              freq: str = None,
              year: int = None,
              ):
        start, end = self.handle_time_format(freq, start, end, year)

        if has_generic_consumption:
            warnings.warn("generic consumption is not implemented yet.")
            self.results["p"] = self.generic_consumption(start=start,
                                                         end=end,)
        else:
            self.results["p"] = pd.Series(data=0, index=pd.date_range(start=start, end=end, freq=self.freq, tz=self.tz))

    def generic_consumption(self,
                            start: datetime = None,
                            end: datetime = None,):
        series = pd.Series(data=0, index=pd.date_range(start=start, end=end, freq=self.freq, tz=self.tz))
        return series