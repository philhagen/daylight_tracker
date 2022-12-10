#!/usr/bin/env python3
# (C)2021 Phil Hagen <phil@lewestech.com>
#
# This script will read determine the next seven minutes of the ISS's location, to include whether the ISS is in daylight or shadow.
# It will then create an "at" job for the minute when the ISS enters or exits the shadow.
#
# All clocks are assumed UTC because if they are not, they are wrong.

import time
import requests
import tempfile
import subprocess
import datetime
import argparse

default_log = '/var/log/iss_tracker.log'
run_every = 6

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Verbose mode', action='store_true', default=False)
parser.add_argument('-t', '--test', help='Run in test mode - do not create jobs', action='store_true', default=False)
parser.add_argument('-L', '--nolog', dest='log', help='Disable logging', action='store_false', default=True)
parser.add_argument('-f', '--logfile', help='Specify the logfile location if logging is enabled', default=default_log)
args = parser.parse_args()

if args.test:
    args.log = False

# build a list of timestamps: current time and (run_every+1) minutes after that
ts = []
ts.append(int(time.time()))

for i in range(1,run_every+1):
    ts.append(int(ts[0] + i*60))

# convert the timestamps to strings
ts = [str(int) for int in ts]

# get current and next 9 locations for the ISS
iss_positions_url = 'https://api.wheretheiss.at/v1/satellites/25544/positions?units=miles&timestamps=%s&units=miles' % (','.join(ts))

request_headers = { 'user-agent': 'Lego ISS tracker', 'accept': 'application/json' }
iss_loc = requests.get(iss_positions_url, headers=request_headers)

location_object = iss_loc.json()

if args.log:
    logfile = open(args.logfile, 'a')
    logtime = datetime.datetime.utcnow().isoformat()

light_state_changed = False

for i in range(0,run_every):
    timestamp1 = int(ts[i])
    timestamp2 = int(ts[i+1])

    iss_sun_state1 = location_object[i]['visibility']
    iss_sun_state2 = location_object[i+1]['visibility']

    if args.verbose:
        print('%d - %d: %s' % (timestamp1, timestamp2, iss_sun_state2))

    if iss_sun_state1 != iss_sun_state2:
        light_state_changed = True

        if iss_sun_state2 == 'eclipsed':
            if args.verbose:
                print('ISS eclipses in %d minutes' % (i))

            if args.log:
                logfile.write('%s: ISS eclipses in %d minutes\n' % (logtime, i))

            if not args.test:
                fh = tempfile.TemporaryFile()
                fh.write(bytes('/usr/local/bin/hoobs_power.py -a "Lego ISS" -p on', 'utf-8'))
                fh.seek(0)

                subprocess.run(['at', '-M', 'now', '+', str(i+1), 'minutes'], stdin=fh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                fh.close()

        elif iss_sun_state2 == 'daylight':
            if args.verbose:
                print('ISS in daylight in %d minutes' % (i))
            
            if args.log:
                logfile.write('%s ISS in daylight in %d minutes\n' % (logtime, i))

            if not args.test:
                fh = tempfile.TemporaryFile()
                fh.write(bytes('/usr/local/bin/hoobs_power.py -a "Lego ISS" -p off', 'utf-8'))
                fh.seek(0)

                subprocess.run(['at', '-M', 'now', '+', str(i+1), 'minutes'], stdin=fh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                fh.close()

if not light_state_changed:
    if args.verbose:
        print('Daylight state NOT changed in next %d minutes - no jobs created' % (run_every))
    
    if args.log:
        logfile.write('%s Daylight state NOT changed in next %d minutes - no jobs created\n' % (logtime, run_every))

if args.log:
    logfile.close()
