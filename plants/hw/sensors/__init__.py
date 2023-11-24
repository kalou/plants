__all__ = ["ads1115", "chirp"]

registry = {}


class SensorGroup:
    def poll(self):
        ret = dict((x.kind, {}) for x in self.sensors)
        for s in self.sensors:
            ret[s.kind].update({s.name: s.read(self)})
        return ret
