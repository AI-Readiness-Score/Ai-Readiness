"""
AI-Readiness Scorer — Streamlit app.
Deploy this to Streamlit Cloud (free). It fetches a real Shopify store, runs the
checks from scorer.py, and shows a 0-100 score with a breakdown.
"""

import streamlit as st
import requests
from scorer import score_store, CHECKS

st.set_page_config(page_title="AI Readiness Score", page_icon="🛍️", layout="centered")

HEADERS = {"User-Agent": "Mozilla/5.0 (AI-Readiness-Bot)"}


def fetch(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r
    except Exception:
        return None


def analyze(store_url):
    store_url = store_url.rstrip("/")
    if not store_url.startswith("http"):
        store_url = "https://" + store_url

    # 1. homepage HTML
    home = fetch(store_url)
    if not home or home.status_code >= 400:
        return None, "Couldn't reach that store. Check the URL and try again."
    html = home.text

    # 2. products.json (Shopify exposes this by default on most stores)
    products_sample = None
    pj = fetch(store_url + "/products.json?limit=5")
    if pj and pj.status_code == 200:
        try:
            products_sample = pj.json().get("products", [])[:5]
        except Exception:
            products_sample = None

    # 3. robots.txt + llms.txt
    robots = fetch(store_url + "/robots.txt")
    robots_txt = robots.text if robots and robots.status_code == 200 else ""
    llms = fetch(store_url + "/llms.txt")
    llms_present = bool(llms and llms.status_code == 200 and len(llms.text) > 20)

    result = score_store(html, robots_txt, llms_present, products_sample)
    return result, None


# ---------- UI ----------
st.title("🛍️ Is your store ready for AI shoppers?")
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
        else:
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

            st.divider()
            # ---- paid tier CTA (wire up payment later) ----
            st.subheader("Want the fixes?")
            st.write(
                "Get a prioritised, step-by-step action plan showing exactly how "
                "to raise your score — written for non-technical store owners."
            )
            st.link_button("Get my fix report →", "https://your-payment-link.example")
            st.caption("Replace this button with your Stripe/Gumroad link when ready.")
