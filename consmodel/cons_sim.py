"""
Module Docstring

This module contains the ConsumerModel class. This class joins the subclasses, based on the consumer type, into a single class.
"""

from consmodel.base_model import BaseModel
from consmodel.bs_sim import BS
from consmodel.hp_sim import HP
from consmodel.pv_sim import PV

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
                 has_pv: bool = False,
                 has_heatpump: bool = False,
                 has_ev: bool = False,
                 has_battery: bool = False,
                 #PV params
                 pv_size: float = 0,
                 start: datetime = None,
                 end: datetime = None,
                 year: int = 2022,
                 freq: str = "15min",
                 model: str = "ineichen", # "ineichen", "haurwitz", "simplified_solis"
                 consider_cloud_cover: bool = False,
                 tilt: int = 35,
                 orient: int = 180,):
        """
        Simulate the consumer.

        Parameters
        ----------
        TODO

        Returns
        -------
        TODO
        """
        # first simulate bare consumer
        self.initialize(has_battery=has_battery,
                        has_heatpump=has_heatpump,
                        has_pv=has_pv,
                        has_ev=has_ev,)
        self.model()
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
        if has_heatpump:
            self.hp.simulate(wanted_temp=20,
                             start=start,
                             end=end,
                             year=year,
                             freq=freq,)
            self.results["p_hp"] = self.hp.results["p"]
    
    def initialize(self,
              has_pv: bool = False,
              has_heatpump: bool = False,
              has_ev: bool = False,
              has_battery: bool = False,
              bs_st_type: str = "10kWh_5kW",
              hp_st_type: str = "Generic",
              hp_st_subtype: str = "Outdoor Air / Water (regulated)",
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
        hp_st_type : str
            Heat pump type.
        hp_st_subtype : str
            Heat pump sub-type.

        Returns
        -------
        None
        """
        if has_battery:
            self.bs = BS(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         name=self.name + "_BS",
                         st_type=bs_st_type,)
            self.elements["bs"] = self.bs
        if has_heatpump:
            self.hp = HP(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         name=self.name + "_HP",
                         st_type=hp_st_type,
                         st_subtype=hp_st_subtype)
            self.elements["hp"] = self.hp
        if has_pv:
            self.pv = PV(lat=self.lat,
                         lon=self.lon,
                         alt=self.alt,
                         index=self.index,
                         name=self.name + "_PV",)
            self.elements["pv"] = self.pv
        if has_ev:
            warnings.warn("EV not implemented yet.")

    def model(self):
        pass
if __name__ == "__main__":
    consmodel = ConsumerModel(index=0,
                              lat=46.155768,
                              lon=14.304951,
                              alt=400,
                              name="ConsumerModel_test",
                              tz="Europe/Ljubljana",
                              freq="15min",)