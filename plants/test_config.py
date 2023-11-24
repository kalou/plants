import unittest

from plants import config


class TestConfigMethods(unittest.TestCase):
    def test_parse(self):
        conf = config.load("plants/plants.yaml")
        print(conf)
