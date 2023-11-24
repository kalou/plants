import yaml

from plants import util


class Error(Exception):
    pass


class Config(dict):
    def __init__(self, v):
        super().__init__(v)

    @property
    def name(self):
        """Yaml configs often have optionally named lists"""
        if len(self) == 1:
            return list(self.keys())[0]
        raise Error("Excepted module name")

    @property
    def value(self):
        if len(self) == 1:
            return self[self.name]
        raise Error("No or multiple values in conf dict")

    def __getitem__(self, k):
        val = super().__getitem__(k)
        if k.endswith("duration") or k.endswith("interval"):
            return util.htime(val)
        if isinstance(val, list):
            return [Config(x) for x in val]
        if isinstance(val, dict):
            return Config(val)
        if isinstance(val, str):
            if val.endswith("%"):
                return float(val[:-1]) / 100
            return val
        return val

    def get(self, k, default=None):
        if k in self:
            return self[k]
        return default


def load(f):
    return Config(yaml.unsafe_load(open(f, encoding="utf-8")))
