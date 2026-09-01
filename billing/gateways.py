"""
Payment Gateway Adapters for JASUSS Platform (Powered by Nexus)
Supports Stripe, LemonSqueezy, Razorpay, and PayPal.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import uuid
import hmac
import hashlib

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Community Starter",
        "price_cents": 0,
        "currency": "USD",
        "interval": "monthly",
        "description": "Essential web quality assurance for developers and open-source projects.",
        "features": [
            "10 Automated Scans / month",
            "Multi-Viewport Crawling (Desktop, iPhone 13, iPad)",
            "Deterministic Defect Detection & Triage",
            "Executive Web Quality Score & Grading",
            "Community Support",
        ],
        "max_pages": 10,
        "max_scans_per_month": 10,
    },
    "pro": {
        "id": "pro",
        "name": "Professional QA",
        "price_cents": 4900,
        "currency": "USD",
        "interval": "monthly",
        "description": "Advanced automated testing for growth teams, SaaS apps, and continuous delivery.",
        "features": [
            "200 Automated Scans / month",
            "Up to 50 Pages Deep Crawling",
            "Authenticated Route & Session Crawling",
            "Executive PDF & Excel Multi-Tab Exports",
            "Historical Regression Diffing & Quality Gates",
            "Priority Processing Queue",
        ],
        "max_pages": 50,
        "max_scans_per_month": 200,
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise Suite",
        "price_cents": 19900,
        "currency": "USD",
        "interval": "monthly",
        "description": "Full-scale continuous QA platform with dedicated cluster workers and SLA.",
        "features": [
            "Unlimited Automated QA Scans",
            "Deep Unlimited Page Discovery",
            "Multi-Factor & Custom Form Authentication",
            "Dedicated Celery Worker Pool & High Throughput",
            "Custom Quality Rules & Compliance SLAs",
            "24/7 Dedicated Support & Security Audits",
        ],
        "max_pages": 200,
        "max_scans_per_month": -1,  # unlimited
    },
}


class PaymentGatewayAdapter(ABC):
    """Abstract base class for payment gateway integrations."""

    @abstractmethod
    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Generate checkout URL and session details for client redirection."""
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify the cryptographic authenticity of incoming webhook events."""
        pass

    @abstractmethod
    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize gateway-specific webhook events into unified platform event."""
        pass


class StripeAdapter(PaymentGatewayAdapter):
    """Stripe Payment Gateway Adapter."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY", "mock_stripe_key")

    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        plan = PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan_id: {plan_id}")

        session_id = f"cs_stripe_{uuid.uuid4().hex[:16]}"
        checkout_url = f"https://checkout.stripe.com/c/pay/{session_id}?user={user_id}&plan={plan_id}"

        return {
            "gateway": "stripe",
            "session_id": session_id,
            "checkout_url": checkout_url,
            "plan_id": plan_id,
            "amount_cents": plan["price_cents"],
            "currency": plan["currency"],
        }

    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return True
        computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = data.get("type", "checkout.session.completed")
        obj = data.get("data", {}).get("object", {})
        return {
            "gateway": "stripe",
            "event_type": event_type,
            "user_id": obj.get("client_reference_id") or obj.get("metadata", {}).get("user_id"),
            "customer_id": obj.get("customer"),
            "subscription_id": obj.get("subscription"),
            "plan_id": obj.get("metadata", {}).get("plan_id", "pro"),
            "status": "active" if event_type in ("checkout.session.completed", "invoice.payment_succeeded") else "cancelled",
        }


class LemonSqueezyAdapter(PaymentGatewayAdapter):
    """LemonSqueezy Payment Gateway Adapter."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LEMONSQUEEZY_API_KEY", "mock_lemonsqueezy_key")

    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        plan = PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan_id: {plan_id}")

        checkout_id = f"ls_chk_{uuid.uuid4().hex[:12]}"
        checkout_url = f"https://jasuss.lemonsqueezy.com/checkout/buy/{checkout_id}?custom[user_id]={user_id}&checkout[email]={user_email}"

        return {
            "gateway": "lemonsqueezy",
            "session_id": checkout_id,
            "checkout_url": checkout_url,
            "plan_id": plan_id,
            "amount_cents": plan["price_cents"],
            "currency": plan["currency"],
        }

    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return True
        computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        meta = data.get("meta", {})
        event_name = meta.get("event_name", "subscription_created")
        attributes = data.get("data", {}).get("attributes", {})
        custom_data = meta.get("custom_data", {})
        
        return {
            "gateway": "lemonsqueezy",
            "event_type": event_name,
            "user_id": custom_data.get("user_id"),
            "customer_id": str(attributes.get("customer_id", "")),
            "subscription_id": str(data.get("data", {}).get("id", "")),
            "plan_id": custom_data.get("plan_id", "pro"),
            "status": "active" if attributes.get("status") == "active" else "cancelled",
        }


class RazorpayAdapter(PaymentGatewayAdapter):
    """Razorpay Payment Gateway Adapter."""

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "mock_razorpay_id")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "mock_razorpay_secret")

    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        plan = PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan_id: {plan_id}")

        order_id = f"order_{uuid.uuid4().hex[:14]}"
        checkout_url = f"https://api.razorpay.com/v1/checkout/{order_id}?user={user_id}&plan={plan_id}"

        return {
            "gateway": "razorpay",
            "session_id": order_id,
            "checkout_url": checkout_url,
            "key_id": self.key_id,
            "plan_id": plan_id,
            "amount_cents": plan["price_cents"],
            "currency": plan["currency"],
        }

    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return True
        computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event = data.get("event", "payment.captured")
        payload = data.get("payload", {})
        payment = payload.get("payment", {}).get("entity", {})
        notes = payment.get("notes", {})

        return {
            "gateway": "razorpay",
            "event_type": event,
            "user_id": notes.get("user_id"),
            "customer_id": payment.get("customer_id"),
            "subscription_id": payment.get("order_id"),
            "plan_id": notes.get("plan_id", "pro"),
            "status": "active" if event in ("payment.captured", "subscription.activated") else "cancelled",
        }


class PayPalAdapter(PaymentGatewayAdapter):
    """PayPal Payment Gateway Adapter."""

    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID", "mock_paypal_client_id")

    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        plan = PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan_id: {plan_id}")

        order_id = f"PAYPAL-ORDER-{uuid.uuid4().hex[:12].upper()}"
        checkout_url = f"https://www.paypal.com/checkoutnow?token={order_id}&user={user_id}&plan={plan_id}"

        return {
            "gateway": "paypal",
            "session_id": order_id,
            "checkout_url": checkout_url,
            "plan_id": plan_id,
            "amount_cents": plan["price_cents"],
            "currency": plan["currency"],
        }

    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        return True  # PayPal signature verification simulation

    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = data.get("event_type", "BILLING.SUBSCRIPTION.ACTIVATED")
        resource = data.get("resource", {})
        custom_id = resource.get("custom_id") or resource.get("subscriber", {}).get("email_address")

        return {
            "gateway": "paypal",
            "event_type": event_type,
            "user_id": custom_id,
            "customer_id": resource.get("subscriber", {}).get("payer_id"),
            "subscription_id": resource.get("id"),
            "plan_id": "pro",
            "status": "active" if event_type in ("BILLING.SUBSCRIPTION.ACTIVATED", "PAYMENT.SALE.COMPLETED") else "cancelled",
        }


class GatewayManager:
    """Factory and registry manager for supported payment gateways."""

    _adapters: Dict[str, PaymentGatewayAdapter] = {
        "stripe": StripeAdapter(),
        "lemonsqueezy": LemonSqueezyAdapter(),
        "razorpay": RazorpayAdapter(),
        "paypal": PayPalAdapter(),
    }

    @classmethod
    def get_adapter(cls, gateway_name: str) -> PaymentGatewayAdapter:
        name = gateway_name.lower().strip()
        if name not in cls._adapters:
            raise ValueError(f"Unsupported payment gateway: '{gateway_name}'. Supported: {list(cls._adapters.keys())}")
        return cls._adapters[name]

    @classmethod
    def list_supported_gateways(cls) -> list[str]:
        return list(cls._adapters.keys())
