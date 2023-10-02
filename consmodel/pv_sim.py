from pvlib.irradiance import get_total_irradiance
from pvlib.location import Location

from scipy.optimize import curve_fit
from scipy.special import exp10

from datetime import datetime
import pandas as pd
import numpy as np
import pvlib

from consmodel.base_model import BaseModel


class PV(BaseModel):
    """
    Class to represent a PV object.

    Attributes
    ----------
    index : int
        The id of the PV model object.
    name : str
        The name of the PV model object.
    tz : str
        The timezone of the PV model object.
    lat : float
        The latitude of the PV model object.
    lon : float
        The longitude of the PV model object.
    alt : float
        The altitude of the PV model object.
    pv_size : float
        The size of the PV model object in kW.

    Methods
    -------
    * __init__(self, index: int, name: str)
        Constructor for the PV model class.
    * __repr__(self)
        Returns a string representation of the PV model object.
    * __str__(self)
        Returns a string representation of the PV model object.
    * __eq__(self, other)
        Returns True if the PV model objects are equal, False otherwise.
    * __hash__(self)
        Returns a hash value for the PV model object.
    * get_irradiance_data(self, start end freq)
        Returns a pandas dataframe with the columns about the irradiance data.
    * get_weather_data(self, start end freq)
        Returns a pandas dataframe with the columns about the weather data.
    * model(self, pv_size, pv_efficiency, pv_azimuth, pv_tilt, pv_type)
        Returns a pandas dataframe with the columns about the solar model.
    * simulate(self,pv_size,start,end,freq,model,consider_cloud_cover,tilt,orient)
        Returns a pandas dataframe with the columns about the simulation and
        all the results of the simulation.
    """
    def __init__(self,
                lat,
                lon,
                alt,
                index: int = 0,
                name: str = "PV_default",
                tz: str = None,
                use_utc: bool = False,):
        super().__init__(index, lat, lon, alt, name, tz, use_utc)
        self._location = Location(lat,
                    lon,
                    tz=self._tz,
                    altitude=alt,
                    name=name)

    def __repr__(self):
        return f"PV model(id={self.id}, name={self.name})"

    def __str__(self):
        return f"PV model(id={self.id}, name={self.name})"

    #__________________________________________________________________________
    # Properties
    @property
    def pv_size(self):
        return self._pv_size

    @pv_size.setter
    def pv_size(self, pv_size):
        self._pv_size = pv_size

    @property
    def lat_lon_alt(self):
        return (self._lat, self._lon, self._alt)

    @lat_lon_alt.setter
    def lat_lon_alt(self, lat_lon_alt):
        self._lat = lat_lon_alt[0]
        self._lon = lat_lon_alt[1]
        self._alt = lat_lon_alt[2]
        #recalculate timezone
        # recalculate location
        self._location = Location(self.lat,
                    self.lon,
                    tz=self.tz,
                    altitude=self.alt,
                    name=self.name)

    @property
    def location(self):
        return self._location

    # __________________________________________________________________________
    # Methods
    # __________________________________________________________________________
    def __repr__(self):
        return f"PV(id={self.id}, name={self.name})"

    def get_irradiance_data(self,
                            start: datetime = None,
                            end: datetime = None,
                            freq: str = "15min",
                            model: str = 'ineichen'):
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
            ghi ... global horizontal irradiance
            dni ... direct normal irradiance
            dhi ... diffuse horizontal irradiance
        """
        print(start, end, freq, model, self.tz)
        times = pd.date_range(start=start,
                                end=end,
                                freq=freq,
                                tz=self.tz)
        # ineichen with climatology table by default
        cs = self.location.get_clearsky(times, model=model)[:]
        cs = cs.iloc[:len(cs)-4]
        # change index to pd.DatetimeIndex
        cs.index = pd.DatetimeIndex(cs.index)
        # drop tz aware
        # cs.index = cs.index.tz_localize(None)
        self.results = pd.DataFrame({'ghi': cs['ghi'],
                        'dhi': cs['dhi'],
                        'dni': cs['dni']
                        })
        return self.results

    def model(self,
            pv_size: float = 0.,
            consider_cloud_cover: bool = False,
            tilt: int = 35,
            orient: int = 180,
            pv_efficiency: float = 1100.,):
        """
        INPUT:
        Function takes metadata dictionary as an input and includes the following keys:
            'pv_size'               ... float,
            'consider_cloud_cover'  ... bool,
            'tilt'                  ... float,
            'orient'                ... float,
            'pv_efficiency'         ... float,
        OUTPUT:
            results         ... pandas dataframe with
                                results that includesthe following columns:
                ghi         ... global horizontal irradiance
                dni         ... direct normal irradiance
                dhi         ... diffuse horizontal irradiance
                temp        ... The air temperature in °C
                dwpt        ... The dew point in °C
                rhum        ... The relative humidity in percent (%)
                prcp        ... The one hour precipitation total in mm
                snow        ... The snow depth in mm
                wdir        ... The average wind direction in degrees (°)
                wspd        ... The average wind speed in km/h
                wpgt        ... The peak wind gust in km/h
                pres        ... The average sea-level air pressure in hPa
                tsun        ... The one hour sunshine total in minutes (m)
                coco        ... The weather condition code
                poa_global  ... Total in-plane irradiance
                temp_pv     ... temperature of the pv module
                eta_rel     ... relative efficiency of the pv module
                p_mp        ... output power of the pv array
        """
        solpos = self.location.get_solarposition(self.results.index)
        total_irrad = get_total_irradiance(tilt,
                                            orient,
                                            solpos.apparent_zenith,
                                            solpos.azimuth,
                                            self.results.dni,
                                            self.results.ghi,
                                            self.results.dhi)

        self.results['poa_global'] = total_irrad.poa_global
        self.results['temp_pv'] = pvlib.temperature.faiman(self.results.poa_global,
                                                            self.results.temp,
                                                            self.results.wspd)
        # Borrow the ADR model parameters from the other example:
        # https://pvlib-python.readthedocs.io/en/stable/gallery/adr-pvarray/plot_fit_to_matrix.html
        # IEC 61853-1 standard defines a standard matrix of conditions for measurements
        adr_params = {'k_a': 0.99924,
                    'k_d': -5.49097,
                    'tc_d': 0.01918,
                    'k_rs': 0.06999,
                    'k_rsh': 0.26144
                    }
        self.results['eta_rel'] = self.pvefficiency_adr(self.results['poa_global'],
                                            self.results['temp_pv'],
                                            **adr_params)
        # parameter that is used to mask out the data
        # when the weather condition code is worse than Overcast
        self.results["coco_mask"] = self.results["coco"].apply(
                                    lambda x: 1 if x < 2.5
                                            else (np.random.uniform(0.4, 0.8) if x < 4.5
                                                                            else 0.3))
        if consider_cloud_cover:
            #  pv_size  * scaling
            #           * relative_efficiency of the pannels
            #           * (poa_global / G_STC) - the irradiance level needed to achieve this output
            #           * percentage of minutes of sunshine per hour
            #           * weather condition codes / hard cutoff at 3 - clowdy -  https://dev.meteostat.net/formats.html#weather-condition-codes
            scaling = np.random.uniform(0.8, 1.0, len(self.results))
            self.results['p_mp'] = pv_size * scaling \
                                * self.results['eta_rel'] \
                                * (self.results['poa_global'] / pv_efficiency) \
                                * self.results["coco_mask"]
        else:
            self.results['p_mp'] = pv_size * self.results['eta_rel'] \
                                * (self.results['poa_global'] / pv_efficiency)
        self.results = self.results[1:]
        return self.results

    # @classmethod
    def pvefficiency_adr(self, effective_irradiance, temp_cell,
                     k_a, k_d, tc_d, k_rs, k_rsh):
        """
        Calculate PV module efficiency using the ADR model.
        The efficiency varies with irradiance and operating temperature
        and is determined by 5 model parameters as described in [1]_.
        Parameters
        ----------
        effective_irradiance : numeric, non-negative
            The effective irradiance incident on the PV module. [W/m^2]
        temp_cell : numeric
            The PV module operating temperature. [°C]
        k_a : numeric
            Absolute scaling factor, which is equal to the efficiency at
            reference conditions. This factor allows the model to be used
            with relative or absolute efficiencies, and to accommodate data sets
            which are not perfectly normalized but have a slight bias at
            the reference conditions. [unitless]
        k_d : numeric, negative
            “Dark irradiance” or diode coefficient which influences the voltage
            increase with irradiance. [unitless]
        tc_d : numeric
            Temperature coefficient of the diode coefficient, which indirectly
            influences voltage. Because it is the only temperature coefficient
            in the model, its value will also reflect secondary temperature
            dependencies that are present in the PV module. [unitless]
        k_rs : numeric
            Series resistance loss coefficient. Because of the normalization
            it can be read as a power loss fraction at reference conditions.
            For example, if ``k_rs`` is 0.05, the internal loss assigned to the
            series resistance has a magnitude equal to 5% of the module output.
            [unitless]
        k_rsh : numeric
            Shunt resistance loss coefficient. Can be interpreted as a power
            loss fraction at reference conditions like ``k_rs``.
            [unitless]
        Returns
        -------
        eta : numeric
            The efficiency of the module at the specified irradiance and
            temperature.
        Notes
        -----
        Efficiency values ``eta`` may be absolute or relative, and may be expressed
        as percent or per unit.  This is determined by the efficiency data
        used to derive values for the 5 model parameters.  The first model
        parameter ``k_a`` is equal to the efficiency at STC and therefore
        indicates the efficiency scale being used. ``k_a`` can also be changed
        freely to adjust the scale, or to change the module to a slightly
        higher or lower efficiency class.
        All arguments may be scalars or array-like. If multiple arguments
        are array-like they must be the same shape or broadcastable to the
        same shape.
        See also
        --------
        pvlib.pvarray.fit_pvefficiency_adr
        References
        ----------
        .. [1] A. Driesse and J. S. Stein, "From IEC 61853 power measurements
        to PV system simulations", Sandia Report No. SAND2020-3877, 2020.
        :doi:`10.2172/1615179`
        .. [2] A. Driesse, M. Theristis and J. S. Stein, "A New Photovoltaic Module
        Efficiency Model for Energy Prediction and Rating," in IEEE Journal
        of Photovoltaics, vol. 11, no. 2, pp. 527-534, March 2021.
        :doi:`10.1109/JPHOTOV.2020.3045677`
        Examples
        --------
        >>> pvefficiency_adr([1000, 200], 25,
                k_a=100, k_d=-6.0, tc_d=0.02, k_rs=0.05, k_rsh=0.10)
        array([100.        ,  92.79729308])
        >>> pvefficiency_adr([1000, 200], 25,
                k_a=1.0, k_d=-6.0, tc_d=0.02, k_rs=0.05, k_rsh=0.10)
        array([1.        , 0.92797293])
        """
        # Contributed by Anton Driesse (@adriesse), PV Performance Labs, Dec. 2022
        # Adapted from https://github.com/adriesse/pvpltools-python

        k_a = np.array(k_a)
        k_d = np.array(k_d)
        tc_d = np.array(tc_d)
        k_rs = np.array(k_rs)
        k_rsh = np.array(k_rsh)

        # normalize the irradiance
        G_REF = np.array(1000.)
        s = effective_irradiance / G_REF

        # obtain the difference from reference temperature
        T_REF = np.array(25.)
        dt = temp_cell - T_REF

        # equation 29 in JPV
        s_o     = exp10(k_d + (dt * tc_d))                             # noQA: E221
        s_o_ref = exp10(k_d)

        # equation 28 and 30 in JPV
        # the constant k_v does not appear here because it cancels out
        v  = np.log(s / s_o     + 1)                                   # noQA: E221
        v /= np.log(1 / s_o_ref + 1)

        # equation 25 in JPV
        eta = k_a * ((1 + k_rs + k_rsh) * v - k_rs * s - k_rsh * v**2)

        return eta

    @classmethod
    def fit_pvefficiency_adr(effective_irradiance,
                            temp_cell,
                            eta,
                            dict_output=True,
                            **kwargs):
        """
        Determine the parameters of the ADR module efficiency model by non-linear
        least-squares fit to lab or field measurements.
        Parameters
        ----------
        effective_irradiance : numeric, non-negative
            Effective irradiance incident on the PV module. [W/m^2]
        temp_cell : numeric
            PV module operating temperature. [°C]
        eta : numeric
            Efficiency of the PV module at the specified irradiance and
            temperature(s). [unitless] or [%]
        dict_output : boolean, optional
            When True (default), return the result as a dictionary; when False,
            return the result as a numpy array.
        kwargs :
            Optional keyword arguments passed to `scipy.optimize.curve_fit`.
            These kwargs can over-ride some options set within this function,
            which could be interesting for very advanced users.
        Returns
        -------
        popt : array or dict
            Optimal values for the parameters.
        Notes
        -----
        The best fits are obtained when the lab or field data include a wide range
        of both irradiance and temperature values.  A minimal data set
        would consist of 6 operating points covering low, medium and high
        irradiance levels at two operating temperatures.
        See also
        --------
        pvlib.pvarray.pvefficiency_adr
        scipy.optimize.curve_fit
        """
        # Contributed by Anton Driesse (@adriesse), PV Performance Labs, Dec. 2022
        # Adapted from https://github.com/adriesse/pvpltools-python

        irradiance = np.asarray(effective_irradiance, dtype=float).reshape(-1)
        temperature = np.asarray(temp_cell, dtype=float).reshape(-1)
        eta = np.asarray(eta, dtype=float).reshape(-1)

        eta_max = np.max(eta)

        P_NAMES = ['k_a', 'k_d', 'tc_d', 'k_rs', 'k_rsh']
        P_MAX   = [+np.inf,   0, +0.1, 1, 1]                           # noQA: E221
        P_MIN   = [0,       -12, -0.1, 0, 0]                           # noQA: E221
        P0      = [eta_max,  -6,  0.0, 0, 0]                           # noQA: E221
        P_SCALE = [eta_max,  10,  0.1, 1, 1]

        SIGMA = 1 / np.sqrt(irradiance / 1000)

        fit_options = dict(p0=P0,
                        bounds=[P_MIN, P_MAX],
                        method='trf',
                        x_scale=P_SCALE,
                        loss='soft_l1',
                        f_scale=eta_max * 0.05,
                        sigma=SIGMA,
                        )

        fit_options.update(kwargs)

        def adr_wrapper(xdata, *params):
            return PV.pvefficiency_adr(*xdata, *params)

        result = curve_fit(adr_wrapper,
                        xdata=[irradiance, temperature],
                        ydata=eta,
                        **fit_options,
                        )
        popt = result[0]

        if dict_output:
            return dict(zip(P_NAMES, popt))
        else:
            return popt

    def simulate(self,
                pv_size: float,
                start: datetime = None,
                end: datetime = None,
                year: int = 2022,
                freq: str = "15min",
                model: str = "ineichen", # "ineichen", "haurwitz", "simplified_solis"
                consider_cloud_cover: bool = False,
                tilt: int = 35,
                orient: int = 180,):
        """
        INPUT:
        Function takes metadata dictionary as an input and includes the following keys:
            'pv_size' ... float in kW,
            'start' ... datetime,
            'end' ... datetime,
            'freq' ... str,
            'model' ... str,
            'consider_cloud_cover' ... bool,
            'tilt' ... float,
            'orient' ... float,
        OUTPUT:
            results ... series with results of output power of the pv array in kW
        """
        if (start is None) or (end is None):
            if year is None:
                raise ValueError("Year must be provided if start and end are not.")
            start = datetime(year,month=1,day=1,hour=0,minute=0,second=0)
            end = datetime(year+1,month=1,day=1,hour=1,minute=0,second=0)
        self.get_irradiance_data(start, end, freq, model)
        self.get_weather_data(start, end, freq)
        self.model(pv_size*1000, consider_cloud_cover, tilt, orient)
        self.results.rename(columns={"p_mp": "P"}, inplace=True)
        self.results["P"] = self.results["P"]/1000
        self.timeseries = self.results["P"]
        return self.timeseries