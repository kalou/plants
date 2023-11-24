"""This module forks a main loop thread, talking to hardware, serializing
access to it through a queue, owning a few metrics. Sqlite connections also
like being used from a single thread."""

import queue
import time
import threading
import typing

from prometheus_client import Gauge

from plants.history import HistoryManager
from plants.hw import pumps, sensors

# This import style to populate registry
# pylint: disable=wildcard-import,unused-wildcard-import
from plants.hw.pumps import *
from plants.hw.sensors import *

sensor_metrics = {
    "temperature": Gauge("plants_temp_celsius", "Temperature", ["sensor_id"]),
    "moisture": Gauge(
        "plants_moisture_ratio", "Moisture per sensor ([0..1])", ["sensor_id"]
    ),
}


# Producer messages for queue:
class Water(typing.NamedTuple):
    pump: Pump
    duration: int = None
    force: bool = None


class Gardener:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, conf):
        self.running = True
        self.last_poll = {}
        self.sensor_groups = []
        self.pumps = []
        self.queue = queue.Queue()
        self.config = conf
        self.thread = None
        self.history_manager = None

    def start_thread(self):
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def setup_thread_from_config(self):
        self.history_manager = HistoryManager(self.config)

        for conf in self.config["sensor_groups"]:
            try:
                sensor_cls = sensors.registry[conf["kind"]]
            except KeyError as exc:
                raise config.Error(
                    "Invalid sensor group type " f"{conf['kind']}"
                ) from exc
            self.sensor_groups.append(sensor_cls(conf))

        for p in self.config["pumps"]:
            try:
                pump_cls = pumps.registry[p.value["kind"]]
            except KeyError as exc:
                raise config.Error(
                    "Invalid pump type " f"{p.value['kind']} for {p.name}"
                ) from exc
            self.pumps.append(pump_cls(p.name, p.value, self.history_manager))

    # Queue producers:
    def water(self, pump, duration=None, force=False):
        if pump.water(duration, force, dry_run=True):
            self.queue.put(Water(pump, duration, force))
            return True
        return False

    # Our only queue consumer is the main loop.
    def loop(self):
        self.setup_thread_from_config()

        while self.running:
            last_poll = {}
            for s in self.sensor_groups:
                for sensor_type, measures in s.poll().items():
                    last_poll.setdefault(sensor_type, {}).update(measures)
            # Plot metrics
            for sensor_type, measures in last_poll.items():
                for label, value in measures.items():
                    if value is not None:
                        sensor_metrics[sensor_type].labels(label).set(value)
            # Export a summary for API
            self.last_poll = {"time": time.time(), "result": last_poll}
            # Check which pumps should activate
            for p in self.pumps_to_activate(last_poll):
                self.queue.put(Water(p))

            # Consume from queue: process commands.
            try:
                while msg := self.queue.get_nowait():
                    if isinstance(msg, Water):
                        msg.pump.water(msg.duration, msg.force)
            except queue.Empty:
                pass

            # Wait until next cycle
            next_poll = time.time() + self.config["poll_interval"]
            while time.time() < next_poll and self.running:
                time.sleep(0.1)
        print("Gardener exited")

    def pumps_to_activate(self, poll):
        """Check if pump activation rules triggered."""
        for p in self.pumps:
            if all(
                poll["moisture"][s] and poll["moisture"][s] < p.activation_thresholds[s]
                for s in p.activation_thresholds
            ):
                print(f"{p} triggered on {poll}")
                yield p

    def exit(self):
        self.running = False
        self.thread.join()
