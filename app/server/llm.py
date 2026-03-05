"""Foundation Model API client for the AI chat assistant."""

import logging
from openai import OpenAI
from server.config import get_workspace_host, get_oauth_token
from server.db import execute_query

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an operational intelligence assistant for Ausnet's GroupOps team.
You have access to unified SAP and AVEVA data:
- SAP: work orders (PM/CM/Emergency), maintenance history, costs
- AVEVA: sensor readings, fault events, alarms

Assets: Transformer, Substation, Overhead Line, Underground Cable, Switchgear
Zones: Northern, Eastern, Southern, Western
Key insight: There are currently ~30 assets with 3+ fault events but no open SAP work order.

Answer concisely and include specific data when possible."""


def get_llm_client() -> OpenAI:
    """Create an OpenAI client pointing at Databricks serving endpoints."""
    host = get_workspace_host()
    token = get_oauth_token()
    return OpenAI(
        api_key=token,
        base_url=f"{host}/serving-endpoints",
    )


def build_data_context() -> str:
    """Fetch summary stats from asset_health_360 to give the LLM context."""
    try:
        summary = execute_query("""
            SELECT
                COUNT(*) AS total_assets,
                ROUND(AVG(health_score), 1) AS avg_health,
                SUM(CASE WHEN health_score < 40 THEN 1 ELSE 0 END) AS critical_count,
                SUM(CASE WHEN alarm_active = true THEN 1 ELSE 0 END) AS active_alarms,
                SUM(CASE WHEN fault_count_30d >= 3 AND open_wo_count = 0 THEN 1 ELSE 0 END) AS gap_assets
            FROM ausnet_demo.groupops.asset_health_360
        """)
        if summary:
            s = summary[0]
            return (
                f"\n\nCurrent data snapshot:\n"
                f"- Total assets: {s['total_assets']}\n"
                f"- Average health score: {s['avg_health']}\n"
                f"- Critical assets (health < 40): {s['critical_count']}\n"
                f"- Active alarms: {s['active_alarms']}\n"
                f"- Gap assets (3+ faults, no WO): {s['gap_assets']}\n"
            )
    except Exception as e:
        logger.warning(f"Could not fetch data context: {e}")
    return ""


def try_data_query(user_message: str) -> str:
    """Attempt to run a relevant SQL query based on the user's question."""
    msg_lower = user_message.lower()
    extra_context = ""

    # Extract zone and asset_type from message upfront for reuse
    zone_match = None
    for z in ["Northern", "Eastern", "Southern", "Western"]:
        if z.lower() in msg_lower:
            zone_match = z
            break

    asset_type_match = None
    for t in ["Transformer", "Substation", "Overhead Line", "Underground Cable", "Switchgear"]:
        if t.lower() in msg_lower:
            asset_type_match = t
            break

    # Extract fault type from message upfront
    # Map lowercase search terms to exact database values
    fault_type_map = {
        "overvoltage": "Overvoltage",
        "thermal": "Thermal",
        "earth fault": "Earth fault",
        "phase imbalance": "Phase imbalance",
        "loss of supply": "Loss of supply",
    }
    fault_type_match = None
    for ft_key, ft_db_value in fault_type_map.items():
        if ft_key in msg_lower:
            fault_type_match = ft_db_value
            break

    try:
        if "hot" in msg_lower or ("temp" in msg_lower and "average" not in msg_lower):
            # Q1: "Which transformers in the northern zone are running hot?"
            # Apply zone and asset_type filters if present in the question
            where_clauses = ["latest_temp_c > 60"]
            if zone_match:
                where_clauses.append(f"zone = '{zone_match}'")
            if asset_type_match:
                where_clauses.append(f"asset_type = '{asset_type_match}'")
            where_sql = " AND ".join(where_clauses)
            rows = execute_query(f"""
                SELECT asset_id, asset_type, zone, latest_temp_c, health_score, alarm_active
                FROM ausnet_demo.groupops.asset_health_360
                WHERE {where_sql}
                ORDER BY latest_temp_c DESC
                LIMIT 15
            """)
            label = "Assets running hot (temp > 60°C)"
            if zone_match and asset_type_match:
                label = f"{asset_type_match}s in {zone_match} zone running hot (temp > 60°C)"
            elif zone_match:
                label = f"Assets in {zone_match} zone running hot (temp > 60°C)"
            elif asset_type_match:
                label = f"{asset_type_match}s running hot (temp > 60°C)"
            if rows:
                extra_context = f"\n\n{label}:\n"
                for r in rows:
                    extra_context += f"- {r['asset_id']} ({r['asset_type']}, {r['zone']}): {r['latest_temp_c']}°C, health={r['health_score']}, alarm={'YES' if r['alarm_active'] else 'no'}\n"
            else:
                extra_context = f"\n\nNo assets found matching: {label}. They may all be within normal temperature range.\n"

        elif "gap" in msg_lower or ("fault" in msg_lower and "work order" in msg_lower) or "no open" in msg_lower or "no wo" in msg_lower:
            # Q2: "Show assets with faults but no open work order"
            rows = execute_query("""
                SELECT asset_id, asset_type, zone, fault_count_30d, health_score, latest_temp_c
                FROM ausnet_demo.groupops.asset_health_360
                WHERE fault_count_30d >= 3 AND open_wo_count = 0
                ORDER BY fault_count_30d DESC
            """)
            if rows:
                extra_context = f"\n\nAssets with 3+ faults but no open work order ({len(rows)} total):\n"
                for r in rows[:15]:
                    extra_context += f"- {r['asset_id']} ({r['asset_type']}, {r['zone']}): {r['fault_count_30d']} faults, health={r['health_score']}, temp={r['latest_temp_c']}°C\n"
                if len(rows) > 15:
                    extra_context += f"... and {len(rows) - 15} more\n"

        elif "cost" in msg_lower or "repair" in msg_lower or "spend" in msg_lower or "average" in msg_lower:
            # Q3: "What's the average repair cost for earth faults?" — join through fault_events if fault type mentioned
            if fault_type_match:
                rows = execute_query(f"""
                    SELECT
                        '{fault_type_match}' AS fault_type,
                        COUNT(DISTINCT w.wo_number) AS wo_count,
                        ROUND(AVG(w.cost_aud), 2) AS avg_cost_aud,
                        ROUND(SUM(w.cost_aud), 2) AS total_cost_aud
                    FROM ausnet_demo.groupops.work_orders w
                    WHERE w.asset_id IN (
                        SELECT DISTINCT asset_id
                        FROM ausnet_demo.groupops.fault_events
                        WHERE fault_type = '{fault_type_match}'
                    )
                """)
                if rows and rows[0].get('wo_count') and int(rows[0]['wo_count']) > 0:
                    r = rows[0]
                    extra_context = f"\n\nRepair cost for assets with {fault_type_match} faults:\n"
                    extra_context += f"- Work orders found: {r['wo_count']}\n"
                    extra_context += f"- Average cost: ${r['avg_cost_aud']:,.2f} AUD\n"
                    extra_context += f"- Total cost: ${r['total_cost_aud']:,.2f} AUD\n"
                else:
                    # Fallback: report fault event stats
                    fault_rows = execute_query(f"""
                        SELECT COUNT(*) AS fault_count, COUNT(DISTINCT asset_id) AS asset_count,
                               AVG(duration_mins) AS avg_duration_mins
                        FROM ausnet_demo.groupops.fault_events
                        WHERE fault_type = '{fault_type_match}'
                    """)
                    if fault_rows:
                        fr = fault_rows[0]
                        extra_context = f"\n\n{fault_type_match} fault statistics:\n"
                        extra_context += f"- Total events: {fr['fault_count']}\n"
                        extra_context += f"- Assets affected: {fr['asset_count']}\n"
                        extra_context += f"- Average fault duration: {fr['avg_duration_mins']:.0f} mins\n"
                        extra_context += f"Note: Cost data is tracked at the work order level and may be associated with multiple fault types.\n"
            else:
                rows = execute_query("""
                    SELECT
                        f.fault_type,
                        COUNT(DISTINCT w.wo_number) AS wo_count,
                        ROUND(AVG(w.cost_aud), 2) AS avg_cost_aud,
                        ROUND(SUM(w.cost_aud), 2) AS total_cost_aud
                    FROM ausnet_demo.groupops.fault_events f
                    JOIN ausnet_demo.groupops.work_orders w ON f.asset_id = w.asset_id
                    WHERE w.wo_type IN ('CM', 'Emergency')
                    GROUP BY f.fault_type
                    ORDER BY avg_cost_aud DESC
                """)
                if rows:
                    extra_context = "\n\nAverage repair cost by fault type:\n"
                    for r in rows:
                        extra_context += f"- {r['fault_type']}: avg ${r['avg_cost_aud']:,.2f} AUD ({r['wo_count']} WOs, total ${r['total_cost_aud']:,.2f})\n"

        elif (asset_type_match or "substation" in msg_lower) and ("fault" in msg_lower or "most fault" in msg_lower):
            # Q4: "Which substations had the most faults last month?" — count from fault_events
            at = asset_type_match or "Substation"
            rows = execute_query(f"""
                SELECT a.asset_id, a.zone, COUNT(f.fault_id) AS fault_count,
                       a.health_score, a.open_wo_count
                FROM ausnet_demo.groupops.fault_events f
                JOIN ausnet_demo.groupops.asset_health_360 a ON f.asset_id = a.asset_id
                WHERE a.asset_type = '{at}'
                  AND f.fault_timestamp >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
                GROUP BY a.asset_id, a.zone, a.health_score, a.open_wo_count
                ORDER BY fault_count DESC
                LIMIT 15
            """)
            if rows:
                extra_context = f"\n\n{at}s ranked by fault count (last 30 days):\n"
                for r in rows:
                    wo_flag = " ⚠️ no WO" if r['open_wo_count'] == 0 else ""
                    extra_context += f"- {r['asset_id']} ({r['zone']}): {r['fault_count']} faults, health={r['health_score']}{wo_flag}\n"

        elif asset_type_match:
            # Generic asset type query — health + sensor overview
            where = f"asset_type = '{asset_type_match}'"
            if zone_match:
                where += f" AND zone = '{zone_match}'"
            rows = execute_query(f"""
                SELECT asset_id, zone, health_score, fault_count_30d, open_wo_count,
                       latest_temp_c, latest_voltage_kv, alarm_active
                FROM ausnet_demo.groupops.asset_health_360
                WHERE {where}
                ORDER BY health_score ASC
                LIMIT 15
            """)
            if rows:
                label = f"{asset_type_match} assets"
                if zone_match:
                    label += f" in {zone_match} zone"
                extra_context = f"\n\n{label} (worst health first):\n"
                for r in rows:
                    extra_context += f"- {r['asset_id']} ({r['zone']}): health={r['health_score']}, faults={r['fault_count_30d']}, WOs={r['open_wo_count']}, temp={r['latest_temp_c']}°C, alarm={'YES' if r['alarm_active'] else 'no'}\n"

        elif zone_match:
            rows = execute_query(f"""
                SELECT asset_id, asset_type, health_score, fault_count_30d, open_wo_count,
                       latest_temp_c, alarm_active
                FROM ausnet_demo.groupops.asset_health_360
                WHERE zone = '{zone_match}'
                ORDER BY health_score ASC
                LIMIT 15
            """)
            if rows:
                extra_context = f"\n\nAssets in {zone_match} zone (worst health first):\n"
                for r in rows:
                    extra_context += f"- {r['asset_id']} ({r['asset_type']}): health={r['health_score']}, faults={r['fault_count_30d']}, temp={r['latest_temp_c']}°C, alarm={'YES' if r['alarm_active'] else 'no'}\n"

        elif "fault" in msg_lower or "event" in msg_lower:
            rows = execute_query("""
                SELECT
                    f.fault_type,
                    COUNT(*) AS fault_count,
                    COUNT(DISTINCT f.asset_id) AS affected_assets
                FROM ausnet_demo.groupops.fault_events f
                WHERE f.fault_timestamp >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
                GROUP BY f.fault_type
                ORDER BY fault_count DESC
                LIMIT 10
            """)
            if rows:
                extra_context = "\n\nFault events in last 30 days by type:\n"
                for r in rows:
                    extra_context += f"- {r['fault_type']}: {r['fault_count']} events across {r['affected_assets']} assets\n"

    except Exception as e:
        logger.warning(f"Data query for chat context failed: {e}")

    return extra_context


def chat(user_message: str, history: list[dict] | None = None) -> str:
    """Send a chat message to the LLM with data context."""
    client = get_llm_client()

    # Build context
    data_context = build_data_context()
    query_context = try_data_query(user_message)

    system_content = SYSTEM_PROMPT + data_context + query_context

    messages = [{"role": "system", "content": system_content}]

    # Add conversation history
    if history:
        for h in history[-10:]:  # Keep last 10 turns
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="databricks-meta-llama-3-3-70b-instruct",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"I'm sorry, I encountered an error processing your request. Please try again. (Error: {str(e)[:200]})"
