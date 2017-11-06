import struct
import operator
from unicodedata import normalize
from functools import partial

# Uniform Modbus TCP and RTU interface library
from modbus_tk.modbus_rtu import RtuMaster
from modbus_tk.modbus_tcp import TcpMaster
import modbus_tk.defines as cst

# Used to pretty-print data tables (e.g. stdout)
from tabulate import tabulate

# Cache Modbus register values received for a few seconds, which makes for more
# consistent results in complicated scenarios and also avoids waiting for the
# slow serial interface
from cachetools import cachedmethod, TTLCache

# Full fat API for accessing statistics on Burnham/US Boiler Alpine boiler
# using modbus_tk (supports both Modbus/TCP and Modbus/RTU)
#
# Developed and tested to work with my ALP105BW-4T02
#
# References and other work
# * Simpler, minimalmodbus-based: https://github.com/alanmitchell/mini-monitor/blob/master/readers/sage_boiler.py
# * Sage2 Controller Modbus Interface Documentation (circa 2012): https://www.ccontrols.com/support/dp/Sage2.doc

class Sage2Reading(object):
    multiplier, offset = 1, 0
    default_format = '{self.title}: {self.value:d}'
    units = None

    def __init__(self, boiler, register, title, units=None, summary=False):
        self.boiler = boiler
        self.register = register
        self.title = title
        self.summary = summary
        if units:
            self.units = units

    def __format__(self, fmt=None):
        fmt = fmt or self.default_format
        return fmt.format(self=self)

    def __unicode__(self):
        return format(self)

    def __str__(self):
        return normalize('NFKD', format(self)).encode('ascii', 'ignore')

    @property
    def value(self):
        value = self.raw_value * self.multiplier + self.offset
        return int(value) == value and int(value) or round(value, 1)

    @property
    def raw_value(self):
        return self.boiler.read(self.register, 1)

class Sage2FiringRateReading(Sage2Reading):
    units = '%'

    @property
    def value(self):
        "Returns firing rate as a percentage, expressed as a integer 0-100"

        mask = 2**31
        raw_value = self.raw_value

        if raw_value & mask > 0:
            # Once most significant bit is stripped the remainder of register
            # is in tenths of a percent
            value = (raw_value - mask) / 10.0
        else:
            # Magic register containing maximum modulation rate
            max_rpm = self.boiler.read(193, 1)
            value = 100.0 * raw_value / max_rpm

        return int(value)

class Sage2TemperatureReading(Sage2Reading):
    multiplier, offset = 0.18, 32 # Fahrenheit
    #multiplier, offset = 0.1, 0 # Celsius
    default_format = u'{self.title}: {self.value:.1f}'
    units = u'\N{DEGREE SIGN}F'

    @property
    def raw_value(self):
        temperature = super(Sage2TemperatureReading, self).raw_value

        # Docs say these are unsigned 16-bit integers, but temperatures appear
        # to be signed, as described at:
        #
        # http://github.com/alanmitchell/mini-monitor/blob/master/readers/sage_boiler.py
        return temperature > 2**15 and temperature - 2**16 or temperature

class Sage2FlameSignalReading(Sage2Reading):
    multiplier = 0.01
    units = u'\N{MICRO SIGN}A'

class Sage2EnumeratedReading(Sage2Reading):
    default_format = '{self.title}: {self.value}'
    possible_values = {}

    @property
    def raw_value(self):
        "Returns largest matching key within enumeration of possible values"
        raw_value = super(Sage2EnumeratedReading, self).raw_value
        largest_match = lambda x, y: y <= raw_value and y or x
        return reduce(largest_match, sorted(self.possible_values))

    @property
    def value(self):
        "Returns largest matching value from enumeration of possible values"
        return self.possible_values.get(self.raw_value, None)

class Sage2BurnerStateReading(Sage2EnumeratedReading):
    possible_values = {
        0:   'Initiate',
        1:   'Standby Delay',
        2:   'Standby',
        3:   'Safe Startup',
        4:   'Prepurge - Drive to Purge Rate',
        5:   'Prepurge - Measured Purge Time',
        6:   'Prepurge - Drive to Lightoff Rate',
        7:   'Preigition Test',
        8:   'Preigition Time',
        9:   'Pilot Flame Establishing Period',
        10:  'Main Flame Establishing Period',
        11:  'Direct Burner Ignition',
        12:  'Run',
        13:  'Postpurge',
        14:  'Lockout',
        255: 'Safety Processor Offline'
    }

class Sage2SensorStateReading(Sage2EnumeratedReading):
    possible_values = {
        0: 'None',
        1: 'Normal',
        2: 'Open',
        3: 'Shorted',
        4: 'Above High Range',
        5: 'Below Low Range',
        6: 'Not Reliable'
    }

class Sage2ModulationStateReading(Sage2EnumeratedReading):
    possible_values = {
        0: 'No Active Sensor',
        1: 'DHW Sensor (S6S7)',
        2: 'Outlet Sensor (S3S4)',
        3: 'Inlet Sensor (S1)',
        4: '4-20mA Input (S2)',
        5: 'Header Sensor (S5)', # 'S5 Sensor' in Sage2 docs
        6: 'S10 Sensor (S10)',
        7: 'Steam Sensor (S1)'
    }

class Sage2SetpointSourceReading(Sage2EnumeratedReading):
    possible_values = {
        0: 'Unknown',
        1: 'CH Setpoint',
        2: 'CH Time of Day Setpoint',
        3: 'Outdoor Reset Setpoint',
        4: 'Remote Control Setpoint',
        5: 'DHW Tap Setpoint',
        6: 'DHW Preheat Setpoint',
        7: 'Outdoor Reset Time of Day Setpoint',
        8: 'Mix Setpoint'
    }

class Sage2DemandReading(Sage2EnumeratedReading):
    possible_values = {
        0: 'Off',
        1: 'On'
    }

class Sage2PumpStatusReading(Sage2EnumeratedReading):
    # Tables in Sage2 documentation are numbered 7 and 8
    possible_values = {
        92: 'Forced On, from manual pump control',
        93: 'Forced On, due to Outlet high limit is active',
        94: 'Forced On, from burner demand',
        95: 'Forced On, due to Lead Lag slave has demand',
        96: 'Forced Off, from local DHW priority service',
        97: 'Forced Off, from Lead Lag DHW priority service',
        98: 'Forced Off, from Central Heat anti-condensation',
        99: 'Forced Off, from DHW anti-condensation',
        100: 'Forced Off, due to DHW high limit is active',
        101: 'Forced Off, from EnviraCOM DHW priority service',
        102: 'On, due to local CH frost protection is active',
        103: 'On, due to Lead Lag CH frost protection is active',
        104: 'On, due to local DHW frost protection is active',
        105: 'On, due to Lead Lag DHW frost protection is active',
        106: 'On, from local Central Heat demand',
        107: 'On, from Lead Lag Central Heat demand',
        108: 'On, from local DHW demand',
        109: 'On, from Lead Lag DHW demand',
        110: 'On, from local Mix demand',
        111: 'On, from Lead Lag Mix demand',
        112: 'On, from local Central Heat service',
        113: 'On, from Lead Lag Central Heat service',
        114: 'On, from local DHW service',
        115: 'On, from Lead Lag DHW service',
        116: 'On, from local Mix service',
        117: 'On, from Lead Lag Mix service',
        118: 'On, from Lead Lag auxiliary pump X',
        119: 'On, from Lead Lag auxiliary pump Y',
        120: 'On, from Lead Lag auxiliary pump Z',
        121: 'On, but inhibited by pump start delay',
        122: 'On, from pump override',
        123: 'Off, not needed',
        124: 'On, from burner demand',
        125: 'On, from exercise',
        126: 'On, from local Lead Lag service',
        127: 'On, from local Lead Lag pump demand',
    }

class Sage2CounterReading(Sage2Reading):
    @property
    def raw_value(self):
        reg = self.boiler.read(self.register, 2)
        #return reg[0] * 2**8 + reg[1] # unsigned 32-bit result
        return reg


class Sage2Boiler(object):
    def __init__(self, slave=1, host='localhost', port=502, serial=None):
        self.cache = TTLCache(maxsize=128, ttl=10)
        self.__slave = slave

        if serial:
            self.__master = RtuMaster(serial)
        else:
            self.__master = TcpMaster(host, port)
        #self.__master.set_verbose(True)

    def tabulate(self, summary=True):
        import inspect

        def is_reading(prop):
            """"Returns True when prop is a property and value of the property
            is a Sage2Reading"""
            return isinstance(prop, property) \
                and isinstance(prop.__get__(self), Sage2Reading)

        def readings():
            for prop, reading in inspect.getmembers(self.__class__, is_reading):
                # Hack below invokes the property object so the descriptor
                # calls its wrapped get method, (hopefully) returning a
                # Sage2Reading object)
                #
                # https://docs.python.org/2/howto/descriptor.html
                reading = reading.__get__(self)

                if summary and not reading.summary:
                    continue
                yield (reading.title, reading.raw_value, reading.value, reading.units,)
                #yield (reading.title, reading.value, reading.units,)

        return tabulate(readings(), headers=['Reading', 'Raw', 'Value', 'Units'])

    def __unicode__(self):
        return self.tabulate()

    def __str__(self):
        return normalize('NFKD', unicode(self)).encode('ascii', 'ignore')

    def read(self, register, count=1):
        assert count <= 2 and count > 0

        #reg = self.__master.execute(
        #    self.__slave, cst.READ_HOLDING_REGISTERS, register, count)
        reg = self.dump()[register:register+count]

        # Pad 16-bit values with a zero byte
        if len(reg) == 1:
            reg = (0, reg[0],)
        return struct.unpack('>I', struct.pack('>HH', *reg))[0]

    @cachedmethod(operator.attrgetter('cache'))
    def dump(self):
        """Dump all register values in large batches

        Extracting all interesting register values in bulk is up to 12.8x
        faster than accessing each register individually, depending on the
        number registers accessed.

        Returns a tuple of 194 contiguous registers (0-193)
        """
        function_code = cst.READ_HOLDING_REGISTERS # aka "3"
        get = partial(self.__master.execute, *[self.__slave, function_code])

        # Hardcoded register extract for registers 0-177 and 193
        #
        # N.B. Up to 125 registers that can be retrieved in a single request
        return get(0, 100) + get(100, 77) + (None,) * 16 + get(193, 1)

    def identify_valid_registers(self, min, max):
        from operator import itemgetter
        from itertools import groupby

        def register_walk():
            for id in xrange(min, max):
                try:
                    self.__master.execute(self.__slave, cst.READ_HOLDING_REGISTERS, id, 1)
                except:
                    continue
                yield id

        # clever recipe: https://docs.python.org/2.6/library/itertools.html#examples
        ranges = []
        data = register_walk()
        for k, g in groupby(enumerate(data), lambda (i,x):i-x):
            group = map(itemgetter(1), g)
            ranges.append((group[0], group[-1],))
        return ranges
        # Results for scanning registers 0-10000 on my ALP105 boiler
        # [(0, 182), (188, 1122), (1126, 1128), (1132, 1134), (1138, 1140),
        #  (1144, 1146), (1150, 1152), (1156, 1158), (1162, 1164), (1168, 1170),
        #  (1174, 1176), (1180, 1182), (1186, 1188), (1192, 1194), (1198, 1200),
        #  (1204, 1206), (1210, 1344), (1355, 1369), (2048, 2071), (4096, 4108),
        #  (4110, 4122), (4124, 4148), (4152, 4160), (4162, 4177), (8192, 8212),
        #  (9219, 9219), (9222, 9224)]

    @property
    def supply_sensor(self):
        return Sage2TemperatureReading(self, 7, 'Supply Sensor', summary=True)

    @property
    def firing_rate_requested(self):
        return Sage2FiringRateReading(self, 8, 'Firing Rate (Requested)', summary=True)

    @property
    def firing_rate_measured(self):
        return Sage2FiringRateReading(self, 9, 'Firing Rate (Measured)', summary=True)

    @property
    def flame_signal(self):
        return Sage2FlameSignalReading(self, 10, 'Flame Signal')

    @property
    def return_sensor(self):
        return Sage2TemperatureReading(self, 11, 'Return Sensor', summary=True)

    @property
    def header_sensor(self):
        return Sage2TemperatureReading(self, 13, 'Header Sensor', summary=True)

    @property
    def stack_sensor(self):
        return Sage2TemperatureReading(self, 14, 'Stack Sensor', summary=True)

    @property
    def active_ch_setpoint(self):
        return Sage2TemperatureReading(self, 16, 'Active CH Setpoint')

    @property
    def active_dhw_setpoint(self):
        return Sage2TemperatureReading(self, 17, 'Active DHW Setpoint')

    @property
    def active_ll_setpoint(self):
        return Sage2TemperatureReading(self, 18, 'Active LL Setpoint')

    @property
    def active_ch_operating_point(self):
        return Sage2TemperatureReading(self, 25, 'Active CH Operating Point')

    @property
    def active_dhw_operating_point(self):
        return Sage2TemperatureReading(self, 26, 'Active DHW Operating Point')

    @property
    def active_ll_operating_point(self):
        return Sage2TemperatureReading(self, 27, 'Active LL Operating Point')

    @property
    def active_system_operating_point(self):
        return Sage2TemperatureReading(self, 28, 'Active System Operating Point', summary=True)

    @property
    def active_system_setpoint(self):
        return Sage2TemperatureReading(self, 29, 'Active System Setpoint', summary=True)

    @property
    def active_system_on_hysteresis(self):
        return Sage2TemperatureReading(self, 30, 'Active System Hysteresis (on)')

    @property
    def active_system_off_hysteresis(self):
        return Sage2TemperatureReading(self, 31, 'Active System Hysteresis (off)')

    # BURNER CONTROL STATE
    @property
    def burner_state(self):
        return Sage2BurnerStateReading(self, 33, 'Burner State', summary=True)

#    @property
#    def lockout_code(self):
#        pass # 34

#    @property
#    def lockout_code(self):
#        pass # 40

    # SENSOR STATUS
    @property
    def supply_sensor_state(self):
        return Sage2SensorStateReading(self, 48, 'Supply Sensor State')

    @property
    def return_sensor_state(self):
        return Sage2SensorStateReading(self, 49, 'Return Sensor State')

    @property
    def stack_sensor_state(self):
        return Sage2SensorStateReading(self, 51, 'Stack Sensor State')

    @property
    def header_sensor_state(self):
        return Sage2SensorStateReading(self, 52, 'Header Sensor State')

    @property
    def remote_control_input_state(self):
        return Sage2SensorStateReading(self, 53, '4-20mA Remote Control Input State')

    # DEMAND & MODULATION STATUS
    @property
    def active_system_sensor(self):
        return Sage2ModulationStateReading(self, 61, 'Active System Sensor', summary=True)

    @property
    def active_ll_sensor(self):
        return Sage2ModulationStateReading(self, 62, 'Active LL Sensor')

    # CENTRAL HEAT (CH) STATUS
    @property
    def setpoint_source_ch(self):
        return Sage2SetpointSourceReading(self, 65, 'Setpoint Source (CH)')

    @property
    def demand_ch(self):
        return Sage2DemandReading(self, 66, 'Demand (CH)', summary=True)

    @property
    def requested_rate_ch(self):
        return Sage2FiringRateReading(self, 68, 'Requested Rate (CH)', summary=True)

    @property
    def demand_frost(self):
        return Sage2DemandReading(self, 70, 'Demand (Frost)', summary=True)

    @property
    def active_ch_on_hysteresis(self):
        return Sage2TemperatureReading(self, 71, 'Active CH Hysteresis (on)')

    @property
    def active_ch_off_hysteresis(self):
        return Sage2TemperatureReading(self, 72, 'Active CH Hysteresis (off)')

    @property
    def active_sensor_ch(self):
        return Sage2ModulationStateReading(self, 76, 'Active Sensor (CH)')

    # DHW STATUS
    @property
    def active_sensor_dhw(self):
        return Sage2ModulationStateReading(self, 79, 'Active Sensor (DHW)')

    @property
    def setpoint_source_dhw(self):
        return Sage2SetpointSourceReading(self, 81, 'Setpoint Source (DHW)')

    @property
    def dhw_priority_counter(self):
        return Sage2Reading(self, 82, 'DHW Priority Timer', 'sec')

    @property
    def demand_dhw(self):
        return Sage2DemandReading(self, 83, 'Demand (DHW)', summary=True)

    @property
    def active_dhw_on_hysteresis(self):
        return Sage2TemperatureReading(self, 88, 'Active DHW Hysteresis (on)')

    @property
    def active_dhw_off_hysteresis(self):
        return Sage2TemperatureReading(self, 89, 'Active DHW Hysteresis (off)')

    # PUMP STATUS
    @property
    def pump_status_ch(self):
        return Sage2PumpStatusReading(self, 96, 'Pump Status (CH)', summary=True)

    @property
    def pump_status_dhw(self):
        return Sage2PumpStatusReading(self, 100, 'Pump Status (DHW)', summary=True)

    @property
    def pump_status_boiler(self):
        return Sage2PumpStatusReading(self, 108, 'Pump Status (Boiler)', summary=True)

    # STATISTICS
    @property
    def counter_burner(self):
        return Sage2CounterReading(self, 128, 'Cycle Count (Burner)', 'cycles', summary=True)

    @property
    def counter_burner_hours(self):
        return Sage2CounterReading(self, 130, 'Burner Run Time', 'hours', summary=True)

    @property
    def counter_ch_pump(self):
        return Sage2CounterReading(self, 132, 'Cycle Count (CH Pump)', 'cycles', summary=True)

    @property
    def counter_dhw_pump(self):
        return Sage2CounterReading(self, 134, 'Cycle Count (DHW Pump)', 'cycles', summary=True)

    @property
    def counter_boiler_pump(self):
        return Sage2CounterReading(self, 138, 'Cycle Count (Boiler Pump)', 'cycles', summary=True)

    # LEAD LAG STATUS
    @property
    def setpoint_source_ll(self):
        return Sage2SetpointSourceReading(self, 162, 'Setpoint Source (LL)')

    @property
    def demand_ll(self):
        return Sage2DemandReading(self, 164, 'Demand (LL)')

    # EXTENDED SENSOR STATUS
    @property
    def outdoor_sensor(self):
        return Sage2TemperatureReading(self, 170, 'Outdoor Sensor', summary=True)

    @property
    def outdoor_sensor_state(self):
        return Sage2SensorStateReading(self, 171, 'Outdoor Sensor State')

#    Implement this function. PRs welcome!
#
#    @property
#    def software_version(self):
#        "Retrieve variable length OS version"
#        return Sage2Reading(self, 186, 'OS Version', summary=True)


if __name__ == '__main__':
    import serial
    import sys

    # Modbus/TCP bridge can be specified as an argument
    host = len(sys.argv) == 2 and sys.argv[1] or 'localhost'
    boiler = Sage2Boiler(slave=1, host=host, port=502)

    print boiler
