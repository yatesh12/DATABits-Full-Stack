from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


AVAILABLE_INTEGRATIONS = [
    {
        "id": "slack",
        "name": "Slack",
        "description": "Receive notifications and alerts in your Slack workspace",
        "category": "communication",
        "icon_url": None,
        "docs_url": "https://api.slack.com/",
    },
    {
        "id": "jupyter",
        "name": "Jupyter",
        "description": "Export datasets directly to Jupyter notebooks",
        "category": "analytics",
        "icon_url": None,
        "docs_url": "https://jupyter.org/",
    },
    {
        "id": "tableau",
        "name": "Tableau",
        "description": "Connect Tableau to your datasets for advanced visualization",
        "category": "analytics",
        "icon_url": None,
        "docs_url": "https://help.tableau.com/",
    },
    {
        "id": "powerbi",
        "name": "Power BI",
        "description": "Integrate with Microsoft Power BI for business analytics",
        "category": "analytics",
        "icon_url": None,
        "docs_url": "https://learn.microsoft.com/en-us/power-bi/",
    },
    {
        "id": "airflow",
        "name": "Apache Airflow",
        "description": "Orchestrate data pipelines with Apache Airflow",
        "category": "orchestration",
        "icon_url": None,
        "docs_url": "https://airflow.apache.org/",
    },
]


async def list_integrations(tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    # TODO: Check tenant's connected integrations from DB
    return [
        {**integration, "is_connected": False}
        for integration in AVAILABLE_INTEGRATIONS
    ]


async def connect_integration(
    integration_id: str, credentials: dict[str, Any], config: dict[str, Any]
) -> bool:
    # TODO: Store integration credentials securely
    return True


async def disconnect_integration(integration_id: str) -> bool:
    # TODO: Remove integration connection
    return True


async def list_api_keys(
    session: AsyncSession, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    # TODO: Implement API key storage
    return []


async def create_api_key(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    raw_key = f"db_{secrets.token_urlsafe(48)}"
    key_prefix = raw_key[:12]
    key_hash = sha256(raw_key.encode()).hexdigest()

    # TODO: Persist API key
    return {
        "id": 0,
        "name": name,
        "key": raw_key,
        "key_prefix": key_prefix,
        "scopes": scopes,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    }


async def revoke_api_key(
    session: AsyncSession, key_id: int, user_id: uuid.UUID
) -> bool:
    # TODO: Implement API key revocation
    return True


async def create_webhook(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    url: str,
    events: list[str],
    secret: str | None = None,
) -> dict[str, Any]:
    webhook_secret = secret or secrets.token_hex(32)
    # TODO: Persist webhook
    return {
        "id": 0,
        "url": url,
        "events": events,
        "is_active": True,
        "secret": webhook_secret,
        "created_at": datetime.now(timezone.utc),
    }


async def list_webhooks(
    session: AsyncSession, tenant_id: uuid.UUID
) -> list[dict[str, Any]]:
    # TODO: Implement webhook listing
    return []


async def delete_webhook(
    session: AsyncSession, webhook_id: int, tenant_id: uuid.UUID
) -> bool:
    # TODO: Implement webhook deletion
    return True


async def test_webhook(url: str, secret: str | None = None) -> dict[str, Any]:
    import time

    import httpx

    start = time.monotonic()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"event": "test", "timestamp": datetime.now(timezone.utc).isoformat()},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        duration_ms = (time.monotonic() - start) * 1000
        return {
            "status_code": response.status_code,
            "body": response.text[:1000],
            "duration_ms": round(duration_ms, 2),
        }
    except Exception as e:
        duration_ms = (time.monotonic() - start) * 1000
        return {
            "status_code": 0,
            "body": str(e),
            "duration_ms": round(duration_ms, 2),
        }
