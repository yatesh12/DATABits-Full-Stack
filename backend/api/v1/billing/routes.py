from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.billing.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    CreateSubscriptionRequest,
    InvoiceResponse,
    MessageResponse,
    PlanResponse,
    SubscriptionResponse,
    UsageResponse,
)
from api.v1.billing.service import (
    cancel_subscription,
    create_or_update_subscription,
    create_razorpay_order,
    create_stripe_payment_intent,
    get_current_usage,
    get_plan_by_id,
    get_subscription,
    list_invoices,
    list_plans,
    process_razorpay_webhook,
    process_stripe_webhook,
)
from core.config import get_settings
from models.auth import UserModel

settings = get_settings()
router = APIRouter(tags=["billing"], prefix="/billing")


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans_endpoint(
    session: AsyncSession = Depends(get_db),
) -> list[PlanResponse]:
    plans = await list_plans(session)
    return [
        PlanResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            price_monthly=p.price_monthly,
            price_yearly=p.price_yearly,
            currency=p.currency,
            features=p.features,
            limits=p.limits,
            is_active=p.is_active,
            sort_order=p.sort_order,
        )
        for p in plans
    ]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription_endpoint(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SubscriptionResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    sub = await get_subscription(session, current_user.tenant_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription")
    plan = await get_plan_by_id(session, sub.plan_id)
    return SubscriptionResponse(
        id=sub.id,
        tenant_id=str(sub.tenant_id),
        plan_id=sub.plan_id,
        plan_name=plan.name if plan else None,
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        trial_end=sub.trial_end,
        canceled_at=sub.canceled_at,
        created_at=sub.created_at,
    )


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription_endpoint(
    body: CreateSubscriptionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SubscriptionResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    plan = await get_plan_by_id(session, body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    sub = await create_or_update_subscription(
        session, current_user.tenant_id, body.plan_id, body.payment_method_id, body.coupon_code
    )
    return SubscriptionResponse(
        id=sub.id,
        tenant_id=str(sub.tenant_id),
        plan_id=sub.plan_id,
        plan_name=plan.name,
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        trial_end=sub.trial_end,
        canceled_at=sub.canceled_at,
        created_at=sub.created_at,
    )


@router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription_endpoint(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SubscriptionResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    sub = await cancel_subscription(session, current_user.tenant_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription")
    return SubscriptionResponse(
        id=sub.id,
        tenant_id=str(sub.tenant_id),
        plan_id=sub.plan_id,
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        trial_end=sub.trial_end,
        canceled_at=sub.canceled_at,
        created_at=sub.created_at,
    )


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[InvoiceResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    invoices = await list_invoices(session, current_user.tenant_id, limit, offset)
    return [
        InvoiceResponse(
            id=inv.id,
            amount=inv.amount,
            currency=inv.currency,
            status=inv.status,
            payment_provider=inv.payment_provider,
            payment_id=inv.payment_id,
            payment_method=inv.payment_method,
            description=inv.description,
            created_at=inv.created_at,
        )
        for inv in invoices
    ]


@router.get("/usage", response_model=list[UsageResponse])
async def get_usage_endpoint(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[UsageResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    usage = await get_current_usage(session, current_user.tenant_id, limit, offset)
    return [
        UsageResponse(date=u.date, feature=u.feature, quantity=u.quantity)
        for u in usage
    ]


@router.post("/create-payment-intent", response_model=CreatePaymentIntentResponse)
async def create_payment_intent(
    body: CreatePaymentIntentRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> CreatePaymentIntentResponse:
    plan = await get_plan_by_id(session, body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = await create_stripe_payment_intent(plan)
    return CreatePaymentIntentResponse(**result)


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> CreateOrderResponse:
    plan = await get_plan_by_id(session, body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = await create_razorpay_order(plan)
    return CreateOrderResponse(**result)


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
) -> dict:
    payload = await request.json()
    await process_stripe_webhook(payload)
    return {"status": "ok"}


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
) -> dict:
    payload = await request.json()
    await process_razorpay_webhook(payload)
    return {"status": "ok"}
