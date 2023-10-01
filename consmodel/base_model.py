from meteostat import Point, Hourly
from abc import ABC, abstractmethod
from datetime import datetime
from tzfpy import get_tz
import pandas as pd


class BaseModel(ABC):
	@abstractmethod
	def __init__(self,
				id,
				lat,
				lon,
				alt,
				name,
				TZ,
				use_utc,):
		self._id = id
		self._name = name
		if TZ is None:
			if use_utc:
				self._TZ = 'UTC'
			else:
				self._TZ = get_tz(lon, lat)
		else:
			self._TZ = TZ
		self._lat = lat
		self._lon = lon
		self._alt = alt

		self.timeseries = None
		self.results = pd.DataFrame()

	def __eq__(self, other):
		return self.id == other.id and self.name == other.name
	
	def __hash__(self):
		return hash((self.id, self.name))
	
	#__________________________________________________________________________
	# Properties
	@property
	def id(self):
		return self._id

	@property
	def name(self):
		return self._name
	
	@name.setter
	def name(self, name):
		self._name = name

	@property
	def lat(self):
		return self._lat
	
	@property
	def lon(self):
		return self._lon
	
	@property
	def alt(self):
		return self._alt
	
	@property
	def TZ(self):
		return self._TZ
	
	@TZ.setter
	def TZ(self, TZ):
		if TZ is None:
			self._TZ = get_tz(self.lat, self.lon)
		else:
			self._TZ = TZ
	
	@property
	def lat_lon_alt(self):
		return (self._lat, self._lon, self._alt)

	@lat_lon_alt.setter
	def lat_lon_alt(self, lat_lon_alt):
		self._lat = lat_lon_alt[0]
		self._lon = lat_lon_alt[1]
		self._alt = lat_lon_alt[2]
		#recalculate timezone
		self.TZ = get_tz(lat_lon_alt[0], lat_lon_alt[1])
		#recalculate location
		# self._location = Location(self.lat,
		# 			self.lon,
		# 			tz=self.TZ,
		# 			altitude=self.alt,
		# 			name=self.name)

	
	@abstractmethod
	def model(self):
		pass

	@abstractmethod
	def simulate(self):
		pass

	def get_weather_data(self,
						start: datetime = None,
						end: datetime = None,
						freq: str = "15min"):
		"""
		INPUT:
		Function takes metadata dictionary as an input and includes the following keys:
			'latitude'      ... float,
			'longitude'     ... float,
			'altitude'      ... float,
			'start_date'    ... datetime,
			'end_date'      ... datetime,
			'freq'          ... str,
		OUTPUT:
			weather_data ... pandas dataframe with 
			weather data that includesthe following columns:
				temp ... The air temperature in °C
				dwpt ... The dew point in °C
				rhum ... The relative humidity in percent (%)
				prcp ... The one hour precipitation total in mm
				snow ... The snow depth in mm
				wdir ... The average wind direction in degrees (°)
				wspd ... The average wind speed in km/h
				wpgt ... The peak wind gust in km/h
				pres ... The average sea-level air pressure in hPa
				tsun ... The one hour sunshine total in minutes (m)
				coco ... The weather condition code
		"""
		location = Point(self.lat, self.lon, self.alt)
		weather_data = Hourly(location, 
								start,
								end,
								self.TZ)
		weather_data = weather_data.fetch()
		weather_data = weather_data.iloc[:-1] #TODO: maybe we need to shift it as it depends on the frequency
		weather_data = weather_data.resample(freq) \
									.mean() \
									.interpolate(method='linear')
		self.results = pd.concat([self.results, weather_data], axis=1)
		return self.results
	
	# def get_average_daily_profile(self, p_mp: pd.DataFrame = None):
	# 	"""
	# 	INPUT:
	# 		p_mp ... output power of the pv array
	# 	OUTPUT:
	# 		average_daily_production ... dataframe with the average daily profile
	# 	"""
	# 	p_mp.index = pd.to_datetime(p_mp.index)
	# 	average_daily_production = p_mp.groupby([p_mp.index.hour]).mean()
	# 	return average_daily_production