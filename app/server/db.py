"""Databricks SQL connector for querying Unity Catalog tables."""

import logging
from databricks.sql import connect
from databricks.sql.client import Connection
from server.config import get_workspace_host, get_oauth_token, get_warehouse_id

logger = logging.getLogger(__name__)

_connection: Connection | None = None


def get_connection() -> Connection:
    """Get or create a Databricks SQL connection."""
    global _connection
    if _connection is None:
        host = get_workspace_host().replace("https://", "").replace("http://", "")
        token = get_oauth_token()
        warehouse_id = get_warehouse_id()
        logger.info(f"Connecting to Databricks SQL: host={host}, warehouse={warehouse_id}")
        _connection = connect(
            server_hostname=host,
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            access_token=token,
        )
    return _connection


def execute_query(sql: str) -> list[dict]:
    """Execute a SQL query and return results as list of dicts."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"SQL query failed: {e}")
        # Reset connection on failure so next call creates a fresh one
        reset_connection()
        raise


def reset_connection():
    """Close and reset the SQL connection."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None
