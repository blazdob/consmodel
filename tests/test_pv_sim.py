import unittest
from consmodel.pv_sim import PV
import os

class TestPV(unittest.TestCase):

    def test_size(self):
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
