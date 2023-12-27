import unittest
import pandas as pd
from consmodel.cons_sim import ConsumerModel


class TestConsumerModel(unittest.TestCase):

    def test_empty_result(self):
        cons = ConsumerModel(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            name="ConsumerModel_default",
            tz="Europe/Ljubljana",
            use_utc=False,
            freq="15min",
        )
        timeseries = cons.simulate(
            has_generic_consumption=False,
            has_pv=False,
            has_heatpump=False,
            has_ev=False,
            has_battery=False,
            start=pd.to_datetime("2020-01-01 06:00:00"),
            end=pd.to_datetime("2020-01-01 06:00:00") + pd.Timedelta("1d"),
            year=None,
        )
        self.assertEqual(timeseries.sum(), 0)

    def test_hp_result(self):
        cons = ConsumerModel(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            name="ConsumerModel_default",
            tz="Europe/Ljubljana",
            use_utc=False,
            freq="10min",
        )
        timeseries = cons.simulate(
            has_generic_consumption=False,
            has_pv=False,
            has_heatpump=True,
            has_ev=False,
            has_battery=False,
            start=pd.to_datetime("2020-01-01 07:15:00"),
            end=pd.to_datetime("2020-01-01 07:00:00") + pd.Timedelta("1d"),
            year=None,
        )
        self.assertEqual(round(timeseries.sum(), 2), 226.58)

    def test_pv_generation_round(self):
        cons = ConsumerModel(
            lat=46.155768,
            lon=14.304951,
            alt=400,
            index=1,
            name="ConsumerModel_default",
            tz="Europe/Ljubljana",
            use_utc=False,
            freq="15min",
        )
        timeseries = cons.simulate(
            has_generic_consumption=False,
            has_pv=True,
            has_heatpump=False,
            has_ev=False,
            has_battery=False,
            start=pd.to_datetime("2020-01-01 06:15:00"),
            end=pd.to_datetime("2020-01-01 06:00:00") + pd.Timedelta("1d"),
            year=None,
            pv_size=14.,
        )
        self.assertLessEqual(round(timeseries.sum(), 2), -0)
        self.assertLessEqual(round(timeseries.sum(), 2), -150)
        self.assertGreaterEqual(round(timeseries.sum(), 2), -200)
