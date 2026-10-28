"""
Billing & Subscription API Endpoints for JASUSS Suite (Powered by Nexus)
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from billing.gateways import PLANS, GatewayManager
from config import settings
from db import SessionLocal
from models import User, Subscription, PaymentTransaction
from api.deps import require_user
from api.rate_limiter import make_rate_limiter
from api.utils import iso_utc

logger = logging.getLogger("jasuss.billing")

billing_router = APIRouter(prefix="/api/v1/billing", tags=["Billing & Subscriptions"])

rate_limit_billing = make_rate_limiter(settings.RATE_LIMIT_STANDARD, "user", "billing")
rate_limit_webhook = make_rate_limiter(300, "ip", "webhook")

STRIPE_TOLERANCE_SECONDS = 300


def _webhook_secret(gateway: str) -> str:
    """Per-gateway webhook signing secret, e.g. STRIPE_WEBHOOK_SECRET."""
    import os
    return (os.environ.get(f"{gateway.upper()}_WEBHOOK_SECRET") or "").strip()


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID ('free', 'pro', 'enterprise')", max_length=40)
    gateway: str = Field(default="stripe", description="Payment Gateway ('stripe', 'lemonsqueezy', 'razorpay', 'paypal')", max_length=40)
    success_url: Optional[str] = Field(default=None, max_length=2048)
    cancel_url: Optional[str] = Field(default=None, max_length=2048)


@billing_router.get("/plans")
def list_plans():
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


@billing_router.post("/checkout", dependencies=[Depends(rate_limit_billing)])
def create_checkout(request: CheckoutRequest, current_user: Any = Depends(require_user)):
    """Create a checkout session with the selected payment gateway."""
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan '{request.plan_id}'.")

    user_id = str(getattr(current_user, "id", current_user))
    user_email = str(getattr(current_user, "email", "") or "")

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
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        logger.exception("Checkout session creation failed: %s", error)
        raise HTTPException(status_code=502, detail="Checkout creation failed; please try again")


@billing_router.get("/subscription", dependencies=[Depends(rate_limit_billing)])
def get_user_subscription(current_user: Any = Depends(require_user)):
    """Retrieve current subscription status and feature quotas for user."""
    user_id = str(getattr(current_user, "id", current_user))

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        active_sub = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.updated_at.desc().nullslast(), Subscription.created_at.desc())
            .first()
        )

        current_plan_id = active_sub.plan_id if active_sub else (user.plan_tier if user else "free")
        plan_details = PLANS.get(current_plan_id, PLANS["free"])

        return {
            "user_id": user_id,
            "plan": plan_details,
            "subscription": {
                "id": active_sub.id,
                "status": active_sub.status,
                "gateway": active_sub.gateway,
                "current_period_end": iso_utc(active_sub.current_period_end),
                "cancel_at_period_end": bool(active_sub.cancel_at_period_end),
            }
            if active_sub
            else None,
        }


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

def _verify_stripe_signature(body: bytes, header: str, secret: str) -> bool:
    """Stripe signs ``{t}.{body}`` and sends ``t=<ts>,v1=<hex>[,v1=...]``."""
    if not header or not secret:
        return False
    parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
    timestamp = parts.get("t")
    signatures = [v.split("=", 1)[1] for v in header.split(",") if v.startswith("v1=")]
    if not timestamp or not signatures:
        return False
    try:
        if abs(time.time() - int(timestamp)) > STRIPE_TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False
    expected = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


_PAYMENT_EVENTS = {
    "stripe": {"checkout.session.completed", "invoice.payment_succeeded", "invoice.paid"},
    "lemonsqueezy": {"order_created", "subscription_payment_success"},
    "razorpay": {"payment.captured"},
    "paypal": {"PAYMENT.SALE.COMPLETED", "PAYMENT.CAPTURE.COMPLETED"},
}


def _epoch_to_dt(value) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc) if value else None
    except (TypeError, ValueError, OSError):
        return None


def _iso_to_dt(value) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_details(gateway: str, body: bytes, data: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Gateway event id, amount and period details taken from the delivery
    itself (never fabricated from the plan table)."""
    details: Dict[str, Any] = {
        "event_id": None, "amount_cents": None, "currency": None,
        "transaction_id": None, "current_period_end": None, "cancel_at_period_end": None,
    }
    if gateway == "stripe":
        obj = (data.get("data") or {}).get("object") or {}
        details["event_id"] = data.get("id")
        details["amount_cents"] = obj.get("amount_total") if obj.get("amount_total") is not None else obj.get("amount_paid")
        details["currency"] = obj.get("currency")
        details["transaction_id"] = obj.get("payment_intent") or obj.get("id")
        details["current_period_end"] = _epoch_to_dt(obj.get("current_period_end"))
        if "cancel_at_period_end" in obj:
            details["cancel_at_period_end"] = bool(obj.get("cancel_at_period_end"))
    elif gateway == "lemonsqueezy":
        meta = data.get("meta") or {}
        attributes = (data.get("data") or {}).get("attributes") or {}
        details["event_id"] = meta.get("webhook_id")
        details["amount_cents"] = attributes.get("total") if attributes.get("total") is not None else attributes.get("subtotal")
        details["currency"] = attributes.get("currency")
        details["transaction_id"] = attributes.get("order_id") or (data.get("data") or {}).get("id")
        details["current_period_end"] = _iso_to_dt(attributes.get("renews_at") or attributes.get("ends_at"))
        if "cancelled" in attributes:
            details["cancel_at_period_end"] = bool(attributes.get("cancelled"))
    elif gateway == "razorpay":
        payment = ((data.get("payload") or {}).get("payment") or {}).get("entity") or {}
        details["event_id"] = payment.get("id")
        details["amount_cents"] = payment.get("amount")
        details["currency"] = payment.get("currency")
        details["transaction_id"] = payment.get("id")
    elif gateway == "paypal":
        resource = data.get("resource") or {}
        amount = resource.get("amount") or {}
        details["event_id"] = data.get("id")
        value = amount.get("total") or amount.get("value")
        try:
            details["amount_cents"] = int(round(float(value) * 100)) if value is not None else None
        except (TypeError, ValueError):
            details["amount_cents"] = None
        details["currency"] = amount.get("currency") or amount.get("currency_code")
        details["transaction_id"] = resource.get("id")
    if not details["event_id"]:
        # Exact replays of a delivery without an id are still de-duplicated
        details["event_id"] = f"{gateway}:{hashlib.sha256(body).hexdigest()}"
    return details


def _apply_webhook_event(gateway: str, body: bytes, payload_data: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
    user_id = normalized.get("user_id")
    plan_id = normalized.get("plan_id") or "pro"
    status = normalized.get("status") or "active"
    event_type = normalized.get("event_type") or ""
    subscription_id = normalized.get("subscription_id") or None
    details = _event_details(gateway, body, payload_data, normalized)
    event_id = details["event_id"]

    if not user_id:
        return {"applied": False, "reason": "no user id in event"}

    with SessionLocal() as db:
        if db.query(PaymentTransaction.id).filter(PaymentTransaction.event_id == event_id).first():
            return {"applied": False, "reason": "duplicate event", "event_id": event_id}

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("Webhook %s for unknown user %s ignored", event_type, user_id)
            return {"applied": False, "reason": "unknown user"}

        now = datetime.now(timezone.utc)
        sub = None
        if subscription_id:
            sub = (
                db.query(Subscription)
                .filter(Subscription.gateway == gateway, Subscription.subscription_id == subscription_id)
                .first()
            )
        if sub is None:
            sub = Subscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                gateway=gateway,
                subscription_id=subscription_id,
                created_at=now,
            )
            db.add(sub)
        sub.user_id = user_id
        sub.plan_id = plan_id
        sub.status = status
        sub.customer_id = normalized.get("customer_id") or sub.customer_id
        if details["current_period_end"] is not None:
            sub.current_period_end = details["current_period_end"]
        if details["cancel_at_period_end"] is not None:
            sub.cancel_at_period_end = details["cancel_at_period_end"]
        sub.updated_at = now

        if status == "active":
            user.plan_tier = plan_id
        else:
            other_active = (
                db.query(Subscription.plan_id)
                .filter(Subscription.user_id == user_id, Subscription.status == "active", Subscription.id != sub.id)
                .order_by(Subscription.created_at.desc())
                .first()
            )
            user.plan_tier = other_active[0] if other_active else "free"

        recorded_tx = False
        if event_type in _PAYMENT_EVENTS.get(gateway, set()) or details["amount_cents"] is not None:
            db.add(PaymentTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                gateway=gateway,
                transaction_id=details["transaction_id"] or subscription_id,
                event_id=event_id,
                amount_cents=int(details["amount_cents"] or 0),
                currency=str(details["currency"] or PLANS.get(plan_id, {}).get("currency") or "USD").upper(),
                status="succeeded" if status == "active" else "failed",
                plan_id=plan_id,
            ))
            recorded_tx = True
        else:
            # Non-payment events are still recorded (amount 0) so a replay is
            # recognised; they do not count as revenue.
            db.add(PaymentTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                gateway=gateway,
                transaction_id=None,
                event_id=event_id,
                amount_cents=0,
                currency="USD",
                status="pending",
                plan_id=plan_id,
            ))
        db.commit()
        return {"applied": True, "event_id": event_id, "plan_tier": user.plan_tier, "payment_recorded": recorded_tx}


@billing_router.post("/webhook/{gateway}", dependencies=[Depends(rate_limit_webhook)])
async def handle_gateway_webhook(
    gateway: str,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
):
    """Unified, idempotent webhook receiver for Stripe, LemonSqueezy, Razorpay and PayPal."""
    gateway = gateway.lower().strip()
    try:
        adapter = GatewayManager.get_adapter(gateway)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    body_bytes = await request.body()
    secret = _webhook_secret(gateway)
    if not secret:
        logger.error("Webhook for gateway %s rejected: %s_WEBHOOK_SECRET is not configured", gateway, gateway.upper())
        raise HTTPException(status_code=503, detail="Webhook verification is not configured for this gateway")

    if gateway == "stripe":
        verified = _verify_stripe_signature(body_bytes, stripe_signature or "", secret)
    elif gateway == "razorpay":
        verified = adapter.verify_webhook(body_bytes, razorpay_signature or x_signature or "", secret)
    else:
        verified = adapter.verify_webhook(body_bytes, x_signature or "", secret)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid webhook cryptographic signature")

    try:
        payload_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        payload_data = {}
    if not isinstance(payload_data, dict):
        payload_data = {}

    normalized_event = adapter.parse_webhook_event(payload_data)
    result = await run_in_threadpool(_apply_webhook_event, gateway, body_bytes, payload_data, normalized_event)
    return {"status": "received", "gateway": gateway, "event": normalized_event, **result}
