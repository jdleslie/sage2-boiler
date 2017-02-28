# Boiler Telemetry API

This API facilitates access to much of the telemetry data produced by my [US Boiler/Burnham Alpine boiler](http://www.usboiler.net/product/alpine-high-efficiency-condensing-gas-boiler.html) via the 
 "Boiler to Boiler" RJ45 port. The built-in "Sage2" controller exposes nearly all the data available on the boiler's
LCD display over this interface.

This code works well via a cron script (log_phant.py) to log readings from my ALP105BW-4T02 to [data.sparkfun.com](http://data.sparkfun.com), but is untested on other models. A register-scanning routine is included to discover additional registers on other boilers.

## Use Cases
* Debug installation issues, e.g. short cycling
* Track operation and usage

## Prior Work
* [Mini-Monitor](https://github.com/alanmitchell/mini-monitor/blob/master/readers/sage_boiler.py) contains a simpler [minimalmodbus](http://minimalmodbus.readthedocs.io/)-based API (minimalmodbus supports only Modbus/RTU)
* [Sage2 Controller Modbus Interface Documentation](https://www.ccontrols.com/support/dp/Sage2.doc) (circa 2012)

## Physical Interface

### Boiler
The boiler has two RJ45 ports

| Port  | Protocol | Purpose |
|-------|----------|---------|
| White | 24VAC [EnviraCom](http://www.google.com/patents/US20080112492) | Suitable for connection to [Sage Zone Control](http://www.usboiler.net/product/sage-zone-control-circulator-panel) panels and Honeywell Thermostats |
| Black |  Modbus/RTU | API access, Boiler to Boiler communication over RS485 at 38.4kbps |

Both ports are intended to daisy chain multiple controls/boilers together using a bus topology using splitters, e.g. http://www.l-com.com/ethernet-modular-tee-adapter-8x8m-8x8kf-8x8kf

### RS485 Interface
Any RS485 interface should work. Mine is a bare-wire [USB-FTDI RS485 Adapter](http://www.ftdichip.com/Products/Cables/USBRS485.htm) with a suitably crimped RJ45 jack.

### Modbus
The API works with either a directly connected serial interface (via [PySerial](https://github.com/pyserial/pyserial)), or a Modbus/TCP bridge (bridging Modbus over Ethernet makes it easier to develop software without being physically connected to the boiler). [mbusd](https://github.com/3cky/mbusd) or any hardware Modbus/RTU to Modbus/TCP bridge will work.

## Performance
This API accesses the entire array of Modbus registers using a handful of Modbus reads and caches results with a configurable TTL. Reading and reporting all known registers takes a few hundred milliseconds.
