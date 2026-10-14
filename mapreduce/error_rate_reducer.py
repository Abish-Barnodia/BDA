#!/usr/bin/env python3
"""
error_rate_reducer.py - MapReduce Reducer for Hourly Error Rate Analysis
ponytail: compatible with Python 3.5+, computes total, errors, and error_rate_pct.
"""
import sys

current_hour = None
current_total = 0
current_errors = 0

def emit(hour, total, errors):
    rate = (errors * 100.0 / total) if total > 0 else 0.0
    print("%s\t%d\t%d\t%.2f%%" % (hour, total, errors, rate))

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        hour, total, error = line.split("\t")
        total = int(total)
        error = int(error)
    except ValueError:
        continue

    if current_hour == hour:
        current_total += total
        current_errors += error
    else:
        if current_hour is not None:
            emit(current_hour, current_total, current_errors)
        current_hour = hour
        current_total = total
        current_errors = error

if current_hour is not None:
    emit(current_hour, current_total, current_errors)
