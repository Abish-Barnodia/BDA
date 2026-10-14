#!/usr/bin/env python3
"""
top10_pages_reducer.py - MapReduce Reducer for Top-10 Visited Pages
ponytail: compatible with Python 3.5+, aggregates streaming counts and outputs top 10 using heapq.
"""
import sys
import heapq

current_page = None
current_count = 0
top_heap = []  # min-heap of (count, page)

def push_top(count, page):
    if len(top_heap) < 10:
        heapq.heappush(top_heap, (count, page))
    else:
        if count > top_heap[0][0]:
            heapq.heapreplace(top_heap, (count, page))

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        page, count = line.split("\t", 1)
        count = int(count)
    except ValueError:
        continue

    if current_page == page:
        current_count += count
    else:
        if current_page is not None:
            push_top(current_count, current_page)
        current_page = page
        current_count = count

if current_page is not None:
    push_top(current_count, current_page)

sorted_top = sorted(top_heap, key=lambda x: x[0], reverse=True)
for rank, (count, page) in enumerate(sorted_top, start=1):
    print("%d\t%s\t%d" % (rank, page, count))
