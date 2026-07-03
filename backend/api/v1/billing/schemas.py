from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    price_monthly: float | None
    price_yearly: float | None
    currency: str
    features: dict[str, Any] | None
    limits: dict[str, Any] | None
    is_active: bool
    sort_order: int


class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: str
    plan_id: int
    plan_name: str | None = None
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_end: datetime | None
    canceled_at: datetime | None
    created_at: datetime


class CreateSubscriptionRequest(BaseModel):
    plan_id: int
    payment_method_id: str | None = None
    coupon_code: str | None = None


class InvoiceResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    payment_provider: str | None
    payment_id: str | None
    payment_method: str | None
    description: str | None
    created_at: datetime


class UsageResponse(BaseModel):
    date: datetime
    feature: str
    quantity: int


class CreatePaymentIntentRequest(BaseModel):
    plan_id: int
    currency: str = "usd"


class CreatePaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


class CreateOrderRequest(BaseModel):
    plan_id: int
    currency: str = "INR"


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class MessageResponse(BaseModel):
    message: str
