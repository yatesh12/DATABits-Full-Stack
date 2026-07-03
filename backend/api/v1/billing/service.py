from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.billing import PlanModel, SubscriptionModel, TransactionModel, UsageModel, WebhookEventModel

settings = get_settings()


async def list_plans(session: AsyncSession) -> list[PlanModel]:
    result = await session.execute(
        select(PlanModel)
        .where(PlanModel.is_active == True)
        .order_by(PlanModel.sort_order)
    )
    return list(result.scalars().all())


async def get_plan_by_id(session: AsyncSession, plan_id: int) -> PlanModel | None:
    result = await session.execute(
        select(PlanModel).where(PlanModel.id == plan_id, PlanModel.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_subscription(
    session: AsyncSession, tenant_id: uuid.UUID
) -> SubscriptionModel | None:
    result = await session.execute(
        select(SubscriptionModel)
        .where(
            SubscriptionModel.tenant_id == tenant_id,
            SubscriptionModel.status.in_(["active", "trialing", "past_due"]),
        )
        .order_by(SubscriptionModel.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_or_update_subscription(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    plan_id: int,
    payment_method_id: str | None = None,
    coupon_code: str | None = None,
) -> SubscriptionModel:
    existing = await get_subscription(session, tenant_id)
    if existing:
        existing.plan_id = plan_id
        existing.status = "active"
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        await session.flush()
        return existing

    sub = SubscriptionModel(
        tenant_id=tenant_id,
        plan_id=plan_id,
        status="active",
        current_period_start=datetime.now(timezone.utc),
    )
    session.add(sub)
    await session.flush()
    return sub


async def cancel_subscription(
    session: AsyncSession, tenant_id: uuid.UUID
) -> SubscriptionModel | None:
    sub = await get_subscription(session, tenant_id)
    if sub is None:
        return None
    sub.status = "canceled"
    sub.canceled_at = datetime.now(timezone.utc)
    session.add(sub)
    await session.flush()
    return sub


async def list_invoices(
    session: AsyncSession, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[TransactionModel]:
    result = await session.execute(
        select(TransactionModel)
        .where(TransactionModel.tenant_id == tenant_id)
        .order_by(TransactionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_current_usage(
    session: AsyncSession, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0
) -> list[UsageModel]:
    result = await session.execute(
        select(UsageModel)
        .where(UsageModel.tenant_id == tenant_id)
        .order_by(UsageModel.date.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_stripe_payment_intent(plan: PlanModel) -> dict[str, str]:
    import stripe
    stripe.api_key = settings.STRIPE_API_KEY
    amount = int((plan.price_monthly or 0) * 100)
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency="usd",
        metadata={"plan_id": plan.id},
    )
    return {
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id,
    }


async def create_razorpay_order(plan: PlanModel) -> dict[str, Any]:
    import razorpay
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
    amount = int((plan.price_monthly or 0) * 100)
    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": f"plan_{plan.id}",
    })
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": settings.RAZORPAY_KEY_ID,
    }


async def process_stripe_webhook(payload: dict[str, Any]) -> None:
    event_type = payload.get("type", "")
    event_id = payload.get("id", "")
    # TODO: Process Stripe webhook event
    pass


async def process_razorpay_webhook(payload: dict[str, Any]) -> None:
    event_type = payload.get("event", "")
    # TODO: Process Razorpay webhook event
    pass
