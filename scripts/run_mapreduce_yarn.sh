#!/bin/bash
# run_mapreduce_yarn.sh — End-to-end execution of MapReduce jobs on YARN
# ponytail: clean bash script to ingest Kaggle ecommerce_dataset, submit to YARN, and export results.

set -e

STREAMING_JAR="/opt/hadoop-3.2.1/share/hadoop/tools/lib/hadoop-streaming-3.2.1.jar"

echo "[*] Found Hadoop Streaming Jar: $STREAMING_JAR"

# 1. Prepare HDFS directories
echo "[*] Creating HDFS directories..."
hdfs dfs -mkdir -p /data/raw/ecommerce
hdfs dfs -mkdir -p /data/output

# 2. Upload Kaggle ecommerce_dataset to HDFS
echo "[*] Uploading Kaggle ecommerce_dataset to HDFS..."
hdfs dfs -put -f /opt/data/events.csv /data/raw/ecommerce/events.csv
hdfs dfs -put -f /opt/data/orders.csv /data/raw/ecommerce/orders.csv
hdfs dfs -put -f /opt/data/products.csv /data/raw/ecommerce/products.csv

echo "[+] Successfully stored raw dataset on HDFS:"
hdfs dfs -ls /data/raw/ecommerce/

# 3. Job 1: Peak Traffic Hour (from events.csv clickstream)
echo "=========================================================="
echo "[+] Submitting Job 1 (Peak Traffic Hour) to YARN..."
echo "=========================================================="
hdfs dfs -rm -r -f /data/output/peak_traffic || true
yarn jar "$STREAMING_JAR" \
  -files /opt/mapreduce/peak_hour_mapper.py,/opt/mapreduce/peak_hour_reducer.py \
  -mapper "python3 peak_hour_mapper.py" \
  -reducer "python3 peak_hour_reducer.py" \
  -input /data/raw/ecommerce/events.csv \
  -output /data/output/peak_traffic

# 4. Job 2: Top-10 Most Visited Pages / Products (from events.csv clickstream)
echo "=========================================================="
echo "[+] Submitting Job 2 (Top 10 Pages) to YARN..."
echo "=========================================================="
hdfs dfs -rm -r -f /data/output/top_10_pages || true
yarn jar "$STREAMING_JAR" \
  -files /opt/mapreduce/top10_pages_mapper.py,/opt/mapreduce/top10_pages_reducer.py \
  -mapper "python3 top10_pages_mapper.py" \
  -reducer "python3 top10_pages_reducer.py" \
  -input /data/raw/ecommerce/events.csv \
  -output /data/output/top_10_pages

# 5. Job 3: Hourly Error Rate Analysis (from orders.csv transactional drop-offs)
echo "=========================================================="
echo "[+] Submitting Job 3 (Error Rate Analysis) to YARN..."
echo "=========================================================="
hdfs dfs -rm -r -f /data/output/error_rates || true
yarn jar "$STREAMING_JAR" \
  -files /opt/mapreduce/error_rate_mapper.py,/opt/mapreduce/error_rate_reducer.py \
  -mapper "python3 error_rate_mapper.py" \
  -reducer "python3 error_rate_reducer.py" \
  -input /data/raw/ecommerce/orders.csv \
  -output /data/output/error_rates

# 6. Export outputs to host-mounted /opt/output
echo "=========================================================="
echo "[*] Exporting batch reports to /opt/output..."
echo "=========================================================="
mkdir -p /opt/output
hdfs dfs -getmerge /data/output/peak_traffic /opt/output/peak_traffic.tsv
hdfs dfs -getmerge /data/output/top_10_pages /opt/output/top_10_pages.tsv
hdfs dfs -getmerge /data/output/error_rates /opt/output/error_rates.tsv

echo "[+] All MapReduce jobs completed successfully on YARN for Kaggle ecommerce_dataset!"
