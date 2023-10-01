import unittest
from consmodel import PV
import os

class TestPV(unittest.TestCase):

    def test_size(self):
        from consmodel import PV
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt

        # create a simple PV model
        pv = PV(lat=46.155768,
                    lon=14.304951,
                    alt=400,
                    id=1,
                    name="test",
                    TZ="Europe/Vienna")
        timeseries = pv.simulate(pv_size=14.,
                                year=2022,
                                freq="15min",
                                model="ineichen",
                                consider_cloud_cover=True)
        self.assertEqual(len(timeseries), 35040)
