import unittest
from consmodel.pv_sim import PV
import os
import pandas as pd

class TestPV(unittest.TestCase):

    def test_size_year(self):
        # create a simple PV model
        pv = PV(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    name="test",
                    tz="Europe/Vienna",
                    freq="15min",)
        timeseries = pv.simulate(pv_size=14.,
                                year=2022,
                                model="ineichen",
                                consider_cloud_cover=True)
        self.assertEqual(len(timeseries), 35040)

    def test_size_start_end(self):
        # create a simple PV model
        pv = PV(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    name="test",
                    tz="Europe/Vienna",
                    freq="15min",)
        timeseries = pv.simulate(pv_size=14.,
                                start=pd.to_datetime("2021-01-01 06:15:00"),
                                end=pd.to_datetime("2022-01-01 06:00:00"),
                                model="ineichen",
                                consider_cloud_cover=True)
        self.assertEqual(len(timeseries), 35040)