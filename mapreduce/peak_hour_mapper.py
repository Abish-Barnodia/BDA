#!/usr/bin/env python3
"""
peak_hour_mapper.py - MapReduce Mapper for Peak Traffic Hour
ponytail: supports ecommerce_dataset events.csv and clickstream logs
"""
import sys

for line in sys.stdin:
    line = line.strip()
    if not line or line.startswith("event_id") or line.startswith("event_time"):
        continue

    parts = line.split(",")
    # 1. events.csv: event_id,user_id,product_id,event_type,event_timestamp
    if len(parts) >= 5 and "T" in parts[4]:
        ts = parts[4].strip('"').strip()
        if len(ts) >= 13:
            date_hour = ts[:13].replace("T", " ")
            print("%s\t1" % date_hour)
    # 2. General clickstream: event_time, ...
    elif len(parts) >= 1:
        ts = parts[0].strip('"').strip()
        if len(ts) >= 13:
            date_hour = ts[:13].replace("T", " ")
            print("%s\t1" % date_hour)
