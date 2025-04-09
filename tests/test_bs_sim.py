import unittest
import pandas as pd
from consmodel.bs_sim import BS


class TestBS(unittest.TestCase):

    def test_result(self):
        # create a simple PV model
        test_consumption = [
            0., -3., -2., 8., 7., 6., 7., 8., 3., 5., 4., -2., 0., 2., 0., 0.,
            0.
        ]
        test_consumption_df = pd.DataFrame({"p": test_consumption},
                                           index=pd.date_range(
                                               "2020-01-01 06:00:00",
                                               periods=17,
                                               freq="15min"))
        batt = BS(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            st_type="10kWh_5kW",
            freq="15min",
        )
        timeseries = batt.simulate(control_type="installed_power",
                                   p_kw=test_consumption_df)
        self.assertEqual([
            0.0, -3.0, -2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0,
            3.0, 3.0, 3.0, 3.0
        ], timeseries.values.tolist())

    def test_batt_installed_power(self):
        batt = BS(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            st_type="10kWh_5kW",
            freq="15min",
        )
        test_data = pd.DataFrame(
            {
                "p": [
                    0, 0., 0., 0., 0., 0., 0., 0., 10., 10., 10., 10., 10., 10.,
                    10., 10., -10., -10., -10., -10., -10., -10.,
                    -10., -10., 0, 0., 0., 0., 0., 0., 0., 0.,
                ]
            },
            index=pd.date_range("2020-01-01 06:00:00",
                                periods=32,
                                freq="15min"))
        timeseries = batt.simulate(control_type="installed_power",
                                   p_kw=test_data)
        p_after_result = [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 5.0, 5.0, 5.0, 5.0,
            5.0, 5.0, 5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0,
            -5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        var_bat_result = [
            10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 8.75, 7.5, 6.25,
            5.0, 3.75, 2.5, 1.25, 0.0, 1.25, 2.5, 3.75, 5.0, 6.25, 7.5, 8.75,
            10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        self.assertEqual(timeseries.values.tolist(), p_after_result)
        self.assertEqual(batt.results["var_bat"].tolist(), var_bat_result)

    def test_batt_negative_installed_power(self):
        batt = BS(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            st_type="10kWh_5kW",
            freq="15min",
        )
        test_data = pd.DataFrame(
            {
                "p": [
                    0, 0., 0., 0., 0., 0., 0., 0., 10., 10., 10., 10., 10., 10.,
                    10., 10., -10., -10., -10., -10., -10., -10.,
                    -10., -10., 0, 0., 0., 0., 0., 0., 0., 0.,
                ]
            },
            index=pd.date_range("2020-01-01 06:00:00",
                                periods=32,
                                freq="15min"))
        timeseries = batt.simulate(control_type="negative_installed_power",
                                   p_kw=test_data)
        p_after_result = [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 10.0, 10.0, 10.0,
            10.0, 10.0, 10.0, 10.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0,
            -5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]

        var_bat_result = [
            10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0,
            10.0, 10.0, 10.0, 10.0, 8.75, 7.5, 6.25, 5.0, 3.75, 2.5, 1.25, 0.0, 1.25,
            2.5, 3.75, 5.0, 6.25, 7.5, 8.75, 10.0]

        self.assertEqual(timeseries.values.tolist(), p_after_result)
        self.assertEqual(batt.results["var_bat"].tolist(), var_bat_result)

    def test_batt_production_saving(self):
        batt = BS(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            st_type="10kWh_5kW",
            freq="15min",
        )
        test_data = pd.DataFrame(
            {
                "p": [
                    0, -3., -2., 8., 7., 6., 7., 8., 3., 5., 4., -2., -6., -4.,
                    0., 0., 0.
                ]
            },
            index=pd.date_range("2020-01-01 06:00:00",
                                periods=17,
                                freq="15min"))
        timeseries = batt.simulate(control_type="production_saving",
                                   p_kw=test_data)
        p_after_result = [
            0.0, -3.0, -2.0, 3.0, 2.0, 1.0, 2.0, 3.0,
            0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0]
        var_bat_result = [
            10.0, 10.0, 10.0, 8.75, 7.5, 6.25, 5.0, 3.75,
            3.0, 1.75, 0.75, 1.25, 2.5, 3.5, 3.5, 3.5, 3.5]
        self.assertEqual(timeseries.values.tolist(), p_after_result)
        self.assertEqual(batt.results["var_bat"].tolist(), var_bat_result)


if __name__ == '__main__':

    unittest.main()
