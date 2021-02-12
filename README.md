# daylight_tracker

This is a pair of scripts that scratch a very specific itch.

## City Tracker

This script will read a list of records in JSON format that describe one location each.

It will then determine the sunset and sunrise times for each location and create an "at" job at each of those events.

## ISS Tracker

This script will read determine the next seven minutes of the ISS's location, to include whether the ISS is in daylight or shadow.

It will then create an "at" job for the minute when the ISS enters or exits the shadow.
