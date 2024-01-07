# Plants
*Plants monitoring and watering*

## Description

Plants is composed of:
* A sensor monitoring system and water pumps controller, written in Python, that
  runs on Linux, likely a Pi:
* Some [hardware](./hw) including a Raspberry Pi hat, switches and sensors.

## Features
### Supported sensors
* Support for ADS1115 ADC, to read voltage level sensors such as standard 555-based capacitive moisture sensors.
* Support for [chirp](https://github.com/Miceuz/i2c-moisture-sensor) i2c sensors, reading temperature and moisture.
### Watering
* Configuration and rule based watering:
  - Triggering watering based on sensor humidity percentage.
  - Watering limits per pump, persisted to disk.
* API to manually trigger watering.
### Metrics
* Export of sensor and pump data metrics to prometheus.
* API to poll running config and basic values.
## Example configuration
```
# Plants configuration

# For prometheus, and API, listen on public interface:
host: 0.0.0.0
port: 9191

# How frequently to poll
poll_interval: 5s

sensor_groups:
  -
    kind: 'chirp'   # Got a chirp for temp metrics
  -
    kind: 'ads1115'
    smbus: 1             # i2c BUS to reach the board, default 1 on rpi
    i2c_address: 72      # Address of the ADS1115
    enable_port: 9       # GPIO turning the group on
    sensors:
      - Dragon tail: &cap_sensor
          voltage_dry: 2.62 # This model has a better oscillator
          voltage_wet: 1.23 # and calibrates differently.
          port: 2
      #- Sensor 1: &bad555_cap_sensor
      #    <<: *cap_sensor
      #    voltage_dry: 2.05  # Than this one, where they used an
      #    voltage_wet: 0.95  # ne555.
      #    port: 2
      - Willows:
          <<: *cap_sensor
          port: 3
      - Small money trees:
          <<: *cap_sensor
          port: 1
      - Pothos:
          <<: *cap_sensor
          port: 0
  -
    kind: 'ads1115'
    smbus: 1             # i2c BUS to reach the board, default 1 on rpi
    i2c_address: 72      # Address of the ADS1115
    enable_port: 11      # GPIO turning the group on
    sensors:
      - Money tree:
          <<: *cap_sensor
          port: 3
      - Lemon tree:
          <<: *cap_sensor
          port: 2
      - Bonsai soil:
          <<: *cap_sensor
          port: 1
      - Parlor palm:
          <<: *cap_sensor
          port: 0

# If configured, pump history is saved across restarts
# in sqlite3 db. Otherwise, in-memory watering limits
# are used.
pumps_history_db: /var/lib/plants/plants_pumps_state.db

pumps:
  - Plants to the left:    # Pump 0
      kind: 'gpio'
      port: 10             # GPIO port activates pump on high
      duration: 20s        # Activate for 20s
      limits: &pump_limits
        - per_interval: 2w
          duration: 40s
        - per_interval: 300s
          duration: 20s
      activation_thresholds:
        - Money tree: 50% 
        - Pothos: 50% 
  - Shelf 1:               # Pump 1
      kind: 'gpio'
      port: 17
      duration: 20s
      limits: *pump_limits
      activation_thresholds:
        - Small money trees: 50%
        - Parlor palm: 50% 
  - Dragon tail:
      kind: 'gpio'         # Pump 2
      port: 22             # GPIO port activates pump on high
      duration: 20s
      limits: *pump_limits
      activation_thresholds:
        - Dragon tail: 50%  
  - Shelf 2:               # Pump 3 
      kind: 'gpio'
      port: 27             # GPIO port activates pump on high
      duration: 20s
      limits: *pump_limits
      activation_thresholds:
        - Lemon tree: 50%
        - Willows: 60%
```

## Developement
### Setup and local experiments
```
bash$ pip install -r requirements.txt
bash$ pip install --editable .
bash$ plants_server -c plants/plants.yaml
```
### Various helpers
```
bash$ python -m unittest discover plants
bash$ black plants # auto format
bash$ pylint plants
```
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
