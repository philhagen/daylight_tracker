#!/usr/bin/env python3
# (C)2022 Phil Hagen <phil@lewestech.com>
#
# This script will power on or off a named light via the HOOBS API

import json
import requests
import argparse
import pdb

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--accessory', help="Accessory name to set")
parser.add_argument('-p', '--powermode', help="Power state to set", choices=['on', 'off'])
args = parser.parse_args()

# load hoobs configuration from file
cf = open('/etc/sysconfig/city_config.json', 'r')
hoobs = json.load(cf)['hoobs']
cf.close()

request_headers = { 'user-agent': 'Daylight Tracker', 'content-type': 'application/json', 'accept': 'application/json' }

# POST /api/auth/logon
# body: { "username": hoobs_username, "password": hoobs_password, "remember": false }
# returns: token
login_params = { 'username': hoobs['username'], 'password': hoobs['password'], 'remember': False }
response = requests.post('http://%s/api/auth/logon' % (hoobs['hostname']), json=login_params, headers=request_headers)
token = response.json()['token']

# set token in authorization: header from here on out
request_headers['authorization'] = token

# GET /api/accessories
# returns: list of accessories
response = requests.get('http://%s/api/accessories' % (hoobs['hostname']), json=login_params, headers=request_headers)
accessories = response.json()[0]['accessories']
# build a new dictionary with the name as the key and the full object as the value
accessories_dict = dict((item['name'], item) for item in accessories)

if args.accessory in accessories_dict:
    # get the bridge name and accessory id for the supplied accessory name
    bridge = accessories_dict[args.accessory]['bridge']
    accessory_id = accessories_dict[args.accessory]['accessory_identifier']

    # PUT /api/accessory/{{ bridge ID }}/{{ accessory_identifier }}/on
    # body: { "value": true } (or false for off... duh)
    if args.powermode == 'on':
        action_params = { 'value': True }
    else:
        action_params = { 'value': False }

    response = requests.put('http://%s/api/accessory/%s/%s/on' % (hoobs['hostname'], bridge, accessory_id), json=action_params, headers=request_headers)

else:
    # reqeusted accessory not present in HOOBS list
    pass
