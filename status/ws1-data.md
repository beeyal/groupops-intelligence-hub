# WS1 Status: Authentication + Synthetic Data Generation

**Completed:** 2026-03-05
**Workstream:** WS1 - Authentication + Synthetic Data Generation for Ausnet GroupOps Demo

---

## Summary: ALL STEPS COMPLETED SUCCESSFULLY

---

## Step 1: Authentication

- **Profile:** `fe-vm-sandbox-serverless-sandbox-beyza`
- **Workspace URL:** `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com`
- **Status:** VALID (confirmed via `databricks auth profiles`)

---

## Step 2: Catalog + Schema Creation

- **Catalog:** `ausnet_demo`
- **Schema:** `ausnet_demo.groupops`
- **Storage:** `s3://serverless-sandbox-beyza-ext-s3-332745928618-yto7sb/ausnet_demo`
- **Status:** SUCCEEDED

**Note:** The metastore did not have a default storage root configured, so the catalog was created with an explicit `MANAGED LOCATION` pointing to the existing external location for the beyza sandbox (`serverless-sandbox-beyza-ext-role-332745928618-yto7sb-el-slxzzw`). This is the correct approach for this workspace.

SQL used:
```sql
CREATE CATALOG IF NOT EXISTS ausnet_demo
  MANAGED LOCATION 's3://serverless-sandbox-beyza-ext-s3-332745928618-yto7sb/ausnet_demo';
CREATE SCHEMA IF NOT EXISTS ausnet_demo.groupops;
```

---

## Step 3: Gold Delta Tables Generated

All 4 tables written via Databricks Job Run ID `50772071627140` (serverless compute, with `faker` library). Notebook at `/ausnet_demo/generate_ausnet_gold_tables` in the workspace.

### Table Counts (verified via SQL warehouse)

| Table | Expected | Actual |
|-------|----------|--------|
| `ausnet_demo.groupops.asset_health_360` | ~200 | **200** |
| `ausnet_demo.groupops.fault_events` | ~1000 | **1000** |
| `ausnet_demo.groupops.work_orders` | ~400 | **400** |
| `ausnet_demo.groupops.sensor_trends` | ~18000 | **18200** |

*(sensor_trends is 200 assets x 91 days = 18200, slightly over the ~18000 target — this is correct)*

---

## Critical Business Rule Validation

| Rule | Target | Actual | Status |
|------|--------|--------|--------|
| Assets with `fault_count_30d >= 3` | ~15% (30+) | **66 (33%)** | PASS |
| "Gap assets" (`fault_count_30d >= 3` AND `open_wo_count = 0`) | ~15% (30) | **30 (15%)** | PASS |
| `alarm_active = TRUE` when health_score < 50 OR fault_count_30d >= 3 | Enforced | **125 assets** | PASS |

---

## First 10 Asset IDs (asset_health_360)

```
AST-0001
AST-0002
AST-0003
AST-0004
AST-0005
AST-0006
AST-0007
AST-0008
AST-0009
AST-0010
```

Full range: `AST-0001` to `AST-0200`

---

## Data Distributions

### Work Orders (400 total)
| WO Type | Cancelled | Completed | In Progress | Open |
|---------|-----------|-----------|-------------|------|
| CM | 15 | 66 | 32 | 57 |
| Emergency | 10 | 26 | 15 | 16 |
| PM | 22 | 60 | 31 | 50 |

Overall status mix: ~25% Open, ~20% In Progress, ~38% Completed, ~12% Cancelled (close to target 30/20/40/10).

### Fault Events (1000 total)
| Severity | Count |
|----------|-------|
| Medium | 337 |
| Low | 314 |
| High | 265 |
| Critical | 84 |

Resolved: ~80%, Unresolved: ~20%

### Alarm Active
- Active (`TRUE`): 125 assets (62.5%)
- Inactive (`FALSE`): 75 assets (37.5%)

---

## Catalog + Schema Paths

| Resource | Path |
|----------|------|
| Catalog | `ausnet_demo` |
| Schema | `ausnet_demo.groupops` |
| Table 1 | `ausnet_demo.groupops.asset_health_360` |
| Table 2 | `ausnet_demo.groupops.fault_events` |
| Table 3 | `ausnet_demo.groupops.work_orders` |
| Table 4 | `ausnet_demo.groupops.sensor_trends` |
| Workspace | `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com` |
| Job Run | `https://fe-sandbox-serverless-sandbox-beyza.cloud.databricks.com/?o=7474651325821186#job/279956495346895/run/50772071627140` |
| SQL Warehouse | `01528c33e8098b4d` (Serverless Starter Warehouse) |

---

## Generation Script

Local path: `/Users/beyza.yalavac/claud_projects/ausnet-demo-groupopsapp/scripts/generate_ausnet_gold_tables.py`
Workspace path: `/ausnet_demo/generate_ausnet_gold_tables`

---

## Errors Encountered + Resolutions

1. **`CREATE CATALOG` failed with BAD_REQUEST** - Metastore storage root URL does not exist.
   - **Resolution:** Used `CREATE CATALOG IF NOT EXISTS ausnet_demo MANAGED LOCATION 's3://serverless-sandbox-beyza-ext-s3-332745928618-yto7sb/ausnet_demo'` with the user's dedicated external location.

2. **No running interactive clusters** - `databricks clusters list` returned empty list.
   - **Resolution:** Used the Jobs API (`/api/2.1/jobs/runs/submit`) with serverless compute and `environments` spec to install `faker`. Job ran successfully.

3. **`databricks workspace import` syntax** - CLI required `--file=` flag for local file path.
   - **Resolution:** Used `--file=/path/to/file` flag instead of positional argument.

---

## Notes for Next Workstreams (WS2, WS3, WS4)

1. **Profile to use:** `fe-vm-sandbox-serverless-sandbox-beyza`
2. **SQL Warehouse ID:** `01528c33e8098b4d` (Serverless Starter Warehouse)
3. **Catalog:** `ausnet_demo`, **Schema:** `ausnet_demo.groupops`
4. **All asset_ids** follow the format `AST-0001` to `AST-0200`
5. **Gap assets** (the key business insight - assets with active faults but no open work orders) = 30 assets with `fault_count_30d >= 3` AND `open_wo_count = 0`. This is the central KPI insight for the GroupOps Intelligence Hub dashboard.
6. **Date ranges:**
   - `fault_events.fault_timestamp`: last 90 days from 2026-03-05
   - `work_orders.created_date`: last 12 months from 2026-03-05
   - `sensor_trends.reading_date`: last 90 days (91 days inclusive)
7. **Referential integrity:** `fault_events.asset_id` and `work_orders.asset_id` both reference valid `asset_id` values from `asset_health_360`
8. **Faker seed:** 42 (reproducible data if script is re-run)
9. **Storage:** Tables stored in `s3://serverless-sandbox-beyza-ext-s3-332745928618-yto7sb/ausnet_demo/` (Delta format)
