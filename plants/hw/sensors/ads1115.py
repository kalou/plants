from dataclasses import dataclass
import time

from prometheus_client import Gauge
from gpiozero import LED

from plants import config
from plants.hw import ads1115
from plants.hw import sensors

metric_moisture_volts = Gauge(
    "plants_ads1115_sensor_volts", "Moisture per sensor volts", ["sensor_id"]
)


# We abuse dataclass along this project to provide somewhat
# automatic json serialization.
@dataclass
class Sensor:
    config: config.Config
    kind: str
    name: str
    cur_v: float
    min_v: float
    max_v: float
    moisture_ratio: float

    def __init__(self, name, config):
        print(f"Initializing sensor {name}")
        self.kind = "moisture"
        self.name = name
        self.config = config
        self.cur_v = None
        self.min_v = config["voltage_wet"]
        self.max_v = config["voltage_dry"]
        self.port = config["port"]

    @property
    def moisture_ratio(self):
        if self.cur_v:
            return (self.max_v - self.cur_v) / (self.max_v - self.min_v)

    def read(self, group):
        """Reads ADC. Returns moisture (as fraction), or None if
        exception"""
        try:
            self.cur_v = group.adc.single_shot_read_gnd(self.port)
            metric_moisture_volts.labels(self.name).set(self.cur_v)
            # Moisture is wet ratio (1=wet)
            return (self.max_v - self.cur_v) / (self.max_v - self.min_v)
        except Exception as e:
            print(f"Caught {e} reading ADC")


# Eventually other types?
sensor_cls = {"moisture": Sensor}


@dataclass
class SensorGroup(sensors.SensorGroup):
    sensors: list[Sensor]

    def __init__(self, config):
        self.adc = ads1115.ADC(config.get("smbus", 1), config.get("i2c_address", 72))
        self.port = None
        if config.get("enable_port"):
            self.port = LED(config["enable_port"])
        self.sensors = []
        for sensor in config["sensors"]:
            self.sensors.append(
                sensor_cls[sensor.get("type", "moisture")](sensor.name, sensor.value)
            )

    def poll(self):
        if self.port:
            self.port.on()
            time.sleep(1)
        ret = super().poll()
        if self.port:
            self.port.off()
        return ret


sensors.registry["ads1115"] = SensorGroup


class MockGPIO:
    def on(self):
        pass

    def off(self):
        pass


class MockAdc:
    def single_shot_read_gnd(self, port):
        return 1.7 + port / 5


class MockSensorGroup(SensorGroup):
    """Same with no GPIO or ADC"""

    def __init__(self, config):
        self.sensors = []
        self.port = MockGPIO()
        self.adc = MockAdc()
        for sensor in config["sensors"]:
            self.sensors.append(Sensor(sensor.name, sensor.value))


sensors.registry["mock-ads1115"] = MockSensorGroup
