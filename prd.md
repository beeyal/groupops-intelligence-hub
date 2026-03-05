# Product Requirements Document
# Ausnet GroupOps Intelligence Hub — Databricks App Demo

**Version:** 1.0
**Date:** 2026-03-05
**Author:** Field Engineering
**Status:** Draft

---

## 1. Overview

### 1.1 Problem Statement

Ausnet's Group Operations (GroupOps) team manages electricity and gas distribution infrastructure across four Australian zones (Northern, Eastern, Southern, Western). Their operational data lives in two disconnected systems:

- **SAP** — Enterprise system: asset master records, PM work orders, maintenance history, spare parts, costs
- **AVEVA** — OT/SCADA historian: real-time sensor data (voltage, current, temperature, fault events, breaker states, alarms)

**The core gap:** Operators cannot easily answer cross-system questions such as:
*"Show me assets with 3+ fault events this month that don't have an open SAP work order."*

This represents a real operational risk — faulting assets that maintenance teams don't know need attention.

### 1.2 Proposed Solution

A Databricks-powered **GroupOps Intelligence Hub** that:

1. Unifies SAP + AVEVA data into Gold Delta tables under Unity Catalog
2. Provides a purpose-built GroupOps UI (Databricks App) with live operational dashboards
3. Enables natural language querying via Genie Space and an embedded AI chat panel

### 1.3 Demo Narrative

> *"Your SAP knows the work order history. Your AVEVA knows the live sensor readings. But right now, your team can't easily answer: 'Show me assets with 3+ fault events this month that don't have an open SAP work order.' Databricks can."*

---

## 2. Goals & Success Criteria

| Goal | Success Criterion |
|---|---|
| Unified data layer | `ausnet_demo.groupops.*` tables created in Unity Catalog with referential integrity |
| Operational visibility | Dashboard loads with all 4 panels populated from real Gold table data |
| Cross-system insight | Fault vs WO Gap panel surfaces assets with ≥3 faults and zero open WOs |
| AI-assisted operations | Chat panel answers GroupOps-style questions using Foundation Model API |
| Natural language querying | Genie Space returns correct SQL results for all 4 demo questions |

---

## 3. Databricks Features Showcased

| Feature | Ausnet Relevance |
|---|---|
| **Unity Catalog** | They lack data governance — lineage, access control, data discovery |
| **Delta Lake (Gold tables)** | Replaces their Synapse reporting layer with open, performant format |
| **Databricks App** | Purpose-built GroupOps UI — brand new product capability |
| **Foundation Model API** | AI chat over operational data (Claude Sonnet / Llama 3.3 70B) |
| **Genie Space** | Natural language querying across SAP + AVEVA — the "wow" moment |
| **Liquid Clustering** | Addresses their ~1TB satellite table performance issues |

---

## 4. Architecture

```
Synthetic Data Generation (Faker + PySpark)
              ↓
  Gold Delta Tables — ausnet_demo.groupops.*
  ┌─────────────────────┬──────────────────┐
  │  asset_health_360   │   fault_events   │
  ├─────────────────────┼──────────────────┤
  │    work_orders      │  sensor_trends   │
  └─────────────────────┴──────────────────┘
              ↓                    ↓
    Databricks App          Genie Space
   (GroupOps UI)        (NL SQL queries)
   FastAPI + React
```

---

## 5. Data Model — Gold Tables

### 5.1 `ausnet_demo.groupops.asset_health_360`
Main gold table — one row per asset.

| Column | Type | Description |
|---|---|---|
| `asset_id` | STRING | Primary key (e.g., `AST-0001`) |
| `asset_type` | STRING | Transformer / Substation / Overhead Line / Underground Cable / Switchgear |
| `zone` | STRING | Northern / Eastern / Southern / Western |
| `install_year` | INT | 1980–2015 |
| `health_score` | INT | 0–100 (inverse correlation with faults/alarms) |
| `last_fault_date` | DATE | Most recent fault date |
| `fault_count_30d` | INT | Fault events in last 30 days (0–15) |
| `open_wo_count` | INT | Open SAP work orders (0–5) |
| `latest_temp_c` | FLOAT | Latest AVEVA temperature reading |
| `latest_voltage_kv` | FLOAT | Latest AVEVA voltage reading |
| `latest_load_pct` | FLOAT | Load percentage (0–100) |
| `alarm_active` | BOOLEAN | Active AVEVA alarm flag |
| `sap_plant` | STRING | SAP plant code (AU01 / AU02 / AU03) |
| `cost_centre` | STRING | SAP cost centre (CC1001–CC1020) |

**Data rules:**
- ~200 total assets
- `health_score` inversely correlates with `fault_count_30d` and `alarm_active`
- ~15% of assets must have `fault_count_30d >= 3` AND `open_wo_count = 0` (the "gap" for the key insight)

---

### 5.2 `ausnet_demo.groupops.fault_events`
AVEVA fault history — ~1,000 rows covering last 90 days.

| Column | Type | Description |
|---|---|---|
| `fault_id` | STRING | UUID primary key |
| `asset_id` | STRING | FK → `asset_health_360.asset_id` |
| `fault_timestamp` | TIMESTAMP | When fault occurred |
| `fault_type` | STRING | Overvoltage / Thermal / Earth fault / Phase imbalance / Loss of supply |
| `severity` | STRING | Low / Medium / High / Critical |
| `duration_mins` | INT | Fault duration in minutes (5–480) |
| `resolved` | BOOLEAN | Whether fault has been resolved |

---

### 5.3 `ausnet_demo.groupops.work_orders`
SAP work orders — ~400 rows.

| Column | Type | Description |
|---|---|---|
| `wo_number` | STRING | SAP WO number (e.g., `WO-2024-10042`) |
| `asset_id` | STRING | FK → `asset_health_360.asset_id` |
| `wo_type` | STRING | PM (Preventive) / CM (Corrective) / Emergency |
| `status` | STRING | Open / In Progress / Completed / Cancelled |
| `created_date` | DATE | WO creation date |
| `completion_date` | DATE | Nullable — completion date |
| `cost_aud` | FLOAT | Actual cost in AUD |

---

### 5.4 `ausnet_demo.groupops.sensor_trends`
Daily aggregated AVEVA sensor readings — ~18,000 rows (200 assets × 90 days).

| Column | Type | Description |
|---|---|---|
| `asset_id` | STRING | FK → `asset_health_360.asset_id` |
| `reading_date` | DATE | Date of aggregated reading |
| `avg_temp_c` | FLOAT | Average temperature (°C) |
| `max_temp_c` | FLOAT | Max temperature (°C) |
| `avg_voltage_kv` | FLOAT | Average voltage (kV) |
| `avg_load_pct` | FLOAT | Average load percentage |
| `fault_count` | INT | Number of faults on that day |

---

## 6. Application — GroupOps Intelligence Hub

### 6.1 Technical Stack
- **Framework:** APX (FastAPI + React) via `databricks-app-apx` skill
- **App name:** `ausnet-groupops-hub`
- **Auth:** Databricks OAuth (via `app.yaml` resources — no hardcoded tokens)
- **Data access:** Databricks SQL Warehouse (serverless)
- **Styling:** Dark theme — `#1C2333` background, `#FF3621` accent (Databricks red)

### 6.2 Backend API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health-summary` | GET | Asset counts by health status (healthy/warning/critical) grouped by zone |
| `/api/active-alarms` | GET | Top 20 assets with `alarm_active = true`, with latest sensor readings |
| `/api/maintenance-queue` | GET | Open work orders joined with asset health score |
| `/api/fault-wo-gap` | GET | Assets with `fault_count_30d >= 3` AND `open_wo_count = 0` |
| `/api/chat` | POST | AI chat — user message + history → LLM response with data context |

**Health status thresholds:**
- Healthy: `health_score >= 70`
- Warning: `health_score >= 40 AND < 70`
- Critical: `health_score < 40`

### 6.3 Frontend Layout

**Header:** "GroupOps Intelligence Hub | Ausnet" — dark theme navbar

**Two-column layout:**

**Left column (70%) — Dashboard Panels:**

1. **Asset Health Scorecard**
   - Stacked bar or donut chart by zone
   - Shows healthy (green) / warning (amber) / critical (red) asset counts
   - Library: Recharts or Chart.js

2. **Active Alarms Panel**
   - Table columns: Asset ID, Type, Zone, Temp (°C), Voltage (kV), Fault Count, Alarm Status
   - Real-time feel — sorted by fault count descending

3. **Maintenance Queue**
   - Table columns: WO Number, Asset ID, WO Type, Status, Created Date, Cost (AUD), Health Score
   - Health score colour-coded: green ≥70 / amber 40–69 / red <40

4. **Fault vs WO Gap** *(the key insight panel)*
   - Banner: "⚠️ {N} assets have 3+ faults with no open work order"
   - Table of gap assets with asset_id, type, zone, fault_count_30d, health_score
   - Highlighted in amber/red to draw attention

**Right column (30%) — AI Chat Panel:**

- **Prompt starters** (clickable chips):
  - "Which transformers in the northern zone are running hot?"
  - "Show assets with faults but no open work order"
  - "What's the average repair cost for earth faults?"
  - "Which substations had the most faults last month?"
- Chat history display (user messages right-aligned, AI responses left-aligned)
- Text input + Send button
- System prompt provides full Ausnet GroupOps data context

### 6.4 AI Chat — System Prompt

```
You are an operational intelligence assistant for Ausnet's GroupOps team.
You have access to data from two integrated systems:
- SAP: work orders, maintenance history, costs (tables: work_orders, asset_health_360)
- AVEVA: sensor historian, fault events, alarms (tables: fault_events, sensor_trends, asset_health_360)

Asset types: Transformer, Substation, Overhead Line, Underground Cable, Switchgear
Zones: Northern, Eastern, Southern, Western
WO types: PM (Preventive Maintenance), CM (Corrective Maintenance), Emergency
Fault types: Overvoltage, Thermal, Earth fault, Phase imbalance, Loss of supply

Answer operational questions clearly and concisely, referencing actual data.
When relevant, surface the key insight: assets with active faults but no open work order.
```

---

## 7. Genie Space

### 7.1 Configuration
- **Name:** Ausnet GroupOps Intelligence
- **Tables:** `ausnet_demo.groupops.*` (all 4 tables)
- **Warehouse:** Serverless SQL Warehouse

### 7.2 Business Context (for Genie tuning)

> Ausnet manages electricity and gas distribution infrastructure in Australia. Assets include Transformers, Substations, Overhead Lines, Underground Cables, and Switchgear across Northern, Eastern, Southern, and Western zones. SAP work orders track maintenance activities (PM = Preventive, CM = Corrective, Emergency types). AVEVA sensor data provides real-time health metrics including temperature, voltage, load percentage, and fault events. The key operational risk is assets with active fault events but no corresponding SAP work order raised.

### 7.3 Demo Questions + Expected SQL

**Q1:** "Which substations had the most faults last month?"
```sql
SELECT a.asset_id, a.zone, COUNT(f.fault_id) AS fault_count
FROM ausnet_demo.groupops.fault_events f
JOIN ausnet_demo.groupops.asset_health_360 a ON f.asset_id = a.asset_id
WHERE a.asset_type = 'Substation'
  AND f.fault_timestamp >= DATEADD(MONTH, -1, CURRENT_DATE)
GROUP BY a.asset_id, a.zone
ORDER BY fault_count DESC
LIMIT 10;
```

**Q2:** "Show me all assets due for PM in the next 30 days"
```sql
SELECT w.wo_number, w.asset_id, a.asset_type, a.zone, w.created_date, a.health_score
FROM ausnet_demo.groupops.work_orders w
JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
WHERE w.wo_type = 'PM'
  AND w.status IN ('Open', 'In Progress')
ORDER BY a.health_score ASC;
```

**Q3:** "What's the total maintenance cost in the eastern zone this year?"
```sql
SELECT SUM(w.cost_aud) AS total_cost_aud
FROM ausnet_demo.groupops.work_orders w
JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
WHERE a.zone = 'Eastern'
  AND YEAR(w.created_date) = YEAR(CURRENT_DATE);
```

**Q4:** "Which assets have AVEVA alarms but no SAP work order raised?"
```sql
SELECT asset_id, asset_type, zone, fault_count_30d, health_score, latest_temp_c, latest_voltage_kv
FROM ausnet_demo.groupops.asset_health_360
WHERE alarm_active = true
  AND open_wo_count = 0
ORDER BY fault_count_30d DESC;
```

---

## 8. Implementation Plan

| Step | Task | Tool/Skill | Est. Time |
|---|---|---|---|
| 1 | Authenticate with Databricks | `databricks-authentication` | 5 min |
| 2 | Create `ausnet_demo` catalog + `groupops` schema | `databricks-unity-catalog` | 5 min |
| 3 | Generate all 4 Gold tables with synthetic data | `databricks-synthetic-data-generation` | 20 min |
| 4 | Scaffold APX app (FastAPI + React) | `databricks-app-apx` | 15 min |
| 5 | Implement backend API endpoints | `fe-databricks-tools:databricks-apps` | 20 min |
| 6 | Implement frontend dashboard + chat panel | `fe-databricks-tools:databricks-apps` | 30 min |
| 7 | Deploy app to Databricks | `fe-databricks-tools:databricks-apps` | 10 min |
| 8 | Create and tune Genie Space | `databricks-genie` | 20 min |
| 9 | Verify all components | Manual + `databricks-query` | 10 min |

**Total estimated time: ~2 hours**

---

## 9. Workspace Configuration

| Parameter | Value |
|---|---|
| Profile | `fe-vm-sandbox-serverless-sandbox-beyza` |
| Host | `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com` |
| Org ID | `7474651325821186` |
| Catalog | `ausnet_demo` |
| Schema | `groupops` |
| Compute | Serverless SQL Warehouse (no clusters) |

---

## 10. Assumptions

| Area | Assumption |
|---|---|
| SAP version | S/4HANA (standard PM module data model) |
| AVEVA system | AVEVA PI / System Platform historian |
| Zones | Northern, Eastern, Southern, Western (generic Australian geography) |
| Asset types | Transformer, Substation, Overhead Line, Underground Cable, Switchgear |
| Fault types | Overvoltage, Thermal, Earth fault, Phase imbalance, Loss of supply |
| WO types | Preventive Maintenance (PM), Corrective Maintenance (CM), Emergency |
| LLM | `databricks-meta-llama-3-3-70b-instruct` (or Claude Sonnet if available) |

---

## 11. Verification Checklist

- [ ] App loads at Databricks App URL with Ausnet branding
- [ ] Asset Health Scorecard shows chart with data by zone
- [ ] Active Alarms Panel shows real assets with alarm_active = true
- [ ] Maintenance Queue shows open work orders with colour-coded health scores
- [ ] Fault vs WO Gap panel shows assets meeting the gap criteria
- [ ] AI chat responds correctly to all 4 sample questions
- [ ] Genie Space answers all 4 demo questions with correct SQL
- [ ] Unity Catalog lineage shows `ausnet_demo.groupops.*` tables
- [ ] `asset_health_360` data includes ~15% gap assets (fault_count_30d ≥ 3, open_wo_count = 0)
