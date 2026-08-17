"""
Fix-Report generator — the PAID tier.
Takes the score breakdown from scorer.py and asks Claude to turn every failed /
partial check into a plain-English, prioritised action plan a non-technical
Shopify store owner can actually follow.

Requires an Anthropic API key. On Streamlit Cloud, set it in the app's
Secrets as:  ANTHROPIC_API_KEY = "sk-ant-..."
"""

from anthropic import Anthropic

# Cheapest capable model — great for this job. Swap to "claude-sonnet-5" for
# richer, more detailed reports at higher per-call cost.
MODEL = "claude-haiku-4-5"


SYSTEM_PROMPT = """You are an ecommerce AI-visibility consultant writing a fix \
report for a Shopify store owner who is NOT technical. AI shopping assistants \
(ChatGPT, Claude, Perplexity, Google AI) increasingly recommend products, and \
this store owner wants theirs to be readable and recommendable by those \
assistants.

You will be given a store URL, its overall AI-readiness score, and a list of \
checks with pass/partial/fail status and a short detail for each.

Write a clear, encouraging, prioritised action plan. Rules:
- Address ONLY the checks that are 'fail' or 'partial'. Skip anything that passed.
- Order fixes by impact: biggest score gains first.
- For each fix, give: (1) what it means in plain English, (2) why it matters for \
AI visibility, (3) exact steps to fix it in Shopify (mention specific admin \
areas / apps where relevant), (4) roughly how long it takes.
- No jargon without explaining it. No code unless truly necessary, and if so, \
keep it copy-pasteable and explain where it goes.
- Warm, confident, practical tone. This person paid for this — make it worth it.
- End with a one-line summary of the single highest-impact thing to do first."""


def _breakdown_to_text(breakdown):
    lines = []
    for c in breakdown:
        lines.append(
            f"- [{c['status'].upper()}] {c['label']} "
            f"({c['earned']}/{c['max']} points): {c['detail']}"
        )
    return "\n".join(lines)


def generate_fix_report(api_key, store_url, score, breakdown):
    """
    Returns a markdown string: the full fix report.
    Raises on API errors so the app can show a friendly message.
    """
    client = Anthropic(api_key=api_key)

    user_msg = (
        f"Store URL: {store_url}\n"
        f"Overall AI-readiness score: {score}/100\n\n"
        f"Check results:\n{_breakdown_to_text(breakdown)}\n\n"
        f"Write the prioritised fix report now."
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    # Response content is a list of blocks; concatenate the text blocks.
    return "".join(
        block.text for block in resp.content if getattr(block, "type", "") == "text"
    )
