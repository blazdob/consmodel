

class StorageType:
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
    
    battery_types = {
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
        self._storage_type = storage_type
        self._name = self.battery_types[storage_type]["name"]
        self._max_charge_p_kw = self.battery_types[storage_type]["max_charge_p_kw"]
        self._max_discharge_p_kw = self.battery_types[storage_type]["max_discharge_p_kw"]
        self._max_e_kwh = self.battery_types[storage_type]["max_e_kwh"]
    #__________________________________________________________________________
    # Properties
    #__________________________________________________________________________
    @property
    def storage_type(self):
        return self._storage_type
    
    @property
    def name(self):
        return self._name
    
    @property
    def max_charge_p_kw(self):
        return self._max_charge_p_kw
    
    @property
    def max_discharge_p_kw(self):
        return self._max_discharge_p_kw
    
    @property
    def max_e_kwh(self):
        return self._max_e_kwh
    
    #__________________________________________________________________________

    def get_standard_types(self):
        """
        Return a list of standard storage types.
        """
        return list(self.battery_types.keys())
    