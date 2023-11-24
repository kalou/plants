#!/usr/bin/python

import smbus
import time

# Valid addresses for ads1115
# Address[0] is with address pin to GND
addresses = [0b1001000, 0b1001001, 0b1001010, 0b1001011]


class Register:
    CONVERSION = 0
    CONFIG = 1
    LO_THRESH = 2
    HI_THRESH = 3


class Config:
    """
    Usage: Config.read(0) | Config.
    """

    # For ref from datasheet
    COMP_QUEUE = 0  # Comparator queue and disable - Requires setting
    # LO_THRESH and HI_THRESH registers.
    # 00: assert after one conversion, pin gets high after N comparisons
    # exceed the threshold
    # 01: after two
    # 10: after four
    # 11: disabled - pin is always high state
    COMP_LAT = 2  # latching comparator (alert/rdy latches at conversions)
    COMP_POL = 3  # comparator polarity (0: active low, 1: high)
    COMP_MODE = 4  # 0: traditional with hysteresis, 1: window
    DR = (
        5  # [7:5] Data rate for continuous: 0=8sps to 111=860sps - default 100 = 128s/s
    )
    DR_MASK = 7
    dr_to_rate = {0: 8, 1: 16, 2: 32, 3: 64, 4: 128, 5: 250, 6: 475, 7: 860}

    MODE = 8  # 1: single shot - 0: continuous conversion
    PGA = 9  # [11:9] PGA and amplifier config.
    PGA_MASK = 7
    pga_to_volts = {
        0: 6.144,
        1: 4.096,
        2: 2.048,
        3: 1.024,
        4: 0.512,
        5: 0.256,
        6: 0.256,
        7: 0.256,
    }

    MUX = 12  # [12:14] with ref to GND:
    # Esp 100 to 111 is AINx and GND
    OS = 15  # 0: no effect - 1: single conversion

    def __init__(self, value):
        self.value = value

    def to_bytes(self):
        return [(self.value >> 8) & 0xFF, self.value & 0xFF]

    @classmethod
    def from_bytes(self, b):
        return Config(int.from_bytes(b, byteorder="big"))

    @classmethod
    def single_shot_read_gnd(cls, x=0):
        """Emit config register to read single value from port AINx"""
        return Config(
            (1 << cls.OS)
            | ((0b100 | x) << cls.MUX)
            | (1 << cls.PGA)
            | (0b100 << cls.DR)  # 4.096v FSR
            | (1 << cls.MODE)  # DR=128 samples/second
            | (0b11 << cls.COMP_QUEUE)
        )

    def delay(self):
        return 1 / self.dr_to_rate[(self.value >> self.DR) & self.DR_MASK]

    def volts_range(self):
        return self.pga_to_volts[(self.value >> self.PGA) & self.PGA_MASK]

    def __eq__(self, other):
        return self.value == other.value

    def __repr__(self):
        return bin(self.value)


class ADC:
    def __init__(self, smbus_id, address):
        self.bus = smbus.SMBus(smbus_id)
        self.address = address

    def write_config(self, config):
        self.bus.write_i2c_block_data(self.address, Register.CONFIG, config.to_bytes())

    def read_config(self, wait_for=None):
        attempts = 0

        while conf := Config.from_bytes(
            self.bus.read_i2c_block_data(self.address, Register.CONFIG, 2)
        ):
            if not wait_for or (conf == wait_for):
                break
            time.sleep(wait_for.delay())
            attempts += 1
            if attempts > 3:
                raise Exception("Slow read %s!=%s" % (conf, wait_for))

        return conf

    def single_shot_read_gnd(self, x):
        # Write to config register
        config = Config.single_shot_read_gnd(x)
        self.write_config(config)

        # Check it's there
        conf = self.read_config(wait_for=config)

        # Read conversion register (two bytes, MSB/LSB)
        reg = self.bus.read_i2c_block_data(self.address, Register.CONVERSION, 2)

        # This is a 16 bits signed adc
        return (
            conf.volts_range()
            * int.from_bytes(reg, byteorder="big", signed=True)
            / 32768
        )


if __name__ == "__main__":
    print("Test write for read-ain0 is %s\n", bin(Config.single_shot_read_gnd(0)))
