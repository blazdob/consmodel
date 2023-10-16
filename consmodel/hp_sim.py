from datetime import datetime
import hplib.hplib as hpl
import pandas as pd
import numpy as np

from consmodel.utils.st_types import HPType
from consmodel.base_model import BaseModel

class HP(BaseModel):
    """
    Class to represent a heat pump object.

    Attributes
    ----------
    index : int
        Unique identifier of the heat pump.
    name : str
        Name of the heat pump.
    tz : str
        Time zone of the heat pump.
    use_utc : bool
        Flag to indicate if UTC should be used as time zone.
    lat : float
        Latitude of the heat pump.
    lon : float
        Longitude of the heat pump.
    alt : float
        Altitude of the heat pump.

    Methods
    -------

    """
    def __init__(self,
                lat,
                lon,
                alt,
                index: int = 0,
                name: str = "HP_default",
                tz: str = None,
                use_utc: bool = False,
                st_type: str = None,
                freq: str = "15min",):
        super().__init__(index, lat, lon, alt, name, tz, use_utc, freq)
        if st_type is None:
            self.hp_type = HPType()
        else:
            self.hp_type = HPType(st_type)
        
    def model(self,
            wanted_temp: float,
            hp_type: str = "Generic",
            hp_subtype: str = "Outdoor Air / Water (regulated)"):
        """
        Apply the heat pump model to the weather data.

        Parameters
        ----------
        wanted_temp : float
            Wanted temperature of the heat pump.

        """

        parameters = hpl.get_parameters(hp_type, group_id=hp_subtype, t_in=-7, t_out=40, p_th=10000)
        hp = hpl.HeatPump(parameters)
        results = hp.simulate(t_in_primary=self.results['temp'].values,
                            t_in_secondary=np.array([wanted_temp]*len(self.results)),
                            t_amb=self.results['temp'].values,
                            mode=1)
        output=pd.DataFrame.from_dict(results)
        output.index = self.results.index
        # concatenate the results and output
        self.results = pd.concat([self.results, output], axis=1)
        # drop temp
        self.results.drop(columns=['temp'], inplace=True)
        return self.results


    def simulate(self,
                wanted_temp: float,
                start: datetime = None,
                end: datetime = None,
                freq: str = None,
                year: int = None,
                hp_type: str = "Outdoor Air / Water (regulated)",
                ):
        """
        Simulate the heat pump for a given time period.

        Parameters
        ----------
        wanted_temp : float
            Wanted temperature of the heat pump.
        start : datetime
            Start of the simulation.
        end : datetime
            End of the simulation.
        freq : str
            Frequency of the simulation.
        year : int
            Year of the simulation.
        hp_type : str
            Heat pump type.

        Returns
        -------
        pd.Series
            pd.Series of the simulated power values in kW.

        """
        start, end = self.handle_time_format(freq, start, end, year)
        self.get_weather_data(start, end)
        hp_type_id = self.hp_type.types[hp_type]["group_id"]
        self.model(wanted_temp, "Generic", hp_type_id)
        self.results.rename(columns={"P_el": "p"}, inplace=True)
        self.results["p"] = self.results["p"]/1000
        self.results = self.results[self.results.index >= start.tz_localize(self.tz)]
        self.results = self.results[self.results.index <= end.tz_localize(self.tz)]

        self.timeseries = self.results["p"]
        return self.timeseries
