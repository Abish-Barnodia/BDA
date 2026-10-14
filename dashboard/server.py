#!/usr/bin/env python3
"""
server.py — Apple-inspired Batch Report Dashboard Server with Light & Dark Modes
# ponytail: pure Python standard library http.server + Chart.js & Iconify via CDN.
Fast in-memory caching and clean aggregation for instantaneous rendering.
"""

import os
import json
import http.server
import socketserver

PORT = 8501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "output")

# In-memory cached payload
_CACHED_DATA = None

def load_and_aggregate_data():
    global _CACHED_DATA
    peak_file = os.path.join(OUTPUT_DIR, "peak_traffic.tsv")
    top10_file = os.path.join(OUTPUT_DIR, "top_10_pages.tsv")
    error_file = os.path.join(OUTPUT_DIR, "error_rates.tsv")

    # 1. Peak Traffic & 24-Hour Distribution
    hour_counts = {h: 0 for h in range(24)}
    daily_counts = {}
    global_peak_hour = "N/A"
    global_peak_count = 0
    total_requests = 0

    if os.path.exists(peak_file):
        with open(peak_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts[0] == "PEAK_TRAFFIC_HOUR":
                    global_peak_hour = parts[1]
                    global_peak_count = int(parts[2])
                elif len(parts) >= 2:
                    cnt = int(parts[1])
                    total_requests += cnt
                    time_parts = parts[0].split(" ")
                    if len(time_parts) == 2:
                        dt, hr_str = time_parts
                        try:
                            hr = int(hr_str)
                            hour_counts[hr] += cnt
                            daily_counts[dt] = daily_counts.get(dt, 0) + cnt
                        except ValueError:
                            pass

    # Find peak hour of day (0-23)
    peak_hr_of_day = max(hour_counts, key=hour_counts.get) if hour_counts else 0
    peak_hr_of_day_count = hour_counts.get(peak_hr_of_day, 0)

    # 2. Top 10 Pages
    top10 = []
    if os.path.exists(top10_file):
        with open(top10_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    try:
                        top10.append({
                            "rank": int(parts[0]),
                            "page": parts[1],
                            "visits": int(parts[2])
                        })
                    except ValueError:
                        pass
    top10.sort(key=lambda x: x["rank"])
    top10 = top10[:10]

    # 3. Error Rates (24-Hour & Overall)
    hour_errors = {h: [0, 0] for h in range(24)}  # [total_orders, error_orders]
    daily_errors = {}

    if os.path.exists(error_file):
        with open(error_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 4:
                    time_parts = parts[0].split(" ")
                    if len(time_parts) == 2:
                        dt, hr_str = time_parts
                        try:
                            hr = int(hr_str)
                            tot = int(parts[1])
                            err = int(parts[2])
                            hour_errors[hr][0] += tot
                            hour_errors[hr][1] += err
                            if dt not in daily_errors:
                                daily_errors[dt] = [0, 0]
                            daily_errors[dt][0] += tot
                            daily_errors[dt][1] += err
                        except ValueError:
                            pass

    total_orders = sum(v[0] for v in hour_errors.values())
    total_failed_orders = sum(v[1] for v in hour_errors.values())
    avg_error_rate = (total_failed_orders / total_orders * 100.0) if total_orders > 0 else 0.0

    # Hourly 24-hr lists
    hourly_24 = [
        {
            "hour": "{:02d}:00".format(h),
            "count": hour_counts[h],
            "is_peak": (h == peak_hr_of_day)
        }
        for h in range(24)
    ]

    error_24 = [
        {
            "hour": "{:02d}:00".format(h),
            "rate": round(hour_errors[h][1] / hour_errors[h][0] * 100.0, 2) if hour_errors[h][0] > 0 else 0.0,
            "total": hour_errors[h][0],
            "errors": hour_errors[h][1]
        }
        for h in range(24)
    ]

    # Downsample daily trend for timeline chart
    sorted_dates = sorted(daily_counts.keys())
    step = max(1, len(sorted_dates) // 35)
    sampled_dates = sorted_dates[::step]
    daily_trend = [
        {
            "date": d,
            "traffic": daily_counts.get(d, 0),
            "error_rate": round(daily_errors[d][1] / daily_errors[d][0] * 100.0, 2) if d in daily_errors and daily_errors[d][0] > 0 else 0.0
        }
        for d in sampled_dates
    ]

    _CACHED_DATA = {
        "kpi": {
            "total_requests": total_requests,
            "global_peak_hour": global_peak_hour,
            "global_peak_count": global_peak_count,
            "diurnal_peak_hour": "{:02d}:00".format(peak_hr_of_day),
            "diurnal_peak_count": peak_hr_of_day_count,
            "top_page": top10[0]["page"] if top10 else "N/A",
            "top_page_visits": top10[0]["visits"] if top10 else 0,
            "avg_error_rate": round(avg_error_rate, 2),
            "total_orders": total_orders,
            "total_failed_orders": total_failed_orders
        },
        "hourly_24": hourly_24,
        "error_24": error_24,
        "top10": top10,
        "daily_trend": daily_trend
    }
    return _CACHED_DATA

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <title>Batch MapReduce Clickstream Analytics | Apple Design</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Iconify for Apple SF / Lucide icons -->
  <script src="https://code.iconify.design/iconify-icon/1.0.8/iconify-icon.min.js"></script>
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root, [data-theme="dark"] {
      --bg: #000000;
      --bg-gradient: 
        radial-gradient(circle at 50% 0%, rgba(41, 151, 255, 0.09) 0%, transparent 45%),
        radial-gradient(circle at 90% 20%, rgba(191, 90, 242, 0.05) 0%, transparent 40%);
      --nav-bg: rgba(10, 12, 16, 0.78);
      --card-bg: rgba(26, 29, 36, 0.72);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(35, 40, 50, 0.85);
      --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      --text: #f5f5f7;
      --text-secondary: #86868b;
      --text-tertiary: #6e6e73;
      --code-bg: rgba(255, 255, 255, 0.05);
      --code-border: rgba(255, 255, 255, 0.07);
      --code-color: #e2e8f0;
      --table-border: rgba(255, 255, 255, 0.04);
      --table-hover: rgba(255, 255, 255, 0.03);
      --btn-bg: rgba(255, 255, 255, 0.08);
      --btn-border: rgba(255, 255, 255, 0.1);
      --btn-hover: rgba(255, 255, 255, 0.15);
      --seg-bg: rgba(255, 255, 255, 0.06);
      --seg-active: rgba(255, 255, 255, 0.16);
      --seg-border: rgba(255, 255, 255, 0.08);
      --apple-blue: #2997ff;
      --apple-blue-soft: rgba(41, 151, 255, 0.12);
      --apple-purple: #bf5af2;
      --apple-purple-soft: rgba(191, 90, 242, 0.12);
      --apple-orange: #ff9f0a;
      --apple-orange-soft: rgba(255, 159, 10, 0.12);
      --apple-red: #ff453a;
      --apple-red-soft: rgba(255, 69, 58, 0.12);
      --apple-green: #30d158;
      --apple-green-soft: rgba(48, 209, 88, 0.12);
      --squircle: 22px;
    }

    [data-theme="light"] {
      --bg: #f5f5f7;
      --bg-gradient: 
        radial-gradient(circle at 50% 0%, rgba(0, 113, 227, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 90% 20%, rgba(191, 90, 242, 0.04) 0%, transparent 40%);
      --nav-bg: rgba(255, 255, 255, 0.82);
      --card-bg: rgba(255, 255, 255, 0.85);
      --card-border: rgba(0, 0, 0, 0.07);
      --card-hover: rgba(255, 255, 255, 0.98);
      --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
      --text: #1d1d1f;
      --text-secondary: #6e6e73;
      --text-tertiary: #86868b;
      --code-bg: rgba(0, 0, 0, 0.04);
      --code-border: rgba(0, 0, 0, 0.08);
      --code-color: #1d1d1f;
      --table-border: rgba(0, 0, 0, 0.06);
      --table-hover: rgba(0, 0, 0, 0.02);
      --btn-bg: rgba(0, 0, 0, 0.05);
      --btn-border: rgba(0, 0, 0, 0.08);
      --btn-hover: rgba(0, 0, 0, 0.09);
      --seg-bg: rgba(0, 0, 0, 0.05);
      --seg-active: rgba(255, 255, 255, 0.95);
      --seg-border: rgba(0, 0, 0, 0.08);
      --apple-blue: #0071e3;
      --apple-blue-soft: rgba(0, 113, 227, 0.1);
      --apple-purple: #9a38cc;
      --apple-purple-soft: rgba(154, 56, 204, 0.1);
      --apple-orange: #d97706;
      --apple-orange-soft: rgba(217, 119, 6, 0.1);
      --apple-red: #d70015;
      --apple-red-soft: rgba(215, 0, 21, 0.1);
      --apple-green: #28cd41;
      --apple-green-soft: rgba(40, 205, 65, 0.1);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
      -webkit-font-smoothing: antialiased;
      transition: background-color 0.25s ease, border-color 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;
    }

    body {
      background-color: var(--bg);
      background-image: var(--bg-gradient);
      color: var(--text);
      min-height: 100vh;
      padding: 0 0 60px 0;
    }

    /* Apple Frosted Navbar */
    .nav {
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(25px) saturate(190%);
      -webkit-backdrop-filter: blur(25px) saturate(190%);
      background: var(--nav-bg);
      border-bottom: 1px solid var(--card-border);
      padding: 14px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .nav-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: linear-gradient(135deg, #0071e3, #2997ff);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      box-shadow: 0 4px 14px rgba(41, 151, 255, 0.35);
    }

    .brand-titles h1 {
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: var(--text);
    }

    .brand-titles p {
      font-size: 0.76rem;
      color: var(--text-secondary);
      font-weight: 400;
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: var(--apple-green-soft);
      border: 1px solid rgba(48, 209, 88, 0.25);
      color: var(--apple-green);
      font-size: 0.78rem;
      font-weight: 500;
      padding: 6px 14px;
      border-radius: 9999px;
    }

    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--apple-green);
      box-shadow: 0 0 10px var(--apple-green);
      animation: pulse 2s infinite ease-in-out;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    .btn-nav {
      background: var(--btn-bg);
      border: 1px solid var(--btn-border);
      color: var(--text);
      font-size: 0.8rem;
      font-weight: 500;
      padding: 7px 14px;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .btn-nav:hover {
      background: var(--btn-hover);
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateY(-1px);
    }

    .btn-theme {
      background: var(--btn-bg);
      border: 1px solid var(--btn-border);
      color: var(--text);
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .btn-theme:hover {
      background: var(--btn-hover);
      transform: scale(1.05);
    }

    /* Main Container */
    .main-wrap {
      max-width: 1320px;
      margin: 0 auto;
      padding: 32px 24px;
    }

    /* Subheader & Segmented Switcher */
    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 28px;
      flex-wrap: wrap;
      gap: 16px;
    }

    .section-headline h2 {
      font-size: 1.7rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--text);
    }

    .section-headline p {
      color: var(--text-secondary);
      font-size: 0.9rem;
      margin-top: 4px;
    }

    /* Apple Segmented Control */
    .segmented-control {
      background: var(--seg-bg);
      border: 1px solid var(--seg-border);
      padding: 3px;
      border-radius: 12px;
      display: inline-flex;
      gap: 2px;
    }

    .seg-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 0.82rem;
      font-weight: 500;
      padding: 7px 16px;
      border-radius: 9px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .seg-btn.active {
      background: var(--seg-active);
      color: var(--text);
      font-weight: 600;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    /* Apple Frosted Squircle Cards */
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: var(--squircle);
      padding: 24px;
      box-shadow: var(--card-shadow);
      transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    }

    .card:hover {
      border-color: rgba(255, 255, 255, 0.14);
    }

    /* KPI Cards Grid */
    .kpis-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
      margin-bottom: 28px;
    }

    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .kpi-icon-badge {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }

    .badge-blue { background: var(--apple-blue-soft); color: var(--apple-blue); }
    .badge-purple { background: var(--apple-purple-soft); color: var(--apple-purple); }
    .badge-orange { background: var(--apple-orange-soft); color: var(--apple-orange); }
    .badge-red { background: var(--apple-red-soft); color: var(--apple-red); }

    .kpi-chip {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 9999px;
      background: var(--btn-bg);
      color: var(--text-tertiary);
      border: 1px solid var(--card-border);
    }

    .kpi-label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-secondary);
      font-weight: 600;
      margin-bottom: 6px;
    }

    .kpi-number {
      font-size: 2.1rem;
      font-weight: 700;
      letter-spacing: -0.03em;
      color: var(--text);
      line-height: 1.1;
    }

    .kpi-meta {
      font-size: 0.82rem;
      color: var(--text-secondary);
      margin-top: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .kpi-meta-accent {
      color: var(--apple-blue);
      font-weight: 500;
    }

    /* Charts Grid */
    .grid-2 {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 24px;
      margin-bottom: 28px;
    }

    @media (max-width: 1024px) {
      .grid-2 { grid-template-columns: 1fr; }
    }

    .card-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }

    .card-title-row h3 {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 9px;
    }

    .card-subtitle {
      font-size: 0.8rem;
      color: var(--text-secondary);
      font-weight: 400;
    }

    .chart-box {
      position: relative;
      height: 310px;
      width: 100%;
    }

    /* Apple-style Table */
    .table-responsive {
      overflow-x: auto;
      margin-top: 8px;
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 0.88rem;
    }

    th {
      text-align: left;
      padding: 12px 16px;
      color: var(--text-secondary);
      font-weight: 500;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--card-border);
    }

    td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--table-border);
      color: var(--text);
    }

    tbody tr {
      transition: background 0.15s ease;
    }

    tbody tr:hover {
      background: var(--table-hover);
    }

    tbody tr:last-child td {
      border-bottom: none;
    }

    .rank-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .rank-1 { background: linear-gradient(135deg, #ffd700, #ff9f0a); color: #000; box-shadow: 0 2px 8px rgba(255, 159, 10, 0.3); }
    .rank-2 { background: linear-gradient(135deg, #e0e0e0, #a0a0a0); color: #000; }
    .rank-3 { background: linear-gradient(135deg, #cd7f32, #9a5316); color: #fff; }
    .rank-other { background: var(--btn-bg); color: var(--text-secondary); }

    .product-code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      background: var(--code-bg);
      border: 1px solid var(--code-border);
      padding: 3px 8px;
      border-radius: 6px;
      color: var(--code-color);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .bar-bg {
      width: 100%;
      height: 6px;
      background: var(--btn-bg);
      border-radius: 9999px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #0071e3, #2997ff);
      border-radius: 9999px;
    }

    /* Footer Banner */
    .cluster-banner {
      margin-top: 32px;
      padding: 20px 24px;
      background: var(--btn-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--squircle);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }

    .cluster-info {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .cluster-icon {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: var(--btn-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--apple-blue);
      font-size: 20px;
    }

    .cluster-specs h4 {
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text);
    }

    .cluster-specs p {
      font-size: 0.78rem;
      color: var(--text-secondary);
      margin-top: 2px;
    }

    .cluster-links {
      display: flex;
      gap: 10px;
    }
  </style>
</head>
<body>

  <!-- Apple Navigation Bar -->
  <nav class="nav">
    <div class="nav-brand">
      <div class="brand-icon">
        <iconify-icon icon="lucide:layers" style="font-size: 20px;"></iconify-icon>
      </div>
      <div class="brand-titles">
        <h1>Clickstream Analytics</h1>
        <p>Apache Hadoop HDFS + MapReduce on YARN</p>
      </div>
    </div>
    <div class="nav-actions">
      <!-- Light / Dark Mode Toggle Button -->
      <button class="btn-theme" onclick="toggleTheme()" id="theme-toggle" title="Switch Light/Dark Mode">
        <iconify-icon icon="lucide:sun" id="theme-icon"></iconify-icon>
      </button>

      <div class="status-pill">
        <span class="status-dot"></span>
        <span>YARN Active</span>
      </div>
      <button class="btn-nav" onclick="refreshDashboard()" id="btn-refresh">
        <iconify-icon icon="lucide:rotate-cw" id="refresh-icon"></iconify-icon>
        <span>Refresh</span>
      </button>
      <a href="http://localhost:8088" target="_blank" class="btn-nav">
        <iconify-icon icon="lucide:server"></iconify-icon>
        <span>YARN UI</span>
      </a>
      <a href="http://localhost:19870" target="_blank" class="btn-nav">
        <iconify-icon icon="lucide:hard-drive"></iconify-icon>
        <span>HDFS UI</span>
      </a>
    </div>
  </nav>

  <!-- Main Body -->
  <main class="main-wrap">
    
    <!-- Controls & Headings -->
    <div class="controls-bar">
      <div class="section-headline">
        <h2>Executive Batch Report</h2>
        <p>Real-time analytics synthesized from 80,000 clickstream events and 20,000 order transactions</p>
      </div>
      <div class="segmented-control">
        <button class="seg-btn active" id="btn-diurnal" onclick="switchView('diurnal')">
          <iconify-icon icon="lucide:clock-4"></iconify-icon>
          <span>24-Hour Diurnal</span>
        </button>
        <button class="seg-btn" id="btn-timeline" onclick="switchView('timeline')">
          <iconify-icon icon="lucide:calendar"></iconify-icon>
          <span>Multi-Month Timeline</span>
        </button>
      </div>
    </div>

    <!-- 4 Apple Glass KPI Cards -->
    <div class="kpis-grid">
      <!-- KPI 1 -->
      <div class="card">
        <div class="kpi-header">
          <div class="kpi-icon-badge badge-blue">
            <iconify-icon icon="lucide:activity"></iconify-icon>
          </div>
          <span class="kpi-chip">HDFS Ingested</span>
        </div>
        <div class="kpi-label">Total Processed Events</div>
        <div class="kpi-number" id="kpi-total">--</div>
        <div class="kpi-meta">
          <iconify-icon icon="lucide:check-circle-2" style="color: var(--apple-blue);"></iconify-icon>
          <span>Kaggle eCommerce Dataset</span>
        </div>
      </div>

      <!-- KPI 2 -->
      <div class="card">
        <div class="kpi-header">
          <div class="kpi-icon-badge badge-purple">
            <iconify-icon icon="lucide:clock-9"></iconify-icon>
          </div>
          <span class="kpi-chip">Peak Hour</span>
        </div>
        <div class="kpi-label">Peak Operating Window</div>
        <div class="kpi-number" id="kpi-peak">--</div>
        <div class="kpi-meta">
          <span class="kpi-meta-accent" id="kpi-peak-val">--</span>
        </div>
      </div>

      <!-- KPI 3 -->
      <div class="card">
        <div class="kpi-header">
          <div class="kpi-icon-badge badge-orange">
            <iconify-icon icon="lucide:shopping-bag"></iconify-icon>
          </div>
          <span class="kpi-chip">Rank #1 Page</span>
        </div>
        <div class="kpi-label">Top Requested Product</div>
        <div class="kpi-number" id="kpi-top-page" style="font-size: 1.45rem; line-height: 1.6;">--</div>
        <div class="kpi-meta">
          <iconify-icon icon="lucide:eye" style="color: var(--apple-orange);"></iconify-icon>
          <span id="kpi-top-visits">-- visits</span>
        </div>
      </div>

      <!-- KPI 4 -->
      <div class="card">
        <div class="kpi-header">
          <div class="kpi-icon-badge badge-red">
            <iconify-icon icon="lucide:shield-alert"></iconify-icon>
          </div>
          <span class="kpi-chip">Orders Status</span>
        </div>
        <div class="kpi-label">Transaction Failure Rate</div>
        <div class="kpi-number" id="kpi-error">--</div>
        <div class="kpi-meta">
          <iconify-icon icon="lucide:x-circle" style="color: var(--apple-red);"></iconify-icon>
          <span id="kpi-error-sub">Cancelled & returned orders</span>
        </div>
      </div>
    </div>

    <!-- Charts Row 1: Traffic + Top 10 -->
    <div class="grid-2">
      <!-- Traffic Chart -->
      <div class="card">
        <div class="card-title-row">
          <div>
            <h3>
              <iconify-icon icon="lucide:trending-up" style="color: var(--apple-blue);"></iconify-icon>
              <span>Traffic Volume</span>
            </h3>
            <span class="card-subtitle" id="traffic-chart-label">Aggregated clickstream volume across 24-hour cycle</span>
          </div>
        </div>
        <div class="chart-box">
          <canvas id="trafficChart"></canvas>
        </div>
      </div>

      <!-- Top 10 Bar Chart -->
      <div class="card">
        <div class="card-title-row">
          <div>
            <h3>
              <iconify-icon icon="lucide:bar-chart-2" style="color: var(--apple-orange);"></iconify-icon>
              <span>Top 10 Most Visited Products</span>
            </h3>
            <span class="card-subtitle">Identified via MapReduce min-heap reducer</span>
          </div>
        </div>
        <div class="chart-box">
          <canvas id="topPagesChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Charts Row 2: Hourly Error Rate -->
    <div class="card" style="margin-bottom: 28px;">
      <div class="card-title-row">
        <div>
          <h3>
            <iconify-icon icon="lucide:alert-triangle" style="color: var(--apple-red);"></iconify-icon>
            <span>Hourly Error & Cancellation Rate (%)</span>
          </h3>
          <span class="card-subtitle" id="error-chart-label">Percentage of failed transactions calculated per hourly bucket</span>
        </div>
      </div>
      <div class="chart-box" style="height: 250px;">
        <canvas id="errorChart"></canvas>
      </div>
    </div>

    <!-- Top 10 Data Table -->
    <div class="card">
      <div class="card-title-row">
        <div>
          <h3>
            <iconify-icon icon="lucide:list-ordered" style="color: var(--apple-purple);"></iconify-icon>
            <span>Top 10 Products Batch Report Table</span>
          </h3>
          <span class="card-subtitle">Official output generated by MapReduce Job 2 into HDFS</span>
        </div>
      </div>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th style="width: 80px;">Rank</th>
              <th>Product Identifier / Path</th>
              <th style="width: 140px;">Visits</th>
              <th style="width: 240px;">Share of Top 10</th>
            </tr>
          </thead>
          <tbody id="top10-table-body">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Cluster Specs Banner -->
    <div class="cluster-banner">
      <div class="cluster-info">
        <div class="cluster-icon">
          <iconify-icon icon="lucide:cpu"></iconify-icon>
        </div>
        <div class="cluster-specs">
          <h4>Apache Hadoop & YARN Infrastructure</h4>
          <p>YARN ResourceManager (Port 8088) &bull; HDFS NameNode (Port 19870) &bull; MapReduce Streaming Runtime</p>
        </div>
      </div>
      <div class="cluster-links">
        <a href="http://localhost:8088" target="_blank" class="btn-nav">
          <iconify-icon icon="lucide:external-link"></iconify-icon>
          <span>Resource Manager</span>
        </a>
        <a href="http://localhost:19870" target="_blank" class="btn-nav">
          <iconify-icon icon="lucide:external-link"></iconify-icon>
          <span>HDFS Explorer</span>
        </a>
      </div>
    </div>

  </main>

  <script>
    let globalData = null;
    let trafficChart = null;
    let topPagesChart = null;
    let errorChart = null;
    let currentView = 'diurnal';

    // Theme Management
    function initTheme() {
      const saved = localStorage.getItem('apple-dashboard-theme') || 'dark';
      setTheme(saved);
    }

    function toggleTheme() {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      setTheme(next);
    }

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('apple-dashboard-theme', theme);
      const icon = document.getElementById('theme-icon');
      if (theme === 'light') {
        icon.setAttribute('icon', 'lucide:moon');
      } else {
        icon.setAttribute('icon', 'lucide:sun');
      }
      if (globalData) {
        renderTop10();
        renderCharts();
      }
    }

    function getThemeTokens() {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      return {
        isLight,
        gridColor: isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.04)',
        tickColor: isLight ? '#6e6e73' : '#86868b',
        titleColor: isLight ? '#1d1d1f' : '#f5f5f7',
        tooltipBg: isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(26, 29, 36, 0.95)',
        tooltipBorder: isLight ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.12)',
        tooltipTitle: isLight ? '#1d1d1f' : '#fff',
        tooltipBody: isLight ? '#6e6e73' : '#86868b'
      };
    }

    async function init() {
      initTheme();
      try {
        const res = await fetch('/api/data');
        globalData = await res.json();
        renderKPIs();
        renderTop10();
        renderCharts();
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      }
    }

    async function refreshDashboard() {
      const icon = document.getElementById('refresh-icon');
      icon.style.transition = 'transform 0.6s ease';
      icon.style.transform = 'rotate(360deg)';
      try {
        await fetch('/api/refresh');
        const res = await fetch('/api/data');
        globalData = await res.json();
        renderKPIs();
        renderTop10();
        renderCharts();
      } finally {
        setTimeout(() => {
          icon.style.transform = 'rotate(0deg)';
        }, 600);
      }
    }

    function renderKPIs() {
      const k = globalData.kpi;
      document.getElementById('kpi-total').textContent = Number(k.total_requests).toLocaleString();
      document.getElementById('kpi-peak').textContent = k.diurnal_peak_hour;
      document.getElementById('kpi-peak-val').textContent = k.diurnal_peak_count.toLocaleString() + ' reqs (Global: ' + k.global_peak_hour + ')';
      document.getElementById('kpi-top-page').textContent = k.top_page;
      document.getElementById('kpi-top-visits').textContent = k.top_page_visits.toLocaleString() + ' total visits';
      document.getElementById('kpi-error').textContent = k.avg_error_rate + '%';
      document.getElementById('kpi-error-sub').textContent = k.total_failed_orders.toLocaleString() + ' / ' + k.total_orders.toLocaleString() + ' orders';
    }

    function renderTop10() {
      const top10 = globalData.top10;
      const totalVisits = top10.reduce((acc, x) => acc + x.visits, 0);
      const tokens = getThemeTokens();

      // Top 10 Chart
      const ctx = document.getElementById('topPagesChart').getContext('2d');
      if (topPagesChart) topPagesChart.destroy();

      topPagesChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: top10.map(d => d.page),
          datasets: [{
            label: 'Visits',
            data: top10.map(d => d.visits),
            backgroundColor: top10.map((d, i) => {
              if (i === 0) return '#ff9f0a';
              if (i === 1) return '#2997ff';
              if (i === 2) return '#bf5af2';
              return tokens.isLight ? 'rgba(0, 113, 227, 0.45)' : 'rgba(41, 151, 255, 0.45)';
            }),
            borderRadius: 8,
            borderSkipped: false
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: tokens.tooltipBg,
              titleColor: tokens.tooltipTitle,
              bodyColor: tokens.tooltipBody,
              borderColor: tokens.tooltipBorder,
              borderWidth: 1,
              padding: 12,
              cornerRadius: 10
            }
          },
          scales: {
            x: {
              grid: { color: tokens.gridColor },
              ticks: { color: tokens.tickColor, font: { size: 11 } }
            },
            y: {
              grid: { display: false },
              ticks: { color: tokens.titleColor, font: { weight: '600', size: 12 } }
            }
          }
        }
      });

      // Table Render
      const tbody = document.getElementById('top10-table-body');
      tbody.innerHTML = top10.map(d => {
        const badgeClass = d.rank === 1 ? 'rank-1' : (d.rank === 2 ? 'rank-2' : (d.rank === 3 ? 'rank-3' : 'rank-other'));
        const pct = ((d.visits / totalVisits) * 100).toFixed(1);
        return `
          <tr>
            <td><span class="rank-pill ${badgeClass}">#${d.rank}</span></td>
            <td>
              <span class="product-code">
                <iconify-icon icon="lucide:package" style="color: var(--apple-blue);"></iconify-icon>
                ${d.page}
              </span>
            </td>
            <td><strong>${Number(d.visits).toLocaleString()}</strong></td>
            <td>
              <div style="display:flex; align-items:center; gap:10px;">
                <div class="bar-bg">
                  <div class="bar-fill" style="width: ${pct}%;"></div>
                </div>
                <span style="font-size:0.8rem; color:var(--text-secondary); width: 45px;">${pct}%</span>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderCharts() {
      if (trafficChart) trafficChart.destroy();
      if (errorChart) errorChart.destroy();

      const tokens = getThemeTokens();
      const trafficCtx = document.getElementById('trafficChart').getContext('2d');
      const errorCtx = document.getElementById('errorChart').getContext('2d');

      // Gradients
      const trafficGradient = trafficCtx.createLinearGradient(0, 0, 0, 300);
      trafficGradient.addColorStop(0, tokens.isLight ? 'rgba(0, 113, 227, 0.28)' : 'rgba(41, 151, 255, 0.35)');
      trafficGradient.addColorStop(1, 'rgba(41, 151, 255, 0.0)');

      const errorGradient = errorCtx.createLinearGradient(0, 0, 0, 240);
      errorGradient.addColorStop(0, tokens.isLight ? 'rgba(215, 0, 21, 0.25)' : 'rgba(255, 69, 58, 0.35)');
      errorGradient.addColorStop(1, 'rgba(255, 69, 58, 0.0)');

      if (currentView === 'diurnal') {
        document.getElementById('traffic-chart-label').textContent = 'Aggregated across 24 hours of day (Peak: ' + globalData.kpi.diurnal_peak_hour + ')';
        document.getElementById('error-chart-label').textContent = 'Average order failure & cancellation rate across 24 hours of day';

        // 1. Diurnal Traffic Chart
        trafficChart = new Chart(trafficCtx, {
          type: 'line',
          data: {
            labels: globalData.hourly_24.map(d => d.hour),
            datasets: [{
              label: 'Total Requests',
              data: globalData.hourly_24.map(d => d.count),
              borderColor: tokens.isLight ? '#0071e3' : '#2997ff',
              backgroundColor: trafficGradient,
              fill: true,
              tension: 0.4,
              borderWidth: 2.8,
              pointRadius: globalData.hourly_24.map(d => d.is_peak ? 7 : 3),
              pointHoverRadius: 9,
              pointBackgroundColor: globalData.hourly_24.map(d => d.is_peak ? (tokens.isLight ? '#d70015' : '#ff453a') : (tokens.isLight ? '#0071e3' : '#2997ff')),
              pointBorderColor: '#fff',
              pointBorderWidth: globalData.hourly_24.map(d => d.is_peak ? 2 : 0)
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.tooltipBg,
                titleColor: tokens.tooltipTitle,
                bodyColor: tokens.tooltipBody,
                borderColor: tokens.tooltipBorder,
                borderWidth: 1,
                padding: 12,
                cornerRadius: 10
              }
            },
            scales: {
              x: {
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor, font: { size: 11 } }
              },
              y: {
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor, font: { size: 11 } }
              }
            }
          }
        });

        // 2. Diurnal Error Chart
        errorChart = new Chart(errorCtx, {
          type: 'line',
          data: {
            labels: globalData.error_24.map(d => d.hour),
            datasets: [{
              label: 'Error Rate (%)',
              data: globalData.error_24.map(d => d.rate),
              borderColor: tokens.isLight ? '#d70015' : '#ff453a',
              backgroundColor: errorGradient,
              fill: true,
              tension: 0.4,
              borderWidth: 2.5,
              pointRadius: 3,
              pointHoverRadius: 7
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.tooltipBg,
                titleColor: tokens.tooltipTitle,
                bodyColor: tokens.tooltipBody,
                borderColor: tokens.tooltipBorder,
                borderWidth: 1,
                padding: 12,
                cornerRadius: 10,
                callbacks: { label: ctx => `Error Rate: ${ctx.parsed.y}%` }
              }
            },
            scales: {
              x: {
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor, font: { size: 11 } }
              },
              y: {
                min: 0,
                max: 100,
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor, callback: v => v + '%' }
              }
            }
          }
        });
      } else {
        document.getElementById('traffic-chart-label').textContent = 'Daily Traffic Timeline (Sampled across dataset timeline)';
        document.getElementById('error-chart-label').textContent = 'Daily Failure Rate (%) Timeline';

        // Timeline Traffic (Bar)
        trafficChart = new Chart(trafficCtx, {
          type: 'bar',
          data: {
            labels: globalData.daily_trend.map(d => d.date),
            datasets: [{
              label: 'Daily Requests',
              data: globalData.daily_trend.map(d => d.traffic),
              backgroundColor: tokens.isLight ? 'rgba(0, 113, 227, 0.75)' : 'rgba(41, 151, 255, 0.75)',
              borderRadius: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.tooltipBg,
                titleColor: tokens.tooltipTitle,
                bodyColor: tokens.tooltipBody,
                borderColor: tokens.tooltipBorder,
                borderWidth: 1,
                padding: 12,
                cornerRadius: 10
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: tokens.tickColor, maxTicksLimit: 12 }
              },
              y: {
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor }
              }
            }
          }
        });

        // Timeline Error (Line)
        errorChart = new Chart(errorCtx, {
          type: 'line',
          data: {
            labels: globalData.daily_trend.map(d => d.date),
            datasets: [{
              label: 'Daily Error Rate (%)',
              data: globalData.daily_trend.map(d => d.error_rate),
              borderColor: tokens.isLight ? '#d70015' : '#ff453a',
              backgroundColor: errorGradient,
              fill: true,
              tension: 0.3,
              borderWidth: 2,
              pointRadius: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.tooltipBg,
                titleColor: tokens.tooltipTitle,
                bodyColor: tokens.tooltipBody,
                borderColor: tokens.tooltipBorder,
                borderWidth: 1,
                padding: 12,
                cornerRadius: 10,
                callbacks: { label: ctx => `Daily Failure: ${ctx.parsed.y}%` }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: tokens.tickColor, maxTicksLimit: 12 }
              },
              y: {
                min: 0,
                max: 100,
                grid: { color: tokens.gridColor },
                ticks: { color: tokens.tickColor, callback: v => v + '%' }
              }
            }
          }
        });
      }
    }

    function switchView(view) {
      currentView = view;
      document.getElementById('btn-diurnal').classList.toggle('active', view === 'diurnal');
      document.getElementById('btn-timeline').classList.toggle('active', view === 'timeline');
      renderCharts();
    }

    init();
  </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            global _CACHED_DATA
            if _CACHED_DATA is None:
                _CACHED_DATA = load_and_aggregate_data()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CACHED_DATA).encode("utf-8"))
        elif self.path == "/api/refresh":
            load_and_aggregate_data()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "refreshed"}')
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

    def log_message(self, format, *args):
        pass

def run():
    print("[*] Pre-computing analytics summaries...")
    load_and_aggregate_data()
    print("[+] Batch Report Dashboard running at http://localhost:{}".format(PORT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run()
