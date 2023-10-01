import pandas as pd
import numpy as np
import hplib.hplib as hpl
from datetime import datetime
import meteostat

from consmodel.base_model import BaseModel

class HP(BaseModel):
	"""
	Class to represent a heat pump object.

	Attributes
	----------
	id : int
		Unique identifier of the heat pump.
	name : str
		Name of the heat pump.
	TZ : str
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
				id: int = 0,
				name: str = "HP_default",
				TZ: str = None,
				use_utc: bool = False,):
		super().__init__(id, lat, lon, alt, name, TZ, use_utc)
	
	def model(self,
			wanted_temp: float,
			hp_type: str = "Generic"):
		"""
		Apply the heat pump model to the weather data.

		Parameters
		----------
		wanted_temp : float
			Wanted temperature of the heat pump.

		"""
		parameters = hpl.get_parameters(hp_type, group_id=1, t_in=-7, t_out=40, p_th=10000)
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
		list
			List of the simulated power values in kW.

		"""
		if (start is None) or (end is None):
			if year is None:
				raise ValueError("Year must be provided if start and end are not.")
			start = datetime(year,month=1,day=1,hour=0,minute=0,second=0)
			end = datetime(year+1,month=1,day=1,hour=1,minute=0,second=0)
		self.get_weather_data(start, end, freq)
		self.model(wanted_temp, hp_type)
		self.results.rename(columns={"P_el": "P"}, inplace=True)
		self.results["P"] = self.results["P"]/1000
		self.timeseries = self.results["P"]
		return self.timeseries


def get_pump_data(self, year, month, day, wanted_temp):
		start = datetime(year, month, day)
		end = datetime(year, month, day+1)

		point = meteostat.Point(self.lat, self.lon, 400)
		data = meteostat.Hourly(point, start, end)
		data = data.fetch()
		data = data.resample('15T').asfreq()
		data['temp'] = data['temp'].interpolate()
		data = data.iloc[:-1,:]
		temp_data = np.array(data['temp'].values)

 
		df = pd.DataFrame({'T_in_primary': temp_data, 'T_in_secondary': np.array([wanted_temp]*96)})
		df['T_amb'] = df['T_in_primary']
		parameters = hpl.get_parameters('Generic', group_id=1, t_in=-7, t_out=40, p_th=10000)
		heatpump = hpl.HeatPump(parameters)
		results = heatpump.simulate(t_in_primary=df['T_in_primary'].values, t_in_secondary=df['T_in_secondary'].values, t_amb=df['T_amb'].values, mode=1)
		results=pd.DataFrame.from_dict(results)

		return list(results['P_el']/1000)

if __name__ == '__main__':
	hp = HP(id=1, name="test", lat=46.155768, lon=14.304951, alt=400, TZ="Europe/Vienna")
	timeseries = hp.simulate(25,
						  	year=2022)