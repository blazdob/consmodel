import unittest
import pandas as pd
from consmodel.bs_sim import BS

class TestBS(unittest.TestCase):

    def test_result(self):
        # create a simple PV model
        test_consumption = [0.,-3.,-2.,8.,7.,6.,7.,8.,3.,5.,4.,-2.,0.,2.,0.,0.,0.]
        test_consumption_df = pd.DataFrame({"p": test_consumption},
                        index=pd.date_range("2020-01-01 06:00:00",
                                            periods=17,
                                            freq="15min"))
        batt = BS(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    st_type="10kWh_5kW")
        timeseries = batt.simulate(control_type="installed_power",
                                p_kw=test_consumption_df)
        self.assertEqual([0.0, -3.0, -2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],timeseries.values.tolist())
    

    def test_batt_installed_power(self):
        batt = BS(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    st_type="10kWh_5kW")
        test_data = pd.DataFrame({"p": [0.,-3.,-2.,8.,7.,6.,7.,8.,3.,5.,4.,-2.,0.,2.,0.,0.,0.]},
                                    index=pd.date_range("2020-01-01 06:00:00",
                                    periods=17,
                                    freq="15min"))
        timeseries = batt.simulate(control_type="installed_power",
                            p_kw=test_data)
        p_after_result = [ 0.,-3.,-2., 3., 3., 3., 3., 3., 3., 3., 3., 3., 3., 3., 3., 3., 3.]
        var_bat_result = [10., 10., 10., 8.75, 7.75, 7., 6., 4.75, 4.75, 4.25, 4., 5.25, 6., 6.25, 7., 7.75, 8.5]
        self.assertEqual(timeseries.values.tolist(), p_after_result)
        self.assertEqual(batt.results["var_bat"].tolist(), var_bat_result)
    
    def test_batt_production_saving(self):
        batt = BS(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    st_type="10kWh_5kW")
        test_data = pd.DataFrame({"p": [0.,-3.,-2.,8.,7.,6.,7.,8.,3.,5.,4.,-2.,0.,2.,0.,0.,0.]}, index=pd.date_range("2020-01-01 06:00:00", periods=17, freq="15min"))
        timeseries = batt.simulate(control_type="production_saving",
                            p_kw=test_data)
        p_after_result = [0., -3., -2., 3., 2., 1., 2., 3., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
        var_bat_result = [10., 10., 10., 8.75, 7.5, 6.25, 5., 3.75, 3., 1.75, 0.75, 1.25, 1.25, 0.75, 0.75, 0.75, 0.75]
        self.assertEqual(timeseries.values.tolist(), p_after_result)
        self.assertEqual(batt.results["var_bat"].tolist(), var_bat_result)