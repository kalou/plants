## Canbus stuff
*Disclaimer: I'm using this project to learn electronics. Use at your own risks and feel free
to reach out with suggestions.*

### Sensors
Sensors are daisy chained on a low bitrate two-wires BUS
(using CANbus transceiver & protocol, at 20kbps).

Sensor circuit is an attiny85 coupled to an MCP2561.
 * +5v generic sensor + ADC
 * 12v 1A module (e.g. water pump, valve)
 * reset button

![Overview of PCB](./pcb.png)

### CAN on the Pi
I use an MCP2515+TJA1050 module with an 8mhz crystal that talks SPI.
Connecting to Pi:
 * GPIO GPIO25(22) to INT, adding dtoverlay=mcp2515-can0,oscillator=8000000,interrupt=25
 * GPIO8(24) to CS
 * GPIO10(19) to MOSI
 * GPIO9(21) to MISO
 * GPIO11(23) to SCLK

### Hat
Future plans to build a +12v hat integrating CAN ports. Mini-DIN/6 (PS/2) ports?

### AVR programming and setup
On ubuntu linux:
```
sh$ git submodule init && git submodule update
sh$ sudo apt-get install avrdude avr-libc binutils-avr gcc-avr
sh$ cd avr && make && make avr-install
```
