"""
Unit tests for Payment Webhook Authentication and Signature Verification.
"""
import hmac
import hashlib
import json
import time
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

SAMPLE_RAZORPAY_PAYLOAD = {
    "event": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_123",
                "customer_id": "cust_123",
                "order_id": "order_123",
                "notes": {
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "plan_id": "pro"
                }
            }
        }
    }
}


def test_missing_secret_returns_503_for_gateways(monkeypatch):
    """If a gateway's webhook secret is not configured, it must return 503 (fail closed)."""
    for gw_key in ["STRIPE_WEBHOOK_SECRET", "LEMONSQUEEZY_WEBHOOK_SECRET", "RAZORPAY_WEBHOOK_SECRET"]:
        monkeypatch.delenv(gw_key, raising=False)

    for gateway in ["stripe", "lemonsqueezy", "razorpay"]:
        res = client.post(
            f"/api/v1/billing/webhook/{gateway}",
            json={"test": "data"},
            headers={"X-Signature": "dummy_sig", "Stripe-Signature": "t=123,v1=dummy_sig"}
        )
        assert res.status_code == 503, f"Expected 503 for unconfigured {gateway}, got {res.status_code}"
        assert "not configured" in res.json().get("detail", "")


def test_paypal_webhook_returns_501_not_implemented():
    """PayPal webhook verification returns 501 Not Implemented and processes nothing."""
    res = client.post(
        "/api/v1/billing/webhook/paypal",
        json={"test": "data"},
        headers={"Paypal-Transmission-Sig": "dummy_sig"}
    )
    assert res.status_code == 501
    assert "not implemented" in res.json().get("detail", "").lower()


def test_stripe_webhook_fresh_timestamp_valid_signature_processed(monkeypatch):
    """Stripe webhook with fresh timestamp and valid v1 signature is processed (200)."""
    secret = "whsec_stripe_test_secret_123"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_STRIPE_PAYLOAD).encode("utf-8")
    t = int(time.time())
    signed_payload = f"{t}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    # 1. Single valid v1
    res = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={t},v1={sig}"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "received"
    assert data.get("gateway") == "stripe"
    assert data.get("event", {}).get("event_type") == "checkout.session.completed"

    # 2. Multiple v1 signatures (rolling secret support)
    res_multi = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={t},v1=old_or_invalid_sig_123,v1={sig}"
        }
    )
    assert res_multi.status_code == 200


def test_stripe_webhook_stale_timestamp_returns_400(monkeypatch):
    """Stripe webhook with timestamp older than 300 seconds or too far in the future returns 400."""
    secret = "whsec_stripe_test_secret_123"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_STRIPE_PAYLOAD).encode("utf-8")

    # 1. Stale timestamp (400 seconds in the past)
    stale_t = int(time.time()) - 400
    signed_stale = f"{stale_t}.".encode("utf-8") + payload_bytes
    stale_sig = hmac.new(secret.encode("utf-8"), signed_stale, hashlib.sha256).hexdigest()

    res_stale = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={stale_t},v1={stale_sig}"
        }
    )
    assert res_stale.status_code == 400
    assert "Invalid webhook cryptographic signature" in res_stale.json().get("detail", "")

    # 2. Future timestamp (400 seconds in the future)
    future_t = int(time.time()) + 400
    signed_future = f"{future_t}.".encode("utf-8") + payload_bytes
    future_sig = hmac.new(secret.encode("utf-8"), signed_future, hashlib.sha256).hexdigest()

    res_future = client.post(
        "/api/v1/billing/webhook/stripe",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={future_t},v1={future_sig}"
        }
    )
    assert res_future.status_code == 400


def test_stripe_webhook_malformed_header_returns_400(monkeypatch):
    """Stripe webhook with missing t=, missing v1=, or non-numeric t returns 400."""
    secret = "whsec_stripe_test_secret_123"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_STRIPE_PAYLOAD).encode("utf-8")
    valid_t = int(time.time())

    malformed_headers = [
        f"t={valid_t}",  # missing v1=
        "v1=abcdef123456",  # missing t=
        "plain_text_header_without_equals",
        f"t=not_a_number,v1=abcdef123456",
        "",  # empty
    ]

    for header_val in malformed_headers:
        res = client.post(
            "/api/v1/billing/webhook/stripe",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": header_val
            }
        )
        assert res.status_code == 400, f"Expected 400 for malformed header '{header_val}', got {res.status_code}"


def test_non_ascii_header_returns_400_never_500(monkeypatch):
    """Adapters must compare bytes so non-ASCII signature headers return 400 and NEVER 500."""
    from billing.gateways import GatewayManager

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "stripe_test_secret")
    monkeypatch.setenv("LEMONSQUEEZY_WEBHOOK_SECRET", "ls_test_secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "rzp_test_secret")

    # 1. Direct adapter checks with non-ASCII strings
    stripe_adapter = GatewayManager.get_adapter("stripe")
    ls_adapter = GatewayManager.get_adapter("lemonsqueezy")
    rzp_adapter = GatewayManager.get_adapter("razorpay")

    assert stripe_adapter.verify_webhook(b"payload", "t=12345,v1=\xc3\xb1\xc3\xa1", "secret") is False
    assert ls_adapter.verify_webhook(b"payload", "non_ascii_\xc3\xb1\xc3\xa1", "secret") is False
    assert rzp_adapter.verify_webhook(b"payload", "non_ascii_\xc3\xb1\xc3\xa1", "secret") is False

    # 2. HTTP endpoint checks with raw byte headers
    res_stripe = client.post(
        "/api/v1/billing/webhook/stripe",
        content=b'{"test": "data"}',
        headers=[(b"Content-Type", b"application/json"), (b"Stripe-Signature", b"t=12345,v1=\xc3\xb1\xc3\xa1")]
    )
    assert res_stripe.status_code == 400
    assert "Invalid webhook cryptographic signature" in res_stripe.json().get("detail", "")

    res_ls = client.post(
        "/api/v1/billing/webhook/lemonsqueezy",
        content=b'{"test": "data"}',
        headers=[(b"Content-Type", b"application/json"), (b"X-Signature", b"\xc3\xb1\xc3\xa1")]
    )
    assert res_ls.status_code == 400

    res_rzp = client.post(
        "/api/v1/billing/webhook/razorpay",
        content=b'{"test": "data"}',
        headers=[(b"Content-Type", b"application/json"), (b"X-Razorpay-Signature", b"\xc3\xb1\xc3\xa1")]
    )
    assert res_rzp.status_code == 400


def test_lemonsqueezy_webhook_valid_signature(monkeypatch):
    """Verify LemonSqueezy HMAC-SHA256 signature verification and byte comparison."""
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


def test_razorpay_webhook_valid_signature(monkeypatch):
    """Verify Razorpay HMAC-SHA256 signature verification."""
    secret = "razorpay_secret_test"
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_RAZORPAY_PAYLOAD).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/v1/billing/webhook/razorpay",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": valid_sig
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "received"
    assert data.get("gateway") == "razorpay"


def test_webhook_route_aliases(monkeypatch):
    """Verify alias paths (/webhook/{gw}, /billing/webhooks/{gw}) route correctly."""
    secret = "test_alias_secret"
    monkeypatch.setenv("LEMONSQUEEZY_WEBHOOK_SECRET", secret)

    payload_bytes = json.dumps(SAMPLE_LEMONSQUEEZY_PAYLOAD).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    for path in [
        "/webhook/lemonsqueezy",
        "/billing/webhooks/lemonsqueezy",
        "/api/v1/billing/webhooks/lemonsqueezy",
    ]:
        res = client.post(
            path,
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Signature": valid_sig
            }
        )
        assert res.status_code == 200, f"Path {path} failed with {res.status_code}"
