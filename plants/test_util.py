import unittest

from plants.util import htime


class TestUtilMethods(unittest.TestCase):
    def test_duration_suffix(self):
        samples = {
            "17s": 17,
            "2d": 86400 * 2,
            "1w": 86400 * 7,
        }
        for exstr, exval in samples.items():
            self.assertEqual(htime(exstr), exval)

    def test_duration_nosuffix(self):
        self.assertEqual(htime("30"), 30)
