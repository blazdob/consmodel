import unittest
from pv_sim import PV

class TestPV(unittest.TestCase):

    def test_size(self):
        pv = PV(id=1, name="test", lat=46.155768, lon=14.304951, alt=400, TZ="Europe/Vienna")
        year = 2022
        results = pv.simulate(14, year, '15min', model="ineichen", consider_cloud_cover=True)
        self.assertEqual(results.shape[0], 35040)