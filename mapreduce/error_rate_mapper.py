#!/usr/bin/env python3
"""
error_rate_mapper.py - MapReduce Mapper for Hourly Error Rate Analysis
ponytail: handles orders.csv (status cancelled/returned) and logs with status codes
"""
import sys

for line in sys.stdin:
    line = line.strip()
    if not line or line.startswith("order_id") or line.startswith("event_time"):
        continue

    parts = line.split(",")
    # 1. orders.csv: order_id,user_id,order_date,order_status,total_amount
    if len(parts) >= 5 and parts[0].startswith("O"):
        ts = parts[2].strip('"').strip()
        if len(ts) < 13:
            continue
        date_hour = ts[:13].replace("T", " ")
        status = parts[3].strip('"').strip().lower()
        is_error = 1 if status in ("cancelled", "returned", "failed", "error") else 0
        print("%s\t1\t%d" % (date_hour, is_error))

    # 2. General clickstream / server logs: event_time,...status_code
    elif len(parts) >= 1:
        ts = parts[0].strip('"').strip()
        if len(ts) < 13:
            continue
        date_hour = ts[:13].replace("T", " ")

        status_code = 200
        if len(parts) >= 10:
            try:
                status_code = int(parts[9].strip('"').strip())
            except ValueError:
                status_code = 200

        is_error = 1 if status_code >= 400 else 0
        print("%s\t1\t%d" % (date_hour, is_error))
