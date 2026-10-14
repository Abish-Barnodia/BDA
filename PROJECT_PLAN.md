# Implementation Plan: Batch MapReduce Clickstream Log Analysis

**Project Reference:** Topic 53 — Batch MapReduce Clickstream Log Analysis  
**Goal:** Build and deploy an end-to-end Big Data pipeline conforming strictly to the problem statement requirements:
* **HDFS storage** of raw clickstream logs
* **Hadoop MapReduce pipeline** (Mappers and Reducers)
* **YARN job scheduling & resource management**
* **Nightly batch schedule**
* **Three mandatory reports:** Peak Traffic Hour, Top-10 Pages, and Error Rates
* **Interactive Batch Report Dashboard**

---

## Architecture Overview

```
[Kaggle Clickstream Dataset]
          │
          ▼ (Phase 2)
   [HDFS Raw Storage] (hdfs:///data/raw/clickstream/)
          │
          ▼ (Phase 3 & 4: Scheduled via YARN / Airflow)
┌────────────────────────────────────────────────────────┐
│               HADOOP YARN CLUSTER                      │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Job 1: Peak Traffic Hour (MapReduce)             │  │
│  │   Mapper: timestamp -> hour, 1                   │  │
│  │   Reducer: aggregate -> rank max peak hour       │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Job 2: Top-10 Page / Product (MapReduce)         │  │
│  │   Mapper: page/product_id -> 1                   │  │
│  │   Reducer: sum counts -> extract global top 10   │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Job 3: Error Rate Analysis (MapReduce)           │  │
│  │   Mapper: hour -> status (error vs success)      │  │
│  │   Reducer: calculate error_rate_pct per hour     │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
          │
          ▼ (Phase 5)
   [HDFS Aggregated Results] (hdfs:///data/output/...)
          │
          ▼ (Export to ./output/)
┌────────────────────────────────────────────────────────┐
│  Phase 6: Batch Report Dashboard (Streamlit / Web UI)  │
│   - KPI Cards: Peak Hour, Total Traffic, Avg Error Rate│
│   - Hourly Traffic Chart & Peak Highlight              │
│   - Top-10 Pages Bar Chart                             │
│   - Error Rate (%) Trend Over Time                     │
└────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Execution Plan

### Step 1: Environment & Infrastructure Setup (HDFS + YARN)
**Objective:** Upgrade `docker-compose.yml` to include full Apache Hadoop HDFS and YARN components so jobs execute on YARN rather than standalone Spark.

* [x] **1.1. Add YARN Containers to `docker-compose.yml`:**
  * Add `resourcemanager` (`bde2020/hadoop-resourcemanager:2.0.0-hadoop3.2.1-java8` on port `8088:8088`).
  * Add `nodemanager` (`bde2020/hadoop-nodemanager:2.0.0-hadoop3.2.1-java8` on port `8042:8042`).
  * Ensure `hdfs-namenode` (port `19870:9870`) and `hdfs-datanode` are correctly linked via Hadoop network.
* [x] **1.2. Configure YARN & MapReduce XMLs:**
  * Mount custom `yarn-site.xml` and `mapred-site.xml` to set `mapreduce.framework.name = yarn` and configure YARN resource allocations (memory/vcores).
* [x] **1.3. Verify Cluster Health:**
  * Start cluster: `docker compose up -d hdfs-namenode hdfs-datanode resourcemanager nodemanager`.
  * Verify HDFS Web UI (`http://localhost:19870` or `9870`) and YARN ResourceManager UI (`http://localhost:8088`).

---

### Step 2: Dataset Preparation & HDFS Ingestion
**Objective:** Prepare the Kaggle E-commerce clickstream dataset and load it into HDFS.

* [x] **2.1. Acquire & Inspect Dataset:**
  * Source: Kaggle eCommerce multi-category store clickstream dataset schema.
  * Provide a lightweight sample generator (`scripts/generate_sample_data.py`) for quick testing without downloading gigabytes of data.
* [x] **2.2. Implement Ingestion Script (`scripts/run_mapreduce_yarn.sh`):**
  * Create HDFS directory: `hdfs dfs -mkdir -p /data/raw/clickstream/`.
  * Upload raw CSV/logs into HDFS: `hdfs dfs -put <data_file> /data/raw/clickstream/`.
  * Validate file size and block distribution across DataNodes.

---

### Step 3: Implement MapReduce Pipeline (Python Hadoop Streaming)
**Objective:** Develop the core MapReduce programs for the 3 required analytical outputs.

#### Job 1: Peak Traffic Hour Analysis
* [x] **File:** `mapreduce/peak_hour_mapper.py`
  * Extract timestamp string, parse date and hour: `YYYY-MM-DD HH`, emit `date_hour \t 1`.
* [x] **File:** `mapreduce/peak_hour_reducer.py`
  * Sum total traffic count per `YYYY-MM-DD HH`, rank max peak hour, emit `PEAK_TRAFFIC_HOUR \t peak_hour \t peak_count`.

#### Job 2: Top-10 Most Visited Pages / Products
* [x] **File:** `mapreduce/top10_pages_mapper.py`
  * Parse line, extract target page / URL / `product_id`, emit `page_identifier \t 1`.
* [x] **File:** `mapreduce/top10_pages_reducer.py`
  * Aggregate total visit counts per page using bounded min-heap to emit the global **Top 10** most visited pages.

#### Job 3: Error Rate Analysis
* [x] **File:** `mapreduce/error_rate_mapper.py`
  * Parse hour (`YYYY-MM-DD HH`) and status code, emit `date_hour \t 1 \t (1 or 0)`.
* [x] **File:** `mapreduce/error_rate_reducer.py`
  * Sum `total_requests` and `error_requests` per hour, compute `error_rate_pct = (error_requests / total_requests) * 100.0`.

---

### Step 4: YARN Job Execution & Nightly Batch Scheduling
**Objective:** Configure YARN execution and automate the pipeline on a nightly schedule.

* [x] **4.1. Create YARN Submission Wrapper (`scripts/run_mapreduce_yarn.sh`):**
  * Submit each job to YARN via Hadoop Streaming.
  * Successfully verified on YARN cluster (`application_1792010673150_0002`, `0003`, `0004`).
* [x] **4.2. Nightly Batch Scheduling:**
  * Created `scripts/run_mapreduce_yarn.sh` ready for Linux cron (`0 0 * * *`) or Airflow DAG integration.

---

### Step 5: Output Export & Data Formatting
**Objective:** Fetch the MapReduce output from HDFS and format it for the presentation layer.

* [x] **5.1. Implement Export Script (`scripts/run_mapreduce_yarn.sh`):**
  * Read from HDFS output paths (`/data/output/peak_traffic`, `/data/output/top_10_pages`, `/data/output/error_rates`).
  * Merge part-files (`hdfs dfs -getmerge`) into structured TSVs in `./output/`.

---

### Step 6: Interactive Batch Report Dashboard
**Objective:** Deliver an executive dashboard fulfilling the "batch report dashboard" requirement.

* [x] **6.1. Build Web Dashboard (`dashboard/server.py` & `dashboard/app.py`):**
  * Pure standard-library server + Chart.js dashboard (`http://localhost:8501`) + Streamlit option.
  * Shows Peak Traffic Hour, Top-10 Pages bar chart, and Hourly Error Rate (%) trend line.

---

### Step 7: Testing, Validation & Final Project Deliverables
**Objective:** Validate all components end-to-end and prepare documentation.

* [x] **7.1. End-to-End Validation Run:**
  * Sample dataset ingested into HDFS.
  * All 3 MapReduce jobs executed on YARN NodeManager.
  * Output TSVs generated and rendered in real-time web dashboard.
* [x] **7.2. Project Documentation:**
  * Update `README.md` with:
    * Problem statement & objective mapping.
    * Architecture diagram showing HDFS, YARN, MapReduce, and Dashboard.
    * Exact execution instructions from zero to working dashboard.
    * Screenshots of YARN UI (`:8088`), HDFS UI (`:19870`), and the Batch Report Dashboard.
