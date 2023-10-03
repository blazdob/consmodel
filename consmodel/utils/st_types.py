
class GenericType:

    types = {}

    def __init__(self):
        self._name = None

    @property
    def name(self):
        return self._name
    

    def get_standard_types(self):
        """
        Return a list of standard types.
        """
        return list(self.types.keys())

    def get_type(self, name):
        """
        Return a type object.
        """
        return self.types[name]
    
    def get_params(self):
        """
        Return a dictionary of parameters.
        """
        # get all attrs
        attrs = [attr for attr in dir(self) if not callable(getattr(self, attr)) 
                                                    and not attr.startswith("__") 
                                                    and not attr.startswith("_")]
        return attrs

class StorageType(GenericType):
    """
    Storage type class.

    Attributes
    ----------
    storage_type : str
        Name of the storage type.
        Where the storage type is one of the following:
        - tesla_powerwall       (13.5 kWh, 5 kW)
        - tesla_powerwall2      (13.5 kWh, 7 kW)
        - tesla_powerwall3      (35 kWh, 15 kW)
        - tesla_powerpack       (210 kWh, 50 kW)
        - 10kWh_5kW             (generic)
        - 20kWh_5kW
        - 20kWh_10kW
        - 20kWh_15kW
    """
    
    types = {
        "tesla_powerwall": {
            "name": "tesla_powerwall",
            "max_charge_p_kw": 5.,
            "max_discharge_p_kw": 5.,
            "max_e_kwh": 13.5,
        },
        "tesla_powerwall2": {
            "name": "tesla_powerwall2",
            "max_charge_p_kw": 7.,
            "max_discharge_p_kw": 7.,
            "max_e_kwh": 13.5,
        },
        "tesla_powerwall3": {
            "name": "tesla_powerwall3",
            "max_charge_p_kw": 15.,
            "max_discharge_p_kw": 15.,
            "max_e_kwh": 35.,
        },
        "tesla_powerpack": {
            "name": "tesla_powerpack",
            "max_charge_p_kw": 50.,
            "max_discharge_p_kw": 50.,
            "max_e_kwh": 210.,
        },
        "10kWh_5kW": {
            "name": "10kWh_5kW",
            "max_charge_p_kw": 5.,
            "max_discharge_p_kw": 5.,
            "max_e_kwh": 10.,
        },
        "20kWh_5kW": {
            "name": "20kWh_5kW",
            "max_charge_p_kw": 5.,
            "max_discharge_p_kw": 5.,
            "max_e_kwh": 20,
        },
        "20kWh_10kW": {
            "name": "20kWh_10kW",
            "max_charge_p_kw": 10.,
            "max_discharge_p_kw": 10.,
            "max_e_kwh": 2.,
        },
        "20kWh_15kW": {
            "name": "20kWh_15kW",
            "max_charge_p_kw": 15.,
            "max_discharge_p_kw": 15.,
            "max_e_kwh": 20.,
        },
    }
    def __init__(self,
                storage_type: str = "tesla_powerwall",
                ):
        self._name = self.types[storage_type]["name"]
        self._max_charge_p_kw = self.types[storage_type]["max_charge_p_kw"]
        self._max_discharge_p_kw = self.types[storage_type]["max_discharge_p_kw"]
        self._max_e_kwh = self.types[storage_type]["max_e_kwh"]

    @property
    def max_charge_p_kw(self):
        return self._max_charge_p_kw
    
    @property
    def max_discharge_p_kw(self):
        return self._max_discharge_p_kw
    
    @property
    def max_e_kwh(self):
        return self._max_e_kwh
    
class HPType(GenericType):
    """
    Heat pump type class.

    Attributes
    ----------
    hp_type : str
        Name of the heat pump type.
        Where the heat pump type is one of the following:
        - Outdoor Air / Water
        - Brine / Water
        - Water / Water

        where each can be regulated or on/off.
    """
    types = {
        "Outdoor Air / Water (regulated)": {
            "name": "Outdoor Air / Water (regulated)",
            "group_id": 1,
            "regulated": True
        },
        "Brine / Water (regulated)": {
            "name": "Brine / Water (regulated)",
            "group_id": 2,
            "regulated": True
        },
        "Water / Water (regulated)": {
            "name": "Water / Water (regulated)",
            "group_id": 3,
            "regulated": True
        },
        "Outdoor Air / Water (on/off)": {
            "name": "Outdoor Air / Water (on/off)",
            "group_id": 4,
            "regulated": False
        },
        "Brine / Water (on/off)": {
            "name": "Brine / Water (on/off)",
            "group_id": 5,
            "regulated": False
        },
        "Water / Water (on/off)": {
            "name": "Water / Water (on/off)",
            "group_id": 6,
            "regulated": False
        },
    }

    def __init__(self,
                hp_type: str = "Outdoor Air / Water (regulated)",
                ):
        self._name = self.types[hp_type]["name"]
        self._group_id = self.types[hp_type]["group_id"]
        self._regulated = self.types[hp_type]["regulated"]

    @property
    def group_id(self):
        return self._group_id
    
    @property
    def regulated(self):
        return self._regulated
