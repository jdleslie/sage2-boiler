# Boiler Telemetry API

This API facilitates access to much of the telemetry data produced by my [US Boiler/Burnham Alpine boiler](http://www.usboiler.net/product/alpine-high-efficiency-condensing-gas-boiler.html) via the 
 "Boiler to Boiler" RJ45 port. The built-in "Sage2" controller exposes nearly all the data available on the boiler's
LCD display over this interface.

This code works well via a cron script (log_phant.py) to log readings from my ALP105BW-4T02 to [data.sparkfun.com](http://data.sparkfun.com), but is untested on other models. A register-scanning routine is included to discover additional registers on other boilers.

## Use Cases
* Debug installation issues, e.g. short cycling
* Track operation and usage

## Reference and Prior Work
* [Mini-Monitor](https://github.com/alanmitchell/mini-monitor/blob/master/readers/sage_boiler.py) contains a simpler [minimalmodbus](http://minimalmodbus.readthedocs.io/)-based API (minimalmodbus supports only Modbus/RTU)
* [Sage2 Controller Modbus Interface Documentation](https://www.ccontrols.com/support/dp/Sage2.doc) (circa 2012)
* [modbus-tk](https://github.com/ljean/modbus-tk) is a uniform Modbus RTU and TCP implementation in python

## Physical Interface

### Boiler
The boiler has two RJ45 ports

| Port  | Protocol | Purpose |
|-------|----------|---------|
| White | [EnviraCom](http://www.google.com/patents/US20080112492) | Suitable for connection to [Sage Zone Control](http://www.usboiler.net/product/sage-zone-control-circulator-panel) panels and a specfic model of Honeywell thermostat ([TH9421C1004](https://customer.honeywell.com/en-US/Pages/Product.aspx?cat=HonECC+Catalog&pid=th9421c1004/U), now obsolete and not available for sale). Be careful connecting to this port as EnviraCom uses 24VAC signalling |
| Black |  RS485 | API access, Boiler to Boiler communication over Modbus/RTU at 38.4kbps |

Both ports are intended to daisy chain multiple controls/boilers together using a bus topology using splitters, e.g. http://www.l-com.com/ethernet-modular-tee-adapter-8x8m-8x8kf-8x8kf

### RS485 Interface
Any RS485 interface should work. Mine is a bare-wire [USB-RS485 FTDI Adapter](http://www.ftdichip.com/Products/Cables/USBRS485.htm) with a suitably crimped RJ45 jack.

### Modbus
The API works with either a directly connected serial interface (via [PySerial](https://github.com/pyserial/pyserial)), or a Modbus/TCP bridge (bridging Modbus over Ethernet makes it easier to develop software without being physically connected to the boiler). [mbusd](https://github.com/3cky/mbusd) or any hardware Modbus/RTU to Modbus/TCP bridge will work.

## Performance
This API accesses the entire array of Modbus registers using a handful of Modbus reads and caches results with a configurable TTL. Reading and reporting all known registers takes a few hundred milliseconds.

## Usage
API contains a `__main__` that dumps current boiler state and illustrates usage:

```
$ python sage_boiler.py localhost
Reading                              Raw  Value                   Units
---------------------------------  -----  ----------------------  -------
Active CH Hysteresis (off)            44  39.9                    F
Active CH Hysteresis (on)             38  38.8                    F
Active CH Operating Point            735  164.3                   F
Active CH Setpoint                   734  164.1                   F
Active DHW Hysteresis (off)           55  41.9                    F
Active DHW Hysteresis (on)            38  38.8                    F
Active DHW Operating Point           795  175.1                   F
Active DHW Setpoint                  767  170.1                   F
Active LL Operating Point           -400  -40                     F
Active LL Sensor                       5  Header Sensor (S5)
Active LL Setpoint                   777  171.9                   F
Active Sensor (CH)                     5  Header Sensor (S5)
Active Sensor (DHW)                    2  Outlet Sensor (S3S4)
Active System Hysteresis (off)        44  39.9                    F
Active System Hysteresis (on)         38  38.8                    F
Active System Operating Point        735  164.3                   F
Active System Sensor                   5  Header Sensor (S5)
Active System Setpoint               734  164.1                   F
Burner State                          12  Run
Cycle Count (Boiler Pump)           2202  2202                    cycles
Cycle Count (Burner)                4270  4270                    cycles
Burner Run Time                     2735  2735                    hours
Cycle Count (CH Pump)                 78  78                      cycles
Cycle Count (DHW Pump)               879  879                     cycles
Demand (CH)                            1  On
Demand (DHW)                           0  Off
Demand (Frost)                         0  Off
Demand (LL)                            0  Off
DHW Priority Timer                     0  0.0                     sec
Firing Rate (Measured)              2555  57                      %
Firing Rate (Requested)             2537  57                      %
Flame Signal                        1305  13.1                    μA
Header Sensor                        735  164.3                   F
Header Sensor State                    1  Normal
Outdoor Sensor                      -122  10.0                    F
Outdoor Sensor State                   1  Normal
Pump Status (Boiler)                 124  On, from burner demand
Pump Status (CH)                     123  Off, not needed
Pump Status (DHW)                    123  Off, not needed
4-20mA Remote Control Input State      2  Open
Requested Rate (CH)                 2537  57                      %
Return Sensor                        719  161.4                   F
Return Sensor State                    1  Normal
Setpoint Source (CH)                   3  Outdoor Reset Setpoint
Setpoint Source (DHW)                  1  CH Setpoint
Setpoint Source (LL)                   1  CH Setpoint
Stack Sensor                         750  167                     F
Stack Sensor State                     1  Normal
Supply Sensor                        795  175.1                   F
Supply Sensor State                    1  Normal
```
