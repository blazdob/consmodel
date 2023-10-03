import unittest
import pandas as pd
from consmodel.hp_sim import HP

class TestHP(unittest.TestCase):

    def test_sum(self):
        hp = HP(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    index=1,
                    st_type="Generic",
                    st_subtype="Outdoor Air / Water (regulated)")
        timeseries = hp.simulate(wanted_temp=45,
                                hp_type="Generic",
                                hp_subtype="Outdoor Air / Water (regulated)",
                                year = 2022,)
        self.assertEqual(timeseries.sum(), 61195.29329676784)