"""
Unit tests for Payment Webhook Authentication and Signature Verification.
"""
import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

SAMPLE_STRIPE_PAYLOAD = {
    "id": "evt_test_123",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_123",
            "client_reference_id": "00000000-0000-0000-0000-000000000001",
            "customer": "cus_123",
            "subscription": "sub_123",
            "metadata": {"plan_id": "pro"}
        }
    }
}

SAMPLE_LEMONSQUEEZY_PAYLOAD = {
    "meta": {
        "event_name": "subscription_created",
        "custom_data": {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "plan_id": "pro"
        }
    },
    "data": {
        "id": "ls_sub_123",
        "attributes": {
            "customer_id": 9999,
            "status": "active"
        }
    }
}


def test_webhook_missing_secret_returns_503(monkeypatch):
    """If a gateway's webhook secret is not configured, it must return 503 (fail closed)."""
    # Clear any environment variables for webhook secrets
    for gw_key in ["STRIPE_WEBHOOK_SECRET", "LEMONSQUEEZY_WEBHOOK_SECRET", "RAZORPAY_WEBHOOK_SECRET", "PAYPAL_WEBHOOK_SECRET", "PAYPAL_WEBHOOK_ID"]:
        monkeypatch.delenv(gw_key, raising=False)

    for gateway in ["stripe", "lemonsqueezy", "razorpay", "paypal"]:
        res = client.post(
            f"/api/v1/billing/webhook/{gateway}",
            json={"test": "data"},
            headers={"X-Signature": "dummy_sig", "Stripe-Signature": "dummy_sig"}
        )
        assert res.status_code == 503, f"Expected 503 for unconfigured {gateway}, got {res.status_code}"
        assert "not configured" in res.json().get("detail", "")


def test_webhook_missing_or_bad_signature_returns_400(monkeypatch):
    """When a secret is configured but the signature is missing or invalid, return 400."""
    secret = "whsec_test_stripe_secret_12345"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_STRIPE_PAYLOAD).encode("utf-8")

    # 1. Missing signature header
    res_no_sig = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={"Content-Type": "application/json"}
    )
    assert res_no_sig.status_code == 400
    assert "signature" in res_no_sig.json().get("detail", "").lower()

    # 2. Tampered / invalid signature header
    res_bad_sig = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": "invalid_hex_signature_deadbeef"
        }
    )
    assert res_bad_sig.status_code == 400
    assert "Invalid webhook cryptographic signature" in res_bad_sig.json().get("detail", "")


def test_webhook_valid_signature_processed_successfully(monkeypatch):
    """When a valid HMAC signature is sent with raw body, return 200 and process event."""
    secret = "whsec_valid_secret_key"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_STRIPE_PAYLOAD).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": valid_sig
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "received"
    assert data.get("gateway") == "stripe"
    assert data.get("event", {}).get("event_type") == "checkout.session.completed"


def test_lemonsqueezy_webhook_valid_signature(monkeypatch):
    """Verify LemonSqueezy HMAC-SHA256 signature verification."""
    secret = "lemonsqueezy_secret_test"
    monkeypatch.setenv("LEMONSQUEEZY_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_LEMONSQUEEZY_PAYLOAD).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/v1/billing/webhook/lemonsqueezy",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Signature": valid_sig
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "received"
    assert data.get("gateway") == "lemonsqueezy"
