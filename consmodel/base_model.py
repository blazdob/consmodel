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
    def __init__(self, index, lat, lon, alt, name, tz, use_utc, freq):
        self._index = index
        self._name = name
        self._use_utc = use_utc
        if tz is None:
            if self.use_utc:
                self._tz = 'UTC'
            else:
                self._tz = get_tz(lon, lat)
        else:
            self._tz = tz
        self._lat = lat
        self._lon = lon
        self._alt = alt
        self._freq = freq
        self._freq_mins = self.get_freq_mins(freq)

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

    @property
    def freq(self):
        return self._freq

    @property
    def freq_mins(self):
        return self._freq_mins

    @property
    def use_utc(self):
        return self._use_utc

    @property
    def lat_lon_alt(self):
        return (self._lat, self._lon, self._alt)

    @name.setter
    def name(self, name):
        self._name = name

    @index.setter
    def index(self, index):
        self._index = index

    @freq_mins.setter
    def freq_mins(self, freq_mins):
        self._freq_mins = freq_mins

    @use_utc.setter
    def use_utc(self, use_utc):
        self._use_utc = use_utc

    @tz.setter
    def tz(self, tz):
        if tz is None:
            self._tz = get_tz(self.lat, self.lon)
        else:
            self._tz = tz

    @freq.setter
    def freq(self, freq):
        self._freq = freq

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

    def get_freq_mins(self, freq):
        """
        INPUT:
        Function takes a string as an input and
        includes the following keys:
            'freq'         ... string,
        OUTPUT:
            freq_mins ... int
        """
        if freq == '10min':
            freq_mins = 10
        elif freq == '15min':
            freq_mins = 15
        elif freq == '30min':
            freq_mins = 30
        elif freq == '60min':
            freq_mins = 60
        else:
            raise ValueError('Frequency must be 10min, 15min, 30min or 60min')
        return freq_mins

    def handle_time_format(self, freq, start, end, year):
        if freq is not None:
            self.freq = freq

        if (start is None) or (end is None):
            if year is None:
                raise ValueError(
                    "Year must be provided if start and end are not.")
            start = pd.to_datetime(f"{year}-01-01 00:15:00")
            end = pd.to_datetime(f"{year+1}-01-01 00:00:00")
        # handle rounding to nearest interval of freq
        self.freq_mins = self.get_freq_mins(self.freq)
        if start.minute % self.freq_mins != 0:
            start = start + pd.Timedelta(minutes=self.freq_mins -
                                         start.minute % self.freq_mins)
        if end.minute % self.freq_mins != 0:
            end = end - pd.Timedelta(minutes=end.minute % self.freq_mins)
        return start, end

    def get_weather_data(
        self,
        start: datetime = None,
        end: datetime = None,
    ):
        """
        INPUT:
        Function takes metadata dictionary as an input and
        includes the following keys:
            'start'         ... datetime,
            'end'           ... datetime,
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
        # round the start to the nearest hour
        start = start.replace(minute=0, second=0, microsecond=0)

        # if end is over an hour then round up to the next hour
        if end.minute > 0 or end.second > 0 or end.microsecond > 0:
            end = end.replace(hour=end.hour + 1,
                              minute=0,
                              second=0,
                              microsecond=0)

        location = Point(self.lat, self.lon, self.alt)
        weather_data = Hourly(location, start, end, self.tz)
        weather_data = weather_data.fetch()
        weather_data = weather_data.resample(self.freq) \
                                   .mean() \
                                   .interpolate(method='linear')
        self.results = pd.concat([self.results, weather_data], axis=1)
        return self.results
