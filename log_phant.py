#!/usr/bin/env python

import requests

from sage_boiler import Sage2Boiler

# Following variables should be set in settings.py
#
#PHANT_PUBLIC_KEY
#PHANT_PRIVATE_KEY
#PHANT_BASE_URL
#
from settings import *

readings_raw_value = ['demand_ch', 'demand_dhw', 'demand_frost']
readings_value = [
    'burner_state',
    'requested_rate_ch',
    'firing_rate_requested',
    'firing_rate_measured',
    'active_system_sensor',
    'active_system_operating_point',
    'active_system_setpoint',
    'outdoor_sensor',
    'header_sensor',
    'supply_sensor',
    'return_sensor',
    'stack_sensor',
    'counter_burner',
    'counter_burner_hours',
    'counter_ch_pump',
    'counter_dhw_pump',
    'counter_boiler_pump',
]

boiler = Sage2Boiler(1, 'localhost', 502)

data = {}
data.update({reg: getattr(boiler, reg).raw_value for reg in readings_raw_value})
data.update({reg: getattr(boiler, reg).value for reg in readings_value})

print requests.post(
    url=PHANT_BASE_URL + '/input/' + PHANT_PUBLIC_KEY,
    headers={'Phant-Private-Key': PHANT_PRIVATE_KEY},
    data=data)
