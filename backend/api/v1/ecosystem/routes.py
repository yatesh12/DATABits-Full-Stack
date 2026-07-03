from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.ecosystem.schemas import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    CreateWebhookRequest,
    IntegrationConnectRequest,
    IntegrationResponse,
    MessageResponse,
    WebhookResponse,
    WebhookTestResponse,
)
from api.v1.ecosystem.service import (
    connect_integration,
    create_api_key,
    create_webhook,
    delete_webhook,
    disconnect_integration,
    list_api_keys,
    list_integrations,
    list_webhooks,
    revoke_api_key,
    test_webhook,
)
from models.auth import UserModel

router = APIRouter(tags=["ecosystem"], prefix="/ecosystem")


@router.get("/integrations", response_model=list[IntegrationResponse])
async def list_integrations_endpoint(
    current_user: UserModel = Depends(get_principal),
) -> list[IntegrationResponse]:
    integrations = await list_integrations(current_user.tenant_id)
    return [IntegrationResponse(**i) for i in integrations]


@router.post("/integrations/{integration_id}/connect", response_model=MessageResponse)
async def connect_integration_endpoint(
    integration_id: str,
    body: IntegrationConnectRequest,
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    success = await connect_integration(integration_id, body.credentials, body.config)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect integration")
    return MessageResponse(message=f"Integration '{integration_id}' connected successfully")


@router.delete("/integrations/{integration_id}/disconnect", response_model=MessageResponse)
async def disconnect_integration_endpoint(
    integration_id: str,
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    success = await disconnect_integration(integration_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to disconnect integration")
    return MessageResponse(message=f"Integration '{integration_id}' disconnected")


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys_endpoint(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[ApiKeyResponse]:
    keys = await list_api_keys(session, current_user.id)
    return [ApiKeyResponse(**k) for k in keys]


@router.post("/api-keys", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key_endpoint(
    body: CreateApiKeyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> CreateApiKeyResponse:
    result = await create_api_key(
        session, current_user.id, body.name, body.scopes, body.expires_at
    )
    return CreateApiKeyResponse(**result)


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key_endpoint(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    success = await revoke_api_key(session, key_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return MessageResponse(message="API key revoked successfully")


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    body: CreateWebhookRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> WebhookResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    result = await create_webhook(
        session, current_user.tenant_id, body.url, body.events, body.secret
    )
    return WebhookResponse(**result)


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks_endpoint(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[WebhookResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    webhooks = await list_webhooks(session, current_user.tenant_id)
    return [WebhookResponse(**w) for w in webhooks]


@router.delete("/webhooks/{webhook_id}", response_model=MessageResponse)
async def delete_webhook_endpoint(
    webhook_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    success = await delete_webhook(session, webhook_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return MessageResponse(message="Webhook deleted successfully")


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook_endpoint(
    webhook_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> WebhookTestResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    webhooks = await list_webhooks(session, current_user.tenant_id)
    webhook = next((w for w in webhooks if w["id"] == webhook_id), None)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    result = await test_webhook(webhook["url"], webhook.get("secret"))
    return WebhookTestResponse(**result)
