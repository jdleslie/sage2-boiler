#!/usr/bin/python3
"""
Log boiler data to InfluxDB.

Requires the InfluxDB python client library:
  https://github.com/influxdata/influxdb-client-python

It is on PyPI as influxdb-client, e.g. `pip install influxdb-client`

Run with --help to see the available options.
"""

import argparse
from typing import List, Dict

from influxdb_client import InfluxDBClient
from sage_boiler import Sage2Boiler, Sage2Reading


parser = argparse.ArgumentParser(
    description="Log Burnham Alpine (Sage 2) data to InfluxDB."
)
parser.add_argument("--influx_host", default="localhost", help="InfluxDB host.")
parser.add_argument("--influx_port", default=8086, help="InfluxDB port.")
parser.add_argument(
    "--influx_bucket",
    default="boiler/autogen",
    help="InfluxDB bucket (database/retention policy).",
)
parser.add_argument(
    "--influx_measurement", default="alpine", help="InfluxDB measurement name."
)
parser.add_argument("--influx_token", default="", help="InfluxDB API token.")
parser.add_argument("--influx_org", default="", help="InfluxDB org.")
parser.add_argument(
    "--include_raw", default=True, help="Also log raw values under [measurement]_raw."
)
parser.add_argument(
    "--serial_port",
    default="/dev/ttyUSB0",
    help="Modbus serial port, for RTU mode (requires tcp_host to be unset).",
)
parser.add_argument(
    "--tcp_host",
    default="",
    help="Modbus host, for TCP bridge mode (if set, supersedes serial).",
)
parser.add_argument("--tcp_port", default=502, help="Modbus port, for TCP bridge mode.")
parser.add_argument(
    "--summary_only",
    action="store_true",
    help="If set, only record summary data (otherwise, all of it).",
)


def gather_readings(boiler: Sage2Boiler, summary_only=False) -> List[Sage2Reading]:
    readings = []
    for key in dir(boiler):
        attr = getattr(boiler, key)
        if isinstance(attr, Sage2Reading) and (not summary_only or attr.summary):
            readings.append(attr)
    return readings


def _field_name(reading: Sage2Reading) -> str:
    if not reading.units:
        return reading.title
    return f"{reading.title} {reading.units}"


def influx_dict(readings: List[Sage2Reading], measurement: str) -> Dict:
    return {
        "measurement": measurement,
        "fields": {_field_name(reading): reading.value for reading in readings},
    }


def influx_dict_raw(readings: List[Sage2Reading], measurement: str) -> Dict:
    return {
        "measurement": measurement,
        # No units in the field name for raw values.
        "fields": {reading.title: reading.raw_value for reading in readings},
    }


def _get_boiler(args) -> Sage2Boiler:
    # Use TCP bridge if it is set...
    if args.tcp_host:
        return Sage2Boiler(host=args.tcp_host, port=args.tcp_port)

    # ...and serial if not.
    import serial

    return Sage2Boiler(serial=serial.Serial(args.serial_port, baudrate=38400))


def _get_influxdb(args) -> InfluxDBClient:
    return InfluxDBClient(
        url=f"http://{args.influx_host}:{args.influx_port}",
        token=args.influx_token,
        org=args.influx_org,
        timeout=1000 * 60 * 10,
    )


if __name__ == "__main__":
    args = parser.parse_args()
    readings = gather_readings(_get_boiler(args), summary_only=args.summary_only)
    client = _get_influxdb(args)
    with _get_influxdb(args) as client:
        with client.write_api() as write_api:
            write_api.write(
                args.influx_bucket,
                record=influx_dict(readings, args.influx_measurement),
            )
            if args.include_raw:
                write_api.write(
                    args.influx_bucket,
                    record=influx_dict_raw(readings, f"raw_{args.influx_measurement}"),
                )
