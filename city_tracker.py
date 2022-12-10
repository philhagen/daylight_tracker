#!/usr/bin/env python3
# (C)2022 Phil Hagen <phil@lewestech.com>
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
import sys
import argparse

if (sys.version_info.major + (sys.version_info.minor * .1)) < 3.7:
    # these 3 lines are needed for python <3.7
    from backports.datetime_fromisoformat import MonkeyPatch
    MonkeyPatch.patch_fromisoformat()

default_log = '/var/log/city_tracker.log'

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Verbose mode', action='store_true', default=False)
parser.add_argument('-t', '--test', help='Run in test mode - do not create jobs', action='store_true', default=False)
parser.add_argument('-L', '--nolog', dest='log', help='Disable logging', action='store_false', default=True)
parser.add_argument('-f', '--logfile', help='Specify the logfile location if logging is enabled', default=default_log)
args = parser.parse_args()

# never log in test mode
if args.test:
    args.log = False

# load a JSON-formatted list of cities and their respective latitudes and longitudes
cf = open('/etc/sysconfig/daylight_tracker_config.json', 'r')
cities = json.load(cf)['cities']
cf.close()

# set the request headers for API interactions
request_headers = { 'user-agent': 'Lego ISS tracker', 'accept': 'application/json' }

# determine current time in UTC
current_time = datetime.datetime.now(datetime.timezone.utc)

# open a log file unless disabled
if args.log:
    logfile = open(args.logfile, 'a')

# format the current time in ISO8601 format for log entries
logtime = datetime.datetime.utcnow().isoformat()

for city in cities:
    # create distinct variables for the city data points
    city_name = city['name']
    latitude = city['latitude']
    longitude = city['longitude']

    # url for the sunrise/sunset API, including the latitude and longitude
    city_sun_url_today = 'https://api.sunrise-sunset.org/json?lat=%f&lng=%f&formatted=0' % (latitude, longitude)

    # get the sun data from the API
    city_sun_data_today = requests.get(city_sun_url_today, headers=request_headers)
    city_object_today = city_sun_data_today.json()['results']

    # isolate the sunrise and sunset times for today
    sunrise = datetime.datetime.fromisoformat(city_object_today['sunrise'])
    sunset = datetime.datetime.fromisoformat(city_object_today['sunset'])

    # calculate how long until the sunrise and sunset
    time_to_sunrise = sunrise - current_time
    time_to_sunset = sunset - current_time

    # if sunrise and/or sunset already happened on the day the script runs, we need to get tomorrow's value(s)
    if time_to_sunrise.total_seconds() < 0 or time_to_sunset.total_seconds() < 0:

        # url for the sunrise/sunset API, including the latitude and longitude
        city_sun_url_tomorrow = 'https://api.sunrise-sunset.org/json?lat=%f&lng=%f&formatted=0&date=tomorrow' % (latitude, longitude)

        # get the sun data from the API
        city_sun_data_tomorrow = requests.get(city_sun_url_tomorrow, headers=request_headers)
        city_object_tomorrow = city_sun_data_tomorrow.json()['results']

        # isolate the sunrise and sunset times for tomorrow
        sunrise_tomorrow = datetime.datetime.fromisoformat(city_object_tomorrow['sunrise'])
        sunset_tomorrow = datetime.datetime.fromisoformat(city_object_tomorrow['sunset'])

        # sunrise already happened today, so use tomorrow's
        if time_to_sunrise.total_seconds() < 0:
            sunrise = sunrise_tomorrow
            time_to_sunrise = sunrise_tomorrow - current_time
        
        # sunset already happened today, so use tomorrow's
        if time_to_sunset.total_seconds() < 0:
            sunset = sunset_tomorrow
            time_to_sunset = sunset_tomorrow - current_time

    if args.verbose:
        print('%s Turning %s on at %s (%d min) and off at %s (%d min)' % (logtime, city_name, sunset.isoformat(), int(time_to_sunset.total_seconds()/60), sunrise.isoformat(), int(time_to_sunrise.total_seconds()/60)))

    if args.log:
        logfile.write('%s %s Turning on at %s and off at %s\n' % (logtime, city_name, sunset.isoformat(), sunrise.isoformat()))

    # if not in test mode, create the at jobs
    if not args.test:
        # create temp file for sunrise, write the poweroff command to it, seek to byte offset 0
        fh1 = tempfile.TemporaryFile()
        fh1.write(bytes('hoobs_power.py -a "Lego %s" -p off' % (city_name), 'utf-8'))
        fh1.seek(0)
        # create temp file for sunset, write the poweron command to it, seek to byte offset 0
        fh2 = tempfile.TemporaryFile()
        fh2.write(bytes('hoobs_power.py -a "Lego %s" -p on' % (city_name), 'utf-8'))
        fh2.seek(0)

        # run the "at" job creations for each of the poweron and poweroff commands
        subprocess.run(['at', '-M', 'now', '+', str(int(time_to_sunrise.total_seconds()/60)), 'minutes'], stdin=fh1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['at', '-M', 'now', '+', str(int(time_to_sunset.total_seconds()/60)), 'minutes'], stdin=fh2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # close the temp files
        fh1.close()
        fh2.close()

# if in log mode, close the log file
if args.log:
    logfile.close()
