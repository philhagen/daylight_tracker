#!/usr/bin/env python3
# (C)2021 Phil Hagen <phil@lewestech.com>
#
# This script will read a list of records in JSON format that describe one location each.
# It will then determine the sunset and sunrise times for each location and create an "at" job at each of those events.
#
# All clocks are assumed UTC because if they are not, they are wrong.

import time
import requests
import tempfile
import subprocess
import json
import datetime
# these 3 lines are needed for python <3.7
from backports.datetime_fromisoformat import MonkeyPatch
MonkeyPatch.patch_fromisoformat()
import argparse

default_log = '/var/log/city_tracker.log'

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Verbose mode', action='store_true', default=False)
parser.add_argument('-t', '--test', help='Run in test mode - do not create jobs', action='store_true', default=False)
parser.add_argument('-L', '--nolog', dest='log', help='Disable logging', action='store_false', default=True)
parser.add_argument('-f', '--logfile', help='Specify the logfile location if logging is enabled', default=default_log)
args = parser.parse_args()

if args.test:
    args.log = False

cf = open('/etc/sysconfig/city_config.json', 'r')
cities = json.load(cf)
cf.close()

request_headers = { 'user-agent': 'Lego ISS tracker', 'accept': 'application/json' }

current_time = datetime.datetime.now(datetime.timezone.utc)

if args.log:
    logfile = open(args.logfile, 'a')
    
logtime = datetime.datetime.utcnow().isoformat()

for city in cities:
    city_name = city['name']
    latitude = city['latitude']
    longitude = city['longitude']
    lights = city['lights']

    city_sun_url = 'https://api.sunrise-sunset.org/json?lat=%f&lng=%f&formatted=0' % (latitude, longitude)

    city_sun_data = requests.get(city_sun_url, headers=request_headers)
    city_object = city_sun_data.json()['results']

    sunrise = datetime.datetime.fromisoformat(city_object['sunrise'])
    sunset = datetime.datetime.fromisoformat(city_object['sunset'])

    time_to_sunrise = sunrise - current_time
    time_to_sunset = sunset - current_time

    if time_to_sunrise.total_seconds() < 0 or time_to_sunset.total_seconds() < 0:
        city_sun_url = 'https://api.sunrise-sunset.org/json?lat=%f&lng=%f&formatted=0&date=tomorrow' % (latitude, longitude)

        city_sun_data_tomorrow = requests.get(city_sun_url, headers=request_headers)
        city_object_tomorrow = city_sun_data_tomorrow.json()['results']

        if time_to_sunrise.total_seconds() < 0:
            sunrise = datetime.datetime.fromisoformat(city_object_tomorrow['sunrise'])
            time_to_sunrise = sunrise - current_time

        if time_to_sunset.total_seconds() < 0:
            sunset = datetime.datetime.fromisoformat(city_object_tomorrow['sunset'])
            time_to_sunset = sunset - current_time

    for light in lights:
        if args.verbose:
            print('%s Turning %s:%s on at %s (%d min) and off at %s (%d min)' % (logtime, city_name, light, sunset.isoformat(), int(time_to_sunset.total_seconds()/60), sunrise.isoformat(), int(time_to_sunrise.total_seconds()/60)))

        if args.log:
            logfile.write('%s %s:%s Turning on at %s and off at %s\n' % (logtime, city_name, light, sunset.isoformat(), sunrise.isoformat()))


        if not args.test:
            fh1 = tempfile.TemporaryFile()
            fh1.write(bytes('/usr/local/bin/homeScript.py -s %s 0' % (light), 'utf-8'))
            fh1.seek(0)
            fh2 = tempfile.TemporaryFile()
            fh2.write(bytes('/usr/local/bin/homeScript.py -s %s 1' % (light), 'utf-8'))
            fh2.seek(0)

            subprocess.run(['at', '-M', 'now', '+', str(int(time_to_sunrise.total_seconds()/60)), 'minutes'], stdin=fh1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['at', '-M', 'now', '+', str(int(time_to_sunset.total_seconds()/60)), 'minutes'], stdin=fh2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            fh1.close()
            fh2.close()

if args.log:
    logfile.close()
