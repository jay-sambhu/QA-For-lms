"""
Billing & Subscription API Endpoints for JASUSS Suite (Powered by Nexus)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging

from billing.gateways import PLANS, GatewayManager
from db import SessionLocal
from models import User, Subscription, PaymentTransaction

logger = logging.getLogger("jasuss.billing")

billing_router = APIRouter(prefix="/api/v1/billing", tags=["Billing & Subscriptions"])


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID ('free', 'pro', 'enterprise')")
    gateway: str = Field(default="stripe", description="Payment Gateway ('stripe', 'lemonsqueezy', 'razorpay', 'paypal')")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@billing_router.get("/plans")
async def list_plans():
    """Retrieve all available subscription plans and supported gateways."""
    return {
        "plans": list(PLANS.values()),
        "supported_gateways": [
            {"id": "stripe", "name": "Stripe", "icon": "CreditCard", "currencies": ["USD", "EUR", "GBP"]},
            {"id": "lemonsqueezy", "name": "LemonSqueezy", "icon": "ShoppingBag", "currencies": ["USD", "EUR"]},
            {"id": "razorpay", "name": "Razorpay", "icon": "Zap", "currencies": ["INR", "USD"]},
            {"id": "paypal", "name": "PayPal", "icon": "DollarSign", "currencies": ["USD", "EUR", "GBP", "AUD"]},
        ],
    }


@billing_router.post("/checkout")
async def create_checkout(request: CheckoutRequest, current_user: Any = None):
    """
    Create a checkout session with the selected payment gateway.
    """
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan '{request.plan_id}'.")

    user_id = str(getattr(current_user, "id", "00000000-0000-0000-0000-000000000001"))
    user_email = str(getattr(current_user, "email", "user@example.com"))

    # Free plan upgrades immediately
    if request.plan_id == "free":
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.plan_tier = "free"
                db.commit()
        return {
            "status": "success",
            "message": "Switched to Community Starter (Free) plan.",
            "plan_id": "free",
        }

    try:
        adapter = GatewayManager.get_adapter(request.gateway)
        session_data = adapter.create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            plan_id=request.plan_id,
            success_url=request.success_url or "http://localhost:3000?billing=success",
            cancel_url=request.cancel_url or "http://localhost:3000?billing=cancel",
        )
        return {
            "status": "success",
            "gateway": request.gateway,
            "checkout_url": session_data.get("checkout_url"),
            "session_id": session_data.get("session_id"),
            "plan": plan,
        }
    except Exception as error:
        logger.exception("Checkout session creation failed: %s", error)
        raise HTTPException(status_code=500, detail=f"Checkout creation failed: {str(error)}")


@billing_router.get("/subscription")
async def get_user_subscription(current_user: Any = None):
    """Retrieve current subscription status and feature quotas for user."""
    user_id = str(getattr(current_user, "id", "00000000-0000-0000-0000-000000000001"))

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        active_sub = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
            .first()
        )

        current_plan_id = active_sub.plan_id if active_sub else (user.plan_tier if user else "free")
        plan_details = PLANS.get(current_plan_id, PLANS["free"])

        return {
            "user_id": user_id,
            "plan": plan_details,
            "subscription": {
                "id": active_sub.id if active_sub else None,
                "status": active_sub.status if active_sub else "active",
                "gateway": active_sub.gateway if active_sub else "none",
                "current_period_end": active_sub.current_period_end.isoformat() if active_sub and active_sub.current_period_end else None,
                "cancel_at_period_end": active_sub.cancel_at_period_end if active_sub else False,
            }
            if active_sub
            else None,
        }


@billing_router.post("/webhook/{gateway}")
async def handle_gateway_webhook(
    gateway: str,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    """
    Unified Webhook receiver for Stripe, LemonSqueezy, Razorpay, and PayPal.
    """
    try:
        adapter = GatewayManager.get_adapter(gateway)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    body_bytes = await request.body()
    signature = stripe_signature or x_signature or ""
    secret = "mock_webhook_secret"

    if not adapter.verify_webhook(body_bytes, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook cryptographic signature")

    try:
        import json
        payload_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        payload_data = {}

    normalized_event = adapter.parse_webhook_event(payload_data)
    user_id = normalized_event.get("user_id")
    plan_id = normalized_event.get("plan_id", "pro")
    status = normalized_event.get("status", "active")

    if user_id:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id, email=f"{user_id}@example.com", role="user")
                db.add(user)

            user.plan_tier = plan_id if status == "active" else "free"

            sub = Subscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=plan_id,
                status=status,
                gateway=gateway,
                customer_id=normalized_event.get("customer_id"),
                subscription_id=normalized_event.get("subscription_id"),
                created_at=datetime.now(timezone.utc),
            )
            db.add(sub)

            plan_price = PLANS.get(plan_id, {}).get("price_cents", 4900)
            tx = PaymentTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                gateway=gateway,
                transaction_id=normalized_event.get("subscription_id"),
                amount_cents=plan_price,
                currency="USD",
                status="succeeded" if status == "active" else "failed",
                plan_id=plan_id,
            )
            db.add(tx)
            db.commit()

    return {"status": "received", "gateway": gateway, "event": normalized_event}
