from dataclasses import dataclass
import time

import smbus
from prometheus_client import Gauge

from plants import config
from plants.hw import sensors

metric_moisture_cap = Gauge(
    "plants_chirp_sensor_capacitance", "Capacitance value", ["sensor_id"]
)
metric_temperature = Gauge(
    "plants_chirp_sensor_temperature", "Temperature in Celsius", ["sensor_id"]
)


class Register:
    GET_CAPACITANCE = 0x00  # (r) 2
    SET_ADDRESS = 0x01  # (w) 1
    GET_ADDRESS = 0x02  # (r) 1
    MEASURE_LIGHT = 0x03  # (w) 0
    GET_LIGHT = 0x04  # (r) 2
    GET_TEMPERATURE = 0x05  # (r) 2
    RESET = 0x06  # (w) 0
    GET_VERSION = 0x07  # (r) 1
    SLEEP = 0x08  # (w) 0
    GET_BUSY = 0x09  # (r) 1


class Sensor:
    pass


@dataclass
class MoistureSensor(Sensor):
    config: config.Config
    kind: str
    name: str
    cur_c: int
    max_c: int
    min_c: int

    def __init__(self, name, config):
        self.kind = "moisture"
        self.config = config
        self.name = name
        self.cur_c = None
        self.max_c = config.get("cap_wet", 500)
        self.min_c = config.get("cap_dry", 250)

    def read(self, group):
        try:
            self.cur_c = int.from_bytes(
                group.bus.read_i2c_block_data(
                    group.address, Register.GET_CAPACITANCE, 2
                ),
                byteorder="big",
            )
            metric_moisture_cap.labels(self.name).set(self.cur_c)
            return (self.cur_c - self.min_c) / (self.max_c - self.min_c)
        except Exception as e:
            print(f"Caught {e} reading c from {self}")


@dataclass
class TemperatureSensor(Sensor):
    config: config.Config
    kind: str
    name: str
    temp: float

    def __init__(self, name, config):
        self.kind = "temperature"
        self.name = name
        self.config = config
        self.temp = None

    def read(self, group):
        try:
            self.temp = (
                int.from_bytes(
                    group.bus.read_i2c_block_data(
                        group.address, Register.GET_TEMPERATURE, 2
                    ),
                    byteorder="big",
                )
                / 10.0
            )
            metric_temperature.labels(self.name).set(self.temp)
            return self.temp
        except Exception as e:
            print(f"Caught {e} reading temp from {self}")


@dataclass
class SensorGroup(sensors.SensorGroup):
    sensors: list[Sensor]

    def __init__(self, config):
        self.address = config.get("i2c_address", 0x20)
        bus = config.get("i2c_bus", 1)
        self.name = config.get("name", f"chirp@{bus}:{self.address}")
        self.bus = smbus.SMBus(bus)
        self.sensors = [
            TemperatureSensor(f"temp-{self.name}", config),
            MoistureSensor(self.name, config),
        ]

    def __repr__(self):
        return self.name


sensors.registry["chirp"] = SensorGroup
