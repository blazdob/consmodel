"""
DocString:
    An abstract base class for all models
"""
from datetime import datetime
from abc import ABC, abstractmethod
from meteostat import Point, Hourly
from tzfpy import get_tz
import pandas as pd


class BaseModel(ABC):
    """
    A base class for all models
    """
    @abstractmethod
    def __init__(self,
                 index,
                 lat,
                 lon,
                 alt,
                 name,
                 tz,
                 use_utc):
        self._index = index
        self._name = name
        if tz is None:
            if use_utc:
                self._tz = 'UTC'
            else:
                self._tz = get_tz(lon, lat)
        else:
            self._tz = tz
        self._lat = lat
        self._lon = lon
        self._alt = alt

        self.timeseries = None
        self.results = pd.DataFrame()

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name

    def __hash__(self):
        return hash((self.index, self.name))

    # Properties
    @property
    def index(self):
        return self._index

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
    def tz(self):
        return self._tz

    @tz.setter
    def tz(self, tz):
        if tz is None:
            self._tz = get_tz(self.lat, self.lon)
        else:
            self._tz = tz

    @property
    def lat_lon_alt(self):
        return (self._lat, self._lon, self._alt)

    @lat_lon_alt.setter
    def lat_lon_alt(self, lat_lon_alt):
        self._lat = lat_lon_alt[0]
        self._lon = lat_lon_alt[1]
        self._alt = lat_lon_alt[2]
        self.tz = get_tz(lat_lon_alt[0], lat_lon_alt[1])

    @abstractmethod
    def model(self):
        """
        abstract method for model
        """
        return

    @abstractmethod
    def simulate(self):
        """
        abstract method for simulate
        """
        return

    def get_weather_data(self,
                         start: datetime = None,
                         end: datetime = None,
                         freq: str = "15min"):
        """
        INPUT:
        Function takes metadata dictionary as an input and
        includes the following keys:
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
                              self.tz)
        weather_data = weather_data.fetch()
        weather_data = weather_data.iloc[:-1]
        weather_data = weather_data.resample(freq) \
                                   .mean() \
                                   .interpolate(method='linear')
        self.results = pd.concat([self.results, weather_data], axis=1)
        return self.results
