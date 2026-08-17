"""
Stripe payment handling.
Two jobs:
  1. create_checkout_session() — makes a Stripe-hosted payment page and returns
     its URL. We stash the store URL in the session's metadata so we can recover
     it after the customer comes back (Streamlit forgets state on redirect).
  2. verify_session() — after they return, we ask Stripe (server-side, using the
     secret key) whether that session was actually paid. Never trust the browser.

Keys live in Streamlit Secrets:
  STRIPE_SECRET_KEY = "sk_live_..."   (or sk_test_... while testing)
  APP_URL           = "https://your-app.streamlit.app"
"""

import stripe

PRICE_CENTS = 2000        # $20.00
CURRENCY = "aud"
PRODUCT_NAME = "AI Store Fix Report"


def create_checkout_session(secret_key, app_url, store_url):
    """Create a Checkout Session; return its hosted-payment URL."""
    stripe.api_key = secret_key
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": CURRENCY,
                "product_data": {"name": PRODUCT_NAME},
                "unit_amount": PRICE_CENTS,
            },
            "quantity": 1,
        }],
        metadata={"store_url": store_url},
        # Stripe swaps {CHECKOUT_SESSION_ID} for the real id on redirect back.
        success_url=f"{app_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=app_url,
    )
    return session.url


def verify_session(secret_key, session_id):
    """
    Check a returned session with Stripe.
    Returns (paid: bool, store_url: str | None).
    """
    stripe.api_key = secret_key
    session = stripe.checkout.Session.retrieve(session_id)
    paid = getattr(session, "payment_status", None) == "paid"
    meta = getattr(session, "metadata", None) or {}
    store_url = meta.get("store_url") if hasattr(meta, "get") else None
    return paid, store_url
