"""Configuration and authentication for Databricks connectivity."""

import os
from databricks.sdk import WorkspaceClient

# Detect if running inside a Databricks App
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# Databricks profile for local development
LOCAL_PROFILE = "fe-vm-sandbox-serverless-sandbox-beyza"


def get_workspace_client() -> WorkspaceClient:
    """Get a WorkspaceClient that works both locally and in Databricks Apps."""
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    return WorkspaceClient(profile=LOCAL_PROFILE)


def get_workspace_host() -> str:
    """Get workspace host URL with https:// prefix."""
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    w = WorkspaceClient(profile=LOCAL_PROFILE)
    return w.config.host


def get_oauth_token() -> str:
    """Get OAuth token for API calls."""
    w = get_workspace_client()
    if w.config.token:
        return w.config.token
    auth_headers = w.config.authenticate()
    if auth_headers and "Authorization" in auth_headers:
        return auth_headers["Authorization"].replace("Bearer ", "")
    raise RuntimeError("Could not obtain authentication token")


def get_warehouse_id() -> str:
    """Get the SQL warehouse ID from environment or default."""
    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
    if not wh_id:
        # Fallback: discover a warehouse
        w = get_workspace_client()
        warehouses = list(w.warehouses.list())
        if warehouses:
            # Prefer serverless warehouses
            for wh in warehouses:
                if wh.enable_serverless_compute:
                    return wh.id
            return warehouses[0].id
        raise RuntimeError("No SQL warehouse available")
    return wh_id
