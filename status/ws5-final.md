# WS5 Final - Chat Query Fixes & Verification

**Date:** 2026-03-05
**App URL:** https://ausnet-groupops-hub-7474651325821186.aws.databricksapps.com
**Deployment ID:** 01f1183d885314a0b759c182e2a56ee6

---

## Diagnostic Query Results

### Query A -- Transformer + Northern zone + temperatures

```
asset_id  | asset_type   | zone     | latest_temp_c | health_score | alarm_active
----------|------------- |----------|---------------|--------------|-------------
AST-0018  | Transformer  | Northern | 87.9          | 29           | true
AST-0058  | Transformer  | Northern | 82.9          | 31           | true
AST-0034  | Transformer  | Northern | 82.6          | 69           | true
AST-0110  | Transformer  | Northern | 49.1          | 68           | false
AST-0154  | Transformer  | Northern | 40.5          | 10           | true
AST-0132  | Transformer  | Northern | 33.2          | 95           | false
AST-0001  | Transformer  | Northern | 30.5          | 31           | true
AST-0104  | Transformer  | Northern | 22.5          | 100          | false
AST-0159  | Transformer  | Northern | 21.2          | 76           | false
```

**Key finding:** 9 transformers total in Northern zone. 3 above 70C, 0 between 60-70C. Lowering threshold from 70C to 60C keeps the same 3 results for this specific query, but broadens coverage for other asset types/zones.

### Query B -- Earth fault WO cost (with CM/Emergency filter)

| wo_count | avg_cost_aud |
|----------|-------------|
| 149      | 22,707.65   |

### Query C -- Earth fault WO cost (without type filter)

| wo_count | avg_cost_aud | total_cost_aud |
|----------|-------------|----------------|
| 231      | 15,703.68   | 3,627,550.90   |

**Key finding:** Removing the `wo_type IN ('CM', 'Emergency')` restriction captures 82 more work orders (231 vs 149). The average drops from $22,707.65 to $15,703.68 because PM work orders are generally cheaper, but total cost coverage is more complete.

---

## Fixes Applied

### Fix A -- Hot assets temperature threshold

**File:** `/Users/beyza.yalavac/claud_projects/ausnet-demo-groupopsapp/app/server/llm.py` line 88

- Changed `latest_temp_c > 70` to `latest_temp_c > 60`
- Updated all labels from "(temp > 70C)" to "(temp > 60C)"
- Zone and asset_type filters were already present in the code (added in earlier WS)

### Fix B -- Earth fault cost query

**File:** `/Users/beyza.yalavac/claud_projects/ausnet-demo-groupopsapp/app/server/llm.py` lines 140-174

- Removed `AND w.wo_type IN ('CM', 'Emergency')` restriction from the fault_type_match branch
- Added robust null/zero check: `rows[0].get('wo_count') and int(rows[0]['wo_count']) > 0`
- Added fallback query: if wo_count is 0, queries fault_events directly for event count, asset count, and avg duration

### Fix C -- Fault type case mismatch (discovered during testing)

**File:** `/Users/beyza.yalavac/claud_projects/ausnet-demo-groupopsapp/app/server/llm.py` lines 77-90

**Root cause:** `.title()` converted "earth fault" to "Earth Fault" but the database stores "Earth fault" (lowercase 'f'). Same issue for "Loss of supply" vs "Loss Of Supply" and "Phase imbalance" vs "Phase Imbalance".

**Fix:** Replaced generic `.title()` call with an explicit mapping dictionary:
```python
fault_type_map = {
    "overvoltage": "Overvoltage",
    "thermal": "Thermal",
    "earth fault": "Earth fault",
    "phase imbalance": "Phase imbalance",
    "loss of supply": "Loss of supply",
}
```

---

## Deployment Notes

1. Initial deploy (01f1183cc42719ea96e9c014479b51a5) deployed from workspace, but the workspace copy was **stale** (old code).
2. Ran `databricks sync` to push local changes to workspace, then redeployed.
3. During testing discovered the fault_type case mismatch -- synced + redeployed again (01f1183d885314a0b759c182e2a56ee6).

**Lesson learned:** Always sync local files to workspace before deploying with `databricks apps deploy`. The deploy command reads from the workspace path, not directly from local disk.

---

## Test Results (curl API tests)

### Q1: "Which transformers in the northern zone are running hot?"

**Result: PASS**

```
There are 3 transformers in the Northern zone running hot (temp > 60C):
1. AST-0018 (87.9C, health=29)
2. AST-0058 (82.9C, health=31)
3. AST-0034 (82.6C, health=69)
```

Matches Query A diagnostic data exactly (3 transformers above 60C).

### Q2: "Show me assets with faults but no open work order"

**Result: PASS**

```
30 assets with 3+ faults but no open SAP work order, led by:
- AST-0155 (Underground Cable, Southern): 14 faults
- AST-0140 (Overhead Line, Western): 13 faults
- AST-0035 (Overhead Line, Southern): 12 faults
... (all 30 listed)
```

### Q3: "What is the average repair cost for earth faults?"

**Result: PASS**

```
The average repair cost for assets with Earth fault faults is $15,703.68 AUD.
```

Matches Query C diagnostic data exactly (231 WOs, avg $15,703.68 AUD).

### Q4: "Which substations had the most faults last month?"

**Result: PASS**

```
Substations AST-0078 (Southern) and AST-0067 (Western) had the most faults,
with 4 faults each, in the last 30 days.
```

---

## Final Verdict

| Question | Status |
|----------|--------|
| Q1: Hot transformers in northern zone | **PASS** |
| Q2: Fault-WO gap assets | **PASS** |
| Q3: Earth fault repair cost | **PASS** |
| Q4: Substations with most faults | **PASS** |

**Overall: ALL 4 QUESTIONS PASS**
