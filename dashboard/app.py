"""
app.py — Batch Report Dashboard
# ponytail: simple, lightweight Streamlit dashboard reading MapReduce TSV outputs.
"""

import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Clickstream Batch Analytics", layout="wide", page_icon="📊")

st.markdown("# 📊 Batch MapReduce Clickstream Log Analysis")
st.caption("Automated nightly batch analytics powered by Hadoop HDFS, MapReduce & YARN")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
PEAK_PATH = os.path.join(OUTPUT_DIR, "peak_traffic.tsv")
TOP10_PATH = os.path.join(OUTPUT_DIR, "top_10_pages.tsv")
ERROR_PATH = os.path.join(OUTPUT_DIR, "error_rates.tsv")

# ── Load Data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    hourly_records = []
    global_peak_hour, global_peak_val = "N/A", 0
    if os.path.exists(PEAK_PATH):
        with open(PEAK_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts[0] == "PEAK_TRAFFIC_HOUR":
                    global_peak_hour = parts[1]
                    global_peak_val = int(parts[2])
                elif len(parts) >= 2:
                    hourly_records.append({"datetime_hour": parts[0], "requests": int(parts[1])})

    df_peak = pd.DataFrame(hourly_records)
    if not df_peak.empty:
        df_peak["hour_of_day"] = df_peak["datetime_hour"].apply(lambda x: x.split(" ")[1] + ":00" if " " in x else x)
        df_peak["date"] = df_peak["datetime_hour"].apply(lambda x: x.split(" ")[0] if " " in x else x)

    # Top 10
    top10_records = []
    if os.path.exists(TOP10_PATH):
        with open(TOP10_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    top10_records.append({"rank": int(parts[0]), "page": parts[1], "visits": int(parts[2])})
    df_top10 = pd.DataFrame(top10_records)

    # Errors
    err_records = []
    if os.path.exists(ERROR_PATH):
        with open(ERROR_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 4:
                    err_records.append({
                        "datetime_hour": parts[0],
                        "total": int(parts[1]),
                        "errors": int(parts[2]),
                        "rate_pct": float(parts[3].replace("%", ""))
                    })
    df_errors = pd.DataFrame(err_records)
    if not df_errors.empty:
        df_errors["hour_of_day"] = df_errors["datetime_hour"].apply(lambda x: x.split(" ")[1] + ":00" if " " in x else x)
        df_errors["date"] = df_errors["datetime_hour"].apply(lambda x: x.split(" ")[0] if " " in x else x)

    return df_peak, global_peak_hour, global_peak_val, df_top10, df_errors

df_peak, global_peak_hour, global_peak_val, df_top10, df_errors = load_data()

# ── KPI Cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

total_traffic = int(df_peak["requests"].sum()) if not df_peak.empty else 0
total_orders = int(df_errors["total"].sum()) if not df_errors.empty else 0
total_failed = int(df_errors["errors"].sum()) if not df_errors.empty else 0
avg_error = (total_failed / total_orders * 100.0) if total_orders > 0 else 0.0
top_page_name = df_top10.iloc[0]["page"] if not df_top10.empty else "N/A"
top_visits = df_top10.iloc[0]["visits"] if not df_top10.empty else 0

# Diurnal peak hour
diurnal_peak_hr = "N/A"
diurnal_peak_cnt = 0
if not df_peak.empty:
    diurnal_traffic = df_peak.groupby("hour_of_day")["requests"].sum().reset_index()
    diurnal_traffic = diurnal_traffic.sort_values(by="hour_of_day")
    p_idx = diurnal_traffic["requests"].idxmax()
    diurnal_peak_hr = diurnal_traffic.loc[p_idx, "hour_of_day"]
    diurnal_peak_cnt = int(diurnal_traffic.loc[p_idx, "requests"])
else:
    diurnal_traffic = pd.DataFrame()

with c1:
    st.metric("Total Clickstream Requests", f"{total_traffic:,}")
with c2:
    st.metric("Peak Hour of Day", f"{diurnal_peak_hr}", f"{diurnal_peak_cnt:,} reqs")
with c3:
    st.metric("Top Product / Page", top_page_name, f"{top_visits:,} visits")
with c4:
    st.metric("Transaction Failure Rate", f"{avg_error:.2f}%", f"{total_failed:,} failed")

st.divider()

# ── View Mode Selector ───────────────────────────────────────────────────────
view_mode = st.radio("Select Analytics View:", ["24-Hour Diurnal Pattern (Clean Aggregate)", "Multi-Month Timeline"], horizontal=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("⏰ Traffic Volume (Peak Highlighted)")
    if view_mode.startswith("24-Hour") and not diurnal_traffic.empty:
        st.line_chart(diurnal_traffic.set_index("hour_of_day")["requests"])
        st.info(f"🏆 **Peak Operating Hour:** `{diurnal_peak_hr}` with **{diurnal_peak_cnt:,} total requests** (Global peak: `{global_peak_hour}`).")
    elif not df_peak.empty:
        daily_traffic = df_peak.groupby("date")["requests"].sum()
        st.bar_chart(daily_traffic)
    else:
        st.warning("No peak traffic data found.")

with col_right:
    st.subheader("🌐 Top 10 Most Visited Products")
    if not df_top10.empty:
        chart_data = df_top10.sort_values(by="visits", ascending=True).set_index("page")["visits"]
        st.bar_chart(chart_data)
    else:
        st.warning("No top pages data found.")

st.divider()

st.subheader("⚠️ Hourly Failure & Error Rate (%)")
if not df_errors.empty:
    if view_mode.startswith("24-Hour"):
        diurnal_err = df_errors.groupby("hour_of_day").apply(lambda g: (g["errors"].sum() / g["total"].sum()) * 100.0).reset_index(name="rate_pct")
        diurnal_err = diurnal_err.sort_values(by="hour_of_day")
        st.line_chart(diurnal_err.set_index("hour_of_day")["rate_pct"])
    else:
        daily_err = df_errors.groupby("date").apply(lambda g: (g["errors"].sum() / g["total"].sum()) * 100.0)
        st.line_chart(daily_err)
    st.caption("Percentage of cancelled/returned transaction statuses per hour")
else:
    st.warning("No error rate data found.")

# ── Raw Data Tables ──────────────────────────────────────────────────────────
with st.expander("🔍 View Raw Batch Report Tables"):
    tab1, tab2, tab3 = st.tabs(["Peak Traffic", "Top 10 Pages", "Error Rates"])
    with tab1:
        st.dataframe(df_peak.head(100), use_container_width=True)
    with tab2:
        st.dataframe(df_top10, use_container_width=True)
    with tab3:
        st.dataframe(df_errors.head(100), use_container_width=True)
