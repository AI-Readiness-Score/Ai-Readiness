"""
AI-Readiness Scorer — Streamlit app.
Free score for any Shopify store; $20 Stripe Checkout unlocks an AI-written,
personalised fix report that appears automatically when the buyer returns.
"""

import streamlit as st
import requests
from scorer import score_store
from fix_report import generate_fix_report
from payments import create_checkout_session, verify_session

st.set_page_config(page_title="AI Readiness Score", page_icon="🛍️", layout="centered")
HEADERS = {"User-Agent": "Mozilla/5.0 (AI-Readiness-Bot)"}


def fetch(url, timeout=10):
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def analyze(store_url):
    store_url = store_url.rstrip("/")
    if not store_url.startswith("http"):
        store_url = "https://" + store_url
    home = fetch(store_url)
    if not home or home.status_code >= 400:
        return None, "Couldn't reach that store. Check the URL and try again."
    products_sample = None
    pj = fetch(store_url + "/products.json?limit=5")
    if pj and pj.status_code == 200:
        try:
            products_sample = pj.json().get("products", [])[:5]
        except Exception:
            products_sample = None
    llms = fetch(store_url + "/llms.txt")
    llms_present = bool(llms and llms.status_code == 200 and len(llms.text) > 20)
    result = score_store(home.text, "", llms_present, products_sample)
    return result, None


def render_score(result):
    score = result["score"]
    colour = "🟢" if score >= 70 else ("🟡" if score >= 40 else "🔴")
    st.markdown(f"## {colour} {score}/100")
    if score >= 70:
        st.success("Strong — AI assistants can read your store well.")
    elif score >= 40:
        st.warning("Middling — you're leaving AI visibility on the table.")
    else:
        st.error("Weak — AI assistants struggle to understand your store.")
    st.divider()
    st.subheader("What we checked")
    for c in result["breakdown"]:
        icon = {"pass": "✅", "partial": "🟡", "fail": "❌"}[c["status"]]
        st.markdown(
            f"{icon} **{c['label']}** — {c['earned']}/{c['max']}  \n"
            f"<span style='color:gray'>{c['detail']}</span>",
            unsafe_allow_html=True,
        )


st.title("🛍️ Is your store ready for AI shoppers?")

# ---------------------------------------------------------------------------
# BRANCH 1: customer is returning from Stripe (URL has ?session_id=...)
# ---------------------------------------------------------------------------
returned_session = st.query_params.get("session_id")

if returned_session:
    st.info("Thanks for your purchase! Generating your report…")
    cache_key = f"report_{returned_session}"

    if cache_key in st.session_state:
        st.markdown(st.session_state[cache_key])
    elif "STRIPE_SECRET_KEY" not in st.secrets:
        st.error("Payments aren't configured. (Owner: add STRIPE_SECRET_KEY to Secrets.)")
    else:
        try:
            paid, store_url = verify_session(st.secrets["STRIPE_SECRET_KEY"], returned_session)
        except Exception as e:
            paid, store_url = False, None
            st.error(f"Couldn't verify payment: {e}")

        if not paid:
            st.error("We couldn't confirm that payment. If you were charged, contact support.")
        elif not store_url:
            st.error("Payment confirmed but we lost the store link. Please re-run the score.")
        elif "ANTHROPIC_API_KEY" not in st.secrets:
            st.error("Report engine isn't configured. (Owner: add ANTHROPIC_API_KEY to Secrets.)")
        else:
            with st.spinner("Analysing your store and writing your fix report…"):
                result, err = analyze(store_url)
                if err:
                    st.error(err)
                else:
                    try:
                        report = generate_fix_report(
                            st.secrets["ANTHROPIC_API_KEY"],
                            store_url, result["score"], result["breakdown"],
                        )
                        st.session_state[cache_key] = report
                        st.markdown(report)
                    except Exception as e:
                        st.error(f"Something went wrong writing the report: {e}")

    if cache_key in st.session_state:
        st.download_button(
            "Download report", st.session_state[cache_key],
            file_name="ai-readiness-fixes.md",
        )
    if st.button("← Analyse another store"):
        st.query_params.clear()
        st.session_state.pop("result", None)
        st.rerun()

# ---------------------------------------------------------------------------
# BRANCH 2: normal flow — free score, then offer paid unlock
# ---------------------------------------------------------------------------
else:
    st.write(
        "AI assistants (ChatGPT, Claude, Perplexity, Google AI) are starting to "
        "recommend products. This checks how easily they can read and recommend "
        "**your** store. Paste your store URL for a free score."
    )
    url = st.text_input("Your Shopify store URL", placeholder="yourstore.com")

    if st.button("Get my AI-readiness score", type="primary"):
        if not url.strip():
            st.warning("Enter a store URL first.")
        else:
            with st.spinner("Analysing your store…"):
                result, err = analyze(url)
            if err:
                st.error(err)
                st.session_state.pop("result", None)
            else:
                st.session_state["result"] = result
                st.session_state["store_url"] = url

    if "result" in st.session_state:
        render_score(st.session_state["result"])
        st.divider()
        st.subheader("💡 Want the fixes?")
        st.write(
            "Unlock a prioritised, step-by-step action plan showing exactly how "
            "to raise your score — written in plain English for non-technical "
            "store owners. **$20, one-time.**"
        )

        missing = [k for k in ("STRIPE_SECRET_KEY", "APP_URL") if k not in st.secrets]
        if missing:
            st.info("Checkout not configured yet. (Owner: add " + ", ".join(missing) + " to Secrets.)")
        else:
            if st.button("Unlock full fix report — $20", type="primary"):
                try:
                    pay_url = create_checkout_session(
                        st.secrets["STRIPE_SECRET_KEY"],
                        st.secrets["APP_URL"],
                        st.session_state["store_url"],
                    )
                    st.session_state["pay_url"] = pay_url
                except Exception as e:
                    st.error(f"Couldn't start checkout: {e}")

            if "pay_url" in st.session_state:
                st.link_button("Pay $20 securely →", st.session_state["pay_url"], type="primary")
                st.caption("You'll pay on Stripe's secure page, then come straight back here — your report appears automatically.")
