# Boiler Telemetry API

This API facilitates access to much of the telemetry data produced by my US Boiler/Burnham Alpine boiler via the 
white "Boiler to Boiler" port. The built-in "Sage2" controller exposes nearly all the data available on the boiler's
LCD display over this interface.

This code works nicely via a cron script (log_phant.py) for my ALP105BW-4T02, but is untested on other models.

## Use Cases
* Debug installation issues, e.g. short cycling
* Track operation and usage

## Physical Interface

### Boiler
The boiler has two RJ45 ports

1. 24V EnviraCom interface suitable for connection to Sage Zone Control panels (white)
2. RS485 interface for Modbus/RTU communication between boilers (black)

Both ports are intended to daisy chain multiple controls/boilers together using a bus topology using splitters, e.g. http://www.l-com.com/ethernet-modular-tee-adapter-8x8m-8x8kf-8x8kf

### RS485 Interface
Any RS485 interface should work. Mine is a bare-wire [USB-FTDI RS485 Adapter](http://www.ftdichip.com/Products/Cables/USBRS485.htm) with a suitably crimped RJ45 jack.

### Modbus
The API works with either a directly connected serial interface (via [PySerial](https://github.com/pyserial/pyserial)), or a Modbus/TCP bridge (bridging Modbus over Ethernet makes it easier to develop software without being physically connected to the boiler). [mbusd](https://github.com/3cky/mbusd) or any hardware Modbus/RTU to Modbus/TCP bridge will work.
