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
                st_subtype: str = None,):
        super().__init__(index, lat, lon, alt, name, tz, use_utc)
        if st_subtype is None:
            self.hp_type = HPType()
        else:
            self.hp_type = HPType(st_subtype)
        
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
        self.results = self.results[1:]
        return self.results


    def simulate(self,
                wanted_temp: float,
                hp_type: str = "Generic",
                hp_subtype: str = "Outdoor Air / Water (regulated)",
                start: datetime = None,
                end: datetime = None,
                year: int = 2022,
                freq: str = "15min"):
        """
        Simulate the heat pump for a given day.

        Parameters
        ----------
        year : int
            Year of the simulation.
        month : int
            Month of the simulation.
        day : int
            Day of the simulation.
        wanted_temp : float
            Wanted temperature of the heat pump.

        Returns
        -------
        pd.Series
            pd.Series of the simulated power values in kW.

        """
        if (start is None) or (end is None):
            if year is None:
                raise ValueError("Year must be provided if start and end are not.")
            start = datetime(year,month=1,day=1,hour=0,minute=0,second=0)
            end = datetime(year+1,month=1,day=1,hour=1,minute=0,second=0)
        self.get_weather_data(start, end, freq)
        hp_subtype_id = self.hp_type.types[hp_subtype]["group_id"]
        print(hp_subtype_id)
        self.model(wanted_temp, hp_type, hp_subtype_id)
        self.results.rename(columns={"P_el": "P"}, inplace=True)
        self.results["P"] = self.results["P"]/1000
        self.timeseries = self.results["P"]
        return self.timeseries
    
if __name__ == '__main__':
    hp = HP(lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            st_type="Generic",
            st_subtype="Outdoor Air / Water (regulated)")
    timeseries = hp.simulate(wanted_temp=45,
                            hp_type="Generic",
                            hp_subtype="Outdoor Air / Water (regulated)",
                            year = 2022,)
    print(timeseries)
    import matplotlib.pyplot as plt
    print(timeseries.sum())
    plt.show()