import pytest
from billing.gateways import (
    PLANS,
    GatewayManager,
    StripeAdapter,
    LemonSqueezyAdapter,
    RazorpayAdapter,
    PayPalAdapter,
)

def test_plans_structure():
    assert "free" in PLANS
    assert "pro" in PLANS
    assert "enterprise" in PLANS
    assert PLANS["free"]["price_cents"] == 0
    assert PLANS["pro"]["price_cents"] == 4900
    assert PLANS["enterprise"]["price_cents"] == 19900

def test_supported_gateways():
    gateways = GatewayManager.list_supported_gateways()
    assert "stripe" in gateways
    assert "lemonsqueezy" in gateways
    assert "razorpay" in gateways
    assert "paypal" in gateways

def test_stripe_adapter_checkout():
    adapter = GatewayManager.get_adapter("stripe")
    assert isinstance(adapter, StripeAdapter)
    res = adapter.create_checkout_session(
        user_id="user-123",
        user_email="test@example.com",
        plan_id="pro",
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
    )
    assert res["gateway"] == "stripe"
    assert "checkout_url" in res
    assert res["amount_cents"] == 4900

def test_lemonsqueezy_adapter_checkout():
    adapter = GatewayManager.get_adapter("lemonsqueezy")
    assert isinstance(adapter, LemonSqueezyAdapter)
    res = adapter.create_checkout_session(
        user_id="user-123",
        user_email="test@example.com",
        plan_id="enterprise",
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
    )
    assert res["gateway"] == "lemonsqueezy"
    assert "checkout_url" in res
    assert res["amount_cents"] == 19900

def test_razorpay_adapter_checkout():
    adapter = GatewayManager.get_adapter("razorpay")
    assert isinstance(adapter, RazorpayAdapter)
    res = adapter.create_checkout_session(
        user_id="user-123",
        user_email="test@example.com",
        plan_id="pro",
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
    )
    assert res["gateway"] == "razorpay"
    assert "order_" in res["session_id"]

def test_paypal_adapter_checkout():
    adapter = GatewayManager.get_adapter("paypal")
    assert isinstance(adapter, PayPalAdapter)
    res = adapter.create_checkout_session(
        user_id="user-123",
        user_email="test@example.com",
        plan_id="pro",
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
    )
    assert res["gateway"] == "paypal"
    assert "PAYPAL-ORDER-" in res["session_id"]

def test_unsupported_gateway_raises():
    with pytest.raises(ValueError, match="Unsupported payment gateway"):
        GatewayManager.get_adapter("unknown_gateway")
