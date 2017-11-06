#!/usr/bin/env python

import thingspeak
from settings import *

from sage_boiler import Sage2Boiler

boiler = Sage2Boiler(1, "localhost", 502)

demand_sources = {
	"demand_ch": "heat",
	"demand_dhw": "dhw",
	"demand_frost": "frost",
}
demand = [alias for reg, alias in demand_sources.items() if getattr(boiler, reg).raw_value]

registers = [
	"counter_burner",
	"firing_rate_measured",
	" ".join(demand),
	"supply_sensor",
	"return_sensor",
	"stack_sensor",
	"header_sensor",
	"outdoor_sensor",
]
fields = range(1, len(registers) + 1)
readings = {i: getattr(boiler, reg, reg) for reg, i in zip(registers, fields)} 
readings = {k: hasattr(v, "value") and v.value or v for k, v in readings.items()}

# Fix overflow (>100%) when burner is off
readings[2] = readings[2] > 100 and 0

chan = thingspeak.Channel(id=CHANNEL_ID, write_key=WRITE_KEY)

#try:
response = chan.update(readings)
#print response
#except:
#	print "Thingspeak connection failed"

