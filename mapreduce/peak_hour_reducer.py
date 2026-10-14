#!/usr/bin/env python3
"""
peak_hour_reducer.py - MapReduce Reducer for Peak Traffic Hour
ponytail: compatible with Python 3.5+, streaming reducer with peak tracker.
"""
import sys

current_hour = None
current_count = 0
peak_hour = None
peak_count = -1

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        hour, count = line.split("\t", 1)
        count = int(count)
    except ValueError:
        continue

    if current_hour == hour:
        current_count += count
    else:
        if current_hour is not None:
            print("%s\t%d" % (current_hour, current_count))
            if current_count > peak_count:
                peak_count = current_count
                peak_hour = current_hour
        current_hour = hour
        current_count = count

# Emit the final hour
if current_hour is not None:
    print("%s\t%d" % (current_hour, current_count))
    if current_count > peak_count:
        peak_count = current_count
        peak_hour = current_hour

# Emit peak traffic hour summary
if peak_hour is not None:
    print("PEAK_TRAFFIC_HOUR\t%s\t%d" % (peak_hour, peak_count))
