"""API routes for the GroupOps Intelligence Hub."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.db import execute_query
from server.llm import chat

logger = logging.getLogger(__name__)

api = APIRouter(prefix="/api")


# ---------- Pydantic models ----------

class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    response: str


# ---------- Endpoints ----------

@api.get("/health-summary")
async def health_summary():
    """Asset health scorecard data grouped by zone."""
    try:
        rows = execute_query("""
            SELECT zone,
                SUM(CASE WHEN health_score >= 70 THEN 1 ELSE 0 END) AS healthy,
                SUM(CASE WHEN health_score >= 40 AND health_score < 70 THEN 1 ELSE 0 END) AS warning,
                SUM(CASE WHEN health_score < 40 THEN 1 ELSE 0 END) AS critical
            FROM ausnet_demo.groupops.asset_health_360
            GROUP BY zone ORDER BY zone
        """)
        return rows
    except Exception as e:
        logger.error(f"health-summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/active-alarms")
async def active_alarms():
    """Active alarm assets sorted by fault count."""
    try:
        rows = execute_query("""
            SELECT asset_id, asset_type, zone,
                latest_temp_c, latest_voltage_kv, latest_load_pct,
                fault_count_30d, health_score
            FROM ausnet_demo.groupops.asset_health_360
            WHERE alarm_active = true
            ORDER BY fault_count_30d DESC
            LIMIT 20
        """)
        return rows
    except Exception as e:
        logger.error(f"active-alarms failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/maintenance-queue")
async def maintenance_queue():
    """Open and in-progress work orders joined with asset health."""
    try:
        rows = execute_query("""
            SELECT w.wo_number, w.asset_id, a.asset_type, a.zone,
                w.wo_type, w.status, w.created_date, w.cost_aud, a.health_score
            FROM ausnet_demo.groupops.work_orders w
            JOIN ausnet_demo.groupops.asset_health_360 a ON w.asset_id = a.asset_id
            WHERE w.status IN ('Open', 'In Progress')
            ORDER BY a.health_score ASC
            LIMIT 50
        """)
        return rows
    except Exception as e:
        logger.error(f"maintenance-queue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/fault-wo-gap")
async def fault_wo_gap():
    """Assets with 3+ faults and no open work order -- the key business insight."""
    try:
        rows = execute_query("""
            SELECT asset_id, asset_type, zone, fault_count_30d,
                health_score, latest_temp_c, latest_voltage_kv, alarm_active
            FROM ausnet_demo.groupops.asset_health_360
            WHERE fault_count_30d >= 3 AND open_wo_count = 0
            ORDER BY fault_count_30d DESC
        """)
        return rows
    except Exception as e:
        logger.error(f"fault-wo-gap failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """AI chat assistant with data context."""
    try:
        response = chat(request.message, request.history)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
