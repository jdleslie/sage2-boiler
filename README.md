# Boiler Telemetry API

This API facilitates access to much of the telemetry data produced by my US Boiler/Burnham Alpine boiler via the 
white "Boiler to Boiler" port. The built-in "Sage2" controller exposes nearly all the data available on the boiler's
LCD display over this interface.

This code works nicely via a cron script (log_phant.py) for my ALP105BW-4T02, but is untested on other models.
