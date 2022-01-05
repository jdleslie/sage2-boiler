#!/usr/bin/env python

import numbers
import sqlite3
import sys

import sage_boiler

boiler = sage_boiler.Sage2Boiler(1, sys.argv[1])
readings = []
for key in dir(boiler):
	this = getattr(boiler, key)
	if isinstance(this, sage_boiler.Sage2Reading):
		readings.append({
			'boiler': boiler.boiler,
			'register': this.register,
			'raw_value': this.raw_value,
			'numeric_value': this.value \
			                 if   isinstance(this.value, numbers.Number) \
                                         else this.raw_value,
			'title': this.title,
			'value': this.value
		})

db_con = sqlite3.connect('sage_boiler.sqlite3')
db_cur = db_con.cursor()
db_cur.execute('''
	CREATE TABLE IF NOT EXISTS sage2_reading (
		timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		boiler      INTEGER NOT NULL,
		register    INTEGER NOT NULL,
		raw_value   INTEGER NOT NULL,
		value       INTEGER NULL,
		title       TEXT NOT NULL,
		description TEXT NULL
	);
''')

db_cur.executemany('''
	INSERT INTO sage2_reading VALUES (
		CURRENT_TIMESTAMP,
		:boiler,
		:register,
		:raw_value,
		:numeric_value,
		:title,
		:value
	);
''', readings)
db_con.commit()
db_con.close()

print(boiler.tabulate())
