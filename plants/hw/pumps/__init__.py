import dataclasses
import time

import sqlite3
from gpiozero import LED
from prometheus_client import Counter

from plants import config, history

pump_seconds = Counter("plants_pump_seconds", "Seconds of pump activation", ["pump_id"])

registry = {}


@dataclasses.dataclass
class Pump:
    name: str
    config: config.Config
    usage: dict

    def __init__(self, name, config, history_manager):
        self.name = name
        self.config = config
        self.history = history_manager.history_for(self)

    def __repr__(self):
        return f"pump@{self.name}"

    @property
    def usage(self):
        return dict(
            (x["per_interval"], self.history.total_up_to(x["per_interval"]))
            for x in self.limits
        )

    @property
    def limits(self):
        return self.config.get("limits", [{"per_interval": 86400, "duration": 60}])

    @property
    def activation_thresholds(self):
        return dict((c.name, c.value) for c in self.config["activation_thresholds"])

    def _do_water(self, duration):
        print(f"Pump {self} on for {duration}")
        self.history.add(duration)
        # Cleanup history that doesn't matter anymore
        max_window = max(x["per_interval"] for x in self.limits)
        self.history.forget_up_to(max_window)

        pump_seconds.labels(self.name).inc(duration)
        self.on()
        time.sleep(duration)
        self.off()
        print(f"Pump {self} off")

    def water(self, duration=None, force=False, dry_run=False):
        if not duration:
            duration = self.config["duration"]
        allowed = duration

        # Check if we're above limits
        for limit in self.limits:
            total_sofar = self.history.total_up_to(limit["per_interval"])
            allowed = min(allowed, limit["duration"] - total_sofar)
            if not force and allowed <= 0:
                print(f"Inhibiting {self}, reached {limit}")
                return False

        # Water for duration
        if not dry_run:
            if force:
                allowed = duration
                print(f"{self} watering forced")
            self._do_water(allowed)
        return True

    def on(self):
        raise NotImplementedError

    def off(self):
        raise NotImplementedError


class GPIOPump(Pump):
    def __init__(self, name, config, history_manager):
        super().__init__(name, config, history_manager)
        self.gpio = LED(config["port"])

    # def __del__(self):
    #    """Gpiozero takes care of cleaning up the GPIO state,
    #    turning them into inputs, so this isn't required here"""
    #    self.off()

    def on(self):
        self.gpio.on()

    def off(self):
        self.gpio.off()


registry["gpio"] = GPIOPump


class MockGPIOPump(Pump):
    def on(self):
        pass

    def off(self):
        pass


registry["mock-gpio"] = MockGPIOPump
