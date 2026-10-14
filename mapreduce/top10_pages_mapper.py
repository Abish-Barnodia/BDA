#!/usr/bin/env python3
"""
top10_pages_mapper.py - MapReduce Mapper for Top-10 Visited Pages / Products
ponytail: extracts product from ecommerce_dataset events.csv and emits page\t1
"""
import sys

for line in sys.stdin:
    line = line.strip()
    if not line or line.startswith("event_id") or line.startswith("event_time"):
        continue

    parts = line.split(",")
    # 1. events.csv: event_id,user_id,product_id,event_type,event_timestamp
    if len(parts) >= 5 and parts[0].startswith("E"):
        prod_id = parts[2].strip('"').strip()
        page = "/product/%s" % prod_id
        print("%s\t1" % page)
    # 2. General clickstream: event_time,event_type,product_id,...
    elif len(parts) >= 3:
        prod_id = parts[2].strip('"').strip()
        cat_code = parts[4].strip('"').strip() if len(parts) >= 5 else ""
        page = "/%s/%s" % (cat_code, prod_id) if cat_code else "/product/%s" % prod_id
        print("%s\t1" % page)
