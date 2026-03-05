# WS4: Genie Space — Ausnet GroupOps Intelligence

**Status:** COMPLETE
**Date:** 2026-03-05

---

## Genie Space Details

| Field | Value |
|-------|-------|
| **Name** | Ausnet GroupOps Intelligence |
| **Space ID** | `01f1182ef2011e7e842b495788150cde` |
| **Workspace** | `fe-vm-sandbox-serverless-sandbox-beyza` |
| **Host** | `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com` |
| **Warehouse ID** | `01528c33e8098b4d` (Serverless Starter Warehouse — RUNNING) |
| **URL** | `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com/genie/rooms/01f1182ef2011e7e842b495788150cde` |

---

## Tables Registered

| Table | Rows |
|-------|------|
| `ausnet_demo.groupops.asset_health_360` | 200 |
| `ausnet_demo.groupops.fault_events` | 1000 |
| `ausnet_demo.groupops.work_orders` | 400 |
| `ausnet_demo.groupops.sensor_trends` | 18200 |

All 4 gold tables from the `ausnet_demo.groupops` schema are registered.

---

## Business Context Added

The following business context was added as the Genie Space description:

```
Ausnet manages electricity and gas distribution infrastructure in Australia.

ASSETS: Transformers, Substations, Overhead Lines, Underground Cables, and Switchgear
across four zones: Northern, Eastern, Southern, and Western.

SAP DATA (work_orders table): Tracks maintenance activities.
- WO types: PM (Preventive Maintenance), CM (Corrective Maintenance), Emergency
- WO status: Open, In Progress, Completed, Cancelled
- cost_aud is in Australian dollars

AVEVA DATA (fault_events, sensor_trends, asset_health_360 sensor columns): Real-time and historical sensor health.
- Fault types: Overvoltage, Thermal, Earth fault, Phase imbalance, Loss of supply
- Severity levels: Low, Medium, High, Critical
- health_score: 0-100 (70+ = healthy, 40-69 = warning, <40 = critical)
- alarm_active: True means an active AVEVA alarm is present

KEY BUSINESS INSIGHT: The most important query is assets where fault_count_30d >= 3
AND open_wo_count = 0. These are assets with active faults but no SAP work order
raised — an operational risk.

SAP plants: AU01, AU02, AU03 (Australian operations)
```

---

## Example Questions Configured

All 5 example questions are registered as **Sample Questions** (appear in UI) and as **SQL Instructions** (guide Genie's query generation).

### Q1: Which substations had the most faults last month?
```sql
SELECT a.asset_id, a.zone, COUNT(f.fault_id) AS fault_count
FROM ausnet_demo.groupops.fault_events f
JOIN ausnet_demo.groupops.asset_health_360 a ON f.asset_id = a.asset_id
WHERE a.asset_type = 'Substation'
  AND f.fault_timestamp >= DATEADD(DAY, -30, CURRENT_TIMESTAMP)
GROUP BY a.asset_id, a.zone
ORDER BY fault_count DESC
LIMIT 10
```

### Q2: Show me all assets due for preventive maintenance
```sql
SELECT w.wo_number, w.asset_id, a.asset_type, a.zone, w.created_date, a.health_score
FROM ausnet_demo.groupops.work_orders w
JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
WHERE w.wo_type = 'PM'
  AND w.status IN ('Open', 'In Progress')
ORDER BY a.health_score ASC
```

### Q3: What's the total maintenance cost in the eastern zone this year?
```sql
SELECT SUM(w.cost_aud) AS total_cost_aud, COUNT(*) AS work_order_count
FROM ausnet_demo.groupops.work_orders w
JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
WHERE a.zone = 'Eastern'
  AND YEAR(w.created_date) = YEAR(CURRENT_DATE)
```

### Q4: Which assets have AVEVA alarms but no SAP work order raised?
```sql
SELECT asset_id, asset_type, zone, fault_count_30d, health_score, latest_temp_c, latest_voltage_kv
FROM ausnet_demo.groupops.asset_health_360
WHERE alarm_active = true
  AND open_wo_count = 0
ORDER BY fault_count_30d DESC
```

### Q5: What is the average repair cost for earth faults?
```sql
SELECT AVG(w.cost_aud) AS avg_cost_aud, COUNT(*) AS count
FROM ausnet_demo.groupops.work_orders w
JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
JOIN ausnet_demo.groupops.fault_events f ON f.asset_id = a.asset_id
WHERE f.fault_type = 'Earth fault'
  AND w.wo_type = 'CM'
```

---

## Errors and Resolutions

### Issue 1: REST API requires `serialized_space` field
- **Symptom:** Direct `POST /api/2.0/genie/spaces` returned `INVALID_PARAMETER_VALUE: Field 'serialized_space' is required`
- **Root cause:** The public Genie REST API requires a pre-serialized space export proto (versions 1 or 2), not a simple JSON payload.
- **Resolution:** Used `databricks_tools_core.agent_bricks.AgentBricksManager.genie_create()` from the MCP server's Python library (`/Users/beyza.yalavac/mcp/repo/databricks-mcp-server/`), which uses the internal `/api/2.0/data-rooms` endpoint. This creates the space correctly and supports adding sample questions and SQL instructions.

### Issue 2: Databricks CLI `create-space` also requires serialized proto
- **Symptom:** `databricks genie create-space --json '...'` returned `Error: Invalid export proto: ExportConverter supports versions 1 and 2, but got 0`
- **Root cause:** The CLI wraps the same API and requires a valid serialized space export, not an empty JSON.
- **Resolution:** Same as above — bypassed CLI and used Python SDK directly.

### Issue 3: MCP server default profile is `e2-demo-west`
- **Symptom:** The MCP server in `~/.claude/mcp.json` is configured with `DATABRICKS_CONFIG_PROFILE=e2-demo-west`
- **Resolution:** Overrode `os.environ['DATABRICKS_CONFIG_PROFILE']` at runtime before instantiating `AgentBricksManager`, pointing it to `fe-vm-sandbox-serverless-sandbox-beyza`.

---

## How to Access and Demo the Genie Space

### Direct URL
```
https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com/genie/rooms/01f1182ef2011e7e842b495788150cde
```

### Navigation via Databricks UI
1. Log in to `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com`
2. In the left sidebar, click **Genie** (AI/BI section)
3. Find **"Ausnet GroupOps Intelligence"** in the space list
4. Click to open the space

### Demo Script
1. **Open the space** — the 5 sample questions appear as clickable prompts
2. **Key demo question (operational risk):** Ask *"Which assets have AVEVA alarms but no SAP work order raised?"* — this highlights assets with active faults and no maintenance work order, the core business risk insight
3. **Cross-system query:** Ask *"Which substations had the most faults last month?"* to show SAP + AVEVA data joining
4. **Cost analysis:** Ask *"What's the total maintenance cost in the eastern zone this year?"* for financial view
5. **Maintenance queue:** Ask *"Show me all assets due for preventive maintenance"* sorted by health score
6. **Try natural language variants** — Genie accepts questions like "Show me critical assets with no work orders" or "How much have we spent on corrective maintenance?"

### Programmatic Access (API)
```python
import os
os.environ['DATABRICKS_CONFIG_PROFILE'] = 'fe-vm-sandbox-serverless-sandbox-beyza'

from databricks_tools_core.agent_bricks import AgentBricksManager

manager = AgentBricksManager()
SPACE_ID = '01f1182ef2011e7e842b495788150cde'

# Ask a question
from databricks.sdk import WorkspaceClient
from datetime import timedelta

w = WorkspaceClient(profile='fe-vm-sandbox-serverless-sandbox-beyza')
result = w.genie.start_conversation_and_wait(
    space_id=SPACE_ID,
    content="Which assets have AVEVA alarms but no SAP work order raised?",
    timeout=timedelta(seconds=120)
)
```

---

## Summary

| Component | Status |
|-----------|--------|
| Genie Space created | DONE |
| 4 tables registered | DONE |
| Business context / description | DONE |
| 5 sample questions (UI prompts) | DONE |
| 5 SQL instructions (query guidance) | DONE |
| Warehouse connected (RUNNING) | DONE |
