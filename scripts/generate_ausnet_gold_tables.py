"""
Generate synthetic Gold Delta tables for Ausnet GroupOps demo.
Tables: asset_health_360, fault_events, work_orders, sensor_trends
Catalog: ausnet_demo.groupops
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
import uuid
import random

# =============================================================================
# CONFIGURATION
# =============================================================================
CATALOG = "ausnet_demo"
SCHEMA = "groupops"

N_ASSETS = 200
N_FAULTS = 1000
N_WO = 400
# sensor_trends: 200 assets x 90 days = 18000 rows

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE_90 = END_DATE - timedelta(days=90)
START_DATE_12M = END_DATE - timedelta(days=365)

# =============================================================================
# SETUP
# =============================================================================
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

print(f"Catalog: {CATALOG}.{SCHEMA}")
print(f"Spark version: {spark.version}")

# Catalog/schema already created externally, but ensure schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# =============================================================================
# TABLE 1: asset_health_360 (200 rows)
# =============================================================================
print("\n--- Generating asset_health_360 ---")

asset_types   = ["Transformer", "Substation", "Overhead Line", "Underground Cable", "Switchgear"]
zones         = ["Northern", "Eastern", "Southern", "Western"]
voltage_levels = [6.6, 11.0, 22.0, 33.0, 66.0, 132.0]
sap_plants    = ["AU01", "AU02", "AU03"]

assets = []
for i in range(1, N_ASSETS + 1):
    asset_id    = f"AST-{i:04d}"
    asset_type  = random.choice(asset_types)
    zone        = random.choice(zones)
    install_year = random.randint(1980, 2015)
    health_score = random.randint(0, 100)
    last_fault_date = (END_DATE - timedelta(days=random.randint(1, 90))).date()
    latest_temp_c   = round(random.uniform(20.0, 95.0), 1)
    latest_voltage_kv = random.choice(voltage_levels)
    latest_load_pct = round(random.uniform(0.0, 100.0), 1)
    sap_plant   = random.choice(sap_plants)
    cost_centre = f"CC{random.randint(1001, 1020)}"

    # fault_count_30d: most 0-2, ~15% will be >=3 (enforced below)
    fault_count_30d = int(np.random.choice(
        [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
        p=[0.30,0.20,0.15,0.07,0.06,0.05,0.04,0.03,0.02,0.02,0.01,0.01,0.01,0.01,0.01,0.01]
    ))
    open_wo_count = random.randint(0, 5)
    alarm_active  = bool(health_score < 50 or fault_count_30d >= 3)

    assets.append({
        "asset_id": asset_id,
        "asset_type": asset_type,
        "zone": zone,
        "install_year": install_year,
        "health_score": health_score,
        "last_fault_date": last_fault_date,
        "fault_count_30d": fault_count_30d,
        "open_wo_count": open_wo_count,
        "latest_temp_c": latest_temp_c,
        "latest_voltage_kv": latest_voltage_kv,
        "latest_load_pct": latest_load_pct,
        "alarm_active": alarm_active,
        "sap_plant": sap_plant,
        "cost_centre": cost_centre,
    })

assets_df = pd.DataFrame(assets)

# ---- Enforce critical data rule: ~15% (30 assets) with fault_count_30d>=3 AND open_wo_count=0 ----
# First, identify how many already have fault_count_30d >= 3
high_fault_mask = assets_df["fault_count_30d"] >= 3
n_high = high_fault_mask.sum()
print(f"  Initial high-fault assets (>=3): {n_high}")

# We want ~30 gap assets (fault_count_30d>=3 AND open_wo_count=0)
# Ensure at least 30 assets have fault_count_30d >= 3
if n_high < 45:  # need at least 45 to allow 30 gaps
    # Randomly assign fault_count_30d >= 3 to more assets
    non_high_idx = assets_df[~high_fault_mask].index.tolist()
    needed = 45 - n_high
    chosen = random.sample(non_high_idx, min(needed, len(non_high_idx)))
    for idx in chosen:
        assets_df.at[idx, "fault_count_30d"] = random.randint(3, 10)
        assets_df.at[idx, "alarm_active"] = True

high_fault_idx = assets_df[assets_df["fault_count_30d"] >= 3].index.tolist()
print(f"  After adjustment - high-fault assets: {len(high_fault_idx)}")

# Set exactly 30 of them as gap assets (open_wo_count = 0)
gap_idx = random.sample(high_fault_idx, 30)
for idx in gap_idx:
    assets_df.at[idx, "open_wo_count"] = 0

# The rest of high-fault assets should have open_wo_count > 0
non_gap_high = [i for i in high_fault_idx if i not in gap_idx]
for idx in non_gap_high:
    if assets_df.at[idx, "open_wo_count"] == 0:
        assets_df.at[idx, "open_wo_count"] = random.randint(1, 5)

# Recompute alarm_active
assets_df["alarm_active"] = (assets_df["health_score"] < 50) | (assets_df["fault_count_30d"] >= 3)

n_gap = len(assets_df[(assets_df["fault_count_30d"] >= 3) & (assets_df["open_wo_count"] == 0)])
print(f"  Gap assets (fault>=3, open_wo=0): {n_gap}")

# Save asset_health_360
spark.createDataFrame(assets_df).write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.asset_health_360")
print(f"  Saved asset_health_360: {len(assets_df)} rows")

asset_ids = assets_df["asset_id"].tolist()
asset_voltage_map = dict(zip(assets_df["asset_id"], assets_df["latest_voltage_kv"]))
print(f"  First 10 asset IDs: {asset_ids[:10]}")

# =============================================================================
# TABLE 2: fault_events (1000 rows)
# =============================================================================
print("\n--- Generating fault_events ---")

fault_types = ["Overvoltage", "Thermal", "Earth fault", "Phase imbalance", "Loss of supply"]
severities  = ["Low", "Medium", "High", "Critical"]

faults = []
for i in range(N_FAULTS):
    asset_id  = random.choice(asset_ids)
    ts_offset = timedelta(
        seconds=random.randint(0, int((END_DATE - START_DATE_90).total_seconds()))
    )
    fault_ts  = START_DATE_90 + ts_offset
    severity  = random.choices(severities, weights=[0.3, 0.35, 0.25, 0.10])[0]
    resolved  = random.random() < 0.80

    faults.append({
        "fault_id": str(uuid.uuid4()),
        "asset_id": asset_id,
        "fault_timestamp": fault_ts,
        "fault_type": random.choice(fault_types),
        "severity": severity,
        "duration_mins": random.randint(5, 480),
        "resolved": resolved,
    })

faults_df = pd.DataFrame(faults)
spark.createDataFrame(faults_df).write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.fault_events")
print(f"  Saved fault_events: {len(faults_df)} rows")

# =============================================================================
# TABLE 3: work_orders (400 rows)
# =============================================================================
print("\n--- Generating work_orders ---")

wo_types   = ["PM", "CM", "Emergency"]
wo_statuses = ["Open", "In Progress", "Completed", "Cancelled"]
wo_status_weights = [0.30, 0.20, 0.40, 0.10]

cost_ranges = {
    "PM":        (500,   5000),
    "CM":        (2000,  25000),
    "Emergency": (10000, 80000),
}

work_orders = []
for i in range(1, N_WO + 1):
    wo_number = f"WO-2024-{10000 + i}"
    asset_id  = random.choice(asset_ids)
    wo_type   = random.choices(wo_types, weights=[0.4, 0.45, 0.15])[0]
    status    = random.choices(wo_statuses, weights=wo_status_weights)[0]

    created_date = (END_DATE - timedelta(days=random.randint(1, 365))).date()

    if status == "Completed":
        completion_date = (datetime.combine(created_date, datetime.min.time()) +
                           timedelta(days=random.randint(1, 30))).date()
        # ensure completion <= today
        if completion_date > END_DATE.date():
            completion_date = END_DATE.date()
    else:
        completion_date = None

    lo, hi = cost_ranges[wo_type]
    cost_aud = round(random.uniform(lo, hi), 2)

    work_orders.append({
        "wo_number": wo_number,
        "asset_id": asset_id,
        "wo_type": wo_type,
        "status": status,
        "created_date": created_date,
        "completion_date": completion_date,
        "cost_aud": cost_aud,
    })

wo_df = pd.DataFrame(work_orders)
spark.createDataFrame(wo_df).write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.work_orders")
print(f"  Saved work_orders: {len(wo_df)} rows")

# =============================================================================
# TABLE 4: sensor_trends (200 assets x 90 days = 18000 rows)
# =============================================================================
print("\n--- Generating sensor_trends ---")

sensor_rows = []
date_range = [START_DATE_90.date() + timedelta(days=d) for d in range(91)]

for asset_id in asset_ids:
    base_voltage = asset_voltage_map[asset_id]
    for reading_date in date_range:
        avg_temp   = round(random.uniform(20.0, 90.0), 1)
        max_temp   = round(avg_temp + random.uniform(2.0, 10.0), 1)
        avg_load   = round(random.uniform(20.0, 95.0), 1)
        fault_cnt  = random.choices([0,1,2,3,4,5], weights=[0.65,0.15,0.08,0.05,0.04,0.03])[0]
        # voltage drifts slightly around the rated level
        avg_volt   = round(base_voltage * random.uniform(0.97, 1.03), 2)

        sensor_rows.append({
            "asset_id": asset_id,
            "reading_date": reading_date,
            "avg_temp_c": avg_temp,
            "max_temp_c": max_temp,
            "avg_voltage_kv": avg_volt,
            "avg_load_pct": avg_load,
            "fault_count": fault_cnt,
        })

sensor_df = pd.DataFrame(sensor_rows)
spark.createDataFrame(sensor_df).write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.sensor_trends")
print(f"  Saved sensor_trends: {len(sensor_df)} rows")

# =============================================================================
# VALIDATION SUMMARY
# =============================================================================
print("\n=== VALIDATION SUMMARY ===")
print(f"asset_health_360 rows : {len(assets_df)}")
print(f"fault_events rows     : {len(faults_df)}")
print(f"work_orders rows      : {len(wo_df)}")
print(f"sensor_trends rows    : {len(sensor_df)}")

gap_count = len(assets_df[(assets_df["fault_count_30d"] >= 3) & (assets_df["open_wo_count"] == 0)])
high_fault_count = len(assets_df[assets_df["fault_count_30d"] >= 3])
print(f"\nHigh-fault assets (fault_count_30d>=3): {high_fault_count} ({high_fault_count/N_ASSETS*100:.1f}%)")
print(f"Gap assets (fault>=3, open_wo=0)      : {gap_count} ({gap_count/N_ASSETS*100:.1f}%)")
print(f"Alarm active assets                   : {assets_df['alarm_active'].sum()}")

print(f"\nWork order status distribution:")
print(wo_df["status"].value_counts().to_dict())

print(f"\nFault severity distribution:")
print(faults_df["severity"].value_counts().to_dict())

print(f"\nFirst 10 asset IDs: {asset_ids[:10]}")
print("\nDONE - All 4 Gold Delta tables written to ausnet_demo.groupops")
