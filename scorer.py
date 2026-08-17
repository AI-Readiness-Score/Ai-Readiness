"""
AI-Readiness Scorer — core logic.
Takes a store's HTML (+ robots.txt / llms.txt availability) and returns a 0-100
score plus a per-check breakdown. Kept separate from the UI so it can be tested
on its own and reused anywhere.
"""

from bs4 import BeautifulSoup
import json


# Each check has a weight. Weights sum to 100 so the raw score IS the /100 score.
CHECKS = [
    ("structured_data",   20, "Product/Organization schema (JSON-LD)"),
    ("meta_description",   12, "Meta description present & useful length"),
    ("title_tag",          8,  "Page title present & descriptive"),
    ("open_graph",         12, "Open Graph tags (og:title, og:description)"),
    ("image_alt",          15, "Product images have alt text"),
    ("description_depth",  13, "Product descriptions have real depth"),
    ("llms_txt",           10, "llms.txt present (AI-crawler readiness)"),
    ("faq_content",        10, "FAQ / Q&A style content present"),
]


def _check_structured_data(soup):
    scripts = soup.find_all("script", type="application/ld+json")
    types_found = set()
    for s in scripts:
        try:
            data = json.loads(s.string or "{}")
            items = data if isinstance(data, list) else [data]
            for it in items:
                t = it.get("@type", "")
                if isinstance(t, list):
                    types_found.update(t)
                elif t:
                    types_found.add(t)
        except Exception:
            continue
    has_product = "Product" in types_found
    has_org = any(x in types_found for x in ("Organization", "Store", "WebSite"))
    if has_product and has_org:
        return 1.0, "Product + Organization schema found"
    if has_product or has_org:
        return 0.5, f"Partial schema found: {', '.join(types_found) or 'some'}"
    return 0.0, "No JSON-LD structured data found"


def _check_meta_description(soup):
    tag = soup.find("meta", attrs={"name": "description"})
    content = (tag.get("content", "") if tag else "").strip()
    if not content:
        return 0.0, "No meta description"
    if len(content) < 50:
        return 0.5, f"Meta description too short ({len(content)} chars)"
    return 1.0, f"Good meta description ({len(content)} chars)"


def _check_title(soup):
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    if not title:
        return 0.0, "No page title"
    if len(title) < 10:
        return 0.5, "Title present but very short"
    return 1.0, f"Title present ({len(title)} chars)"


def _check_open_graph(soup):
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    have = sum(bool(x and x.get("content")) for x in (og_title, og_desc))
    if have == 2:
        return 1.0, "og:title and og:description present"
    if have == 1:
        return 0.5, "Only one Open Graph tag present"
    return 0.0, "No Open Graph tags"


def _check_image_alt(soup):
    imgs = soup.find_all("img")
    # Ignore tiny/tracking pixels heuristically by keeping all; product stores
    # usually have plenty. If there are no images at all, treat as neutral-low.
    if not imgs:
        return 0.0, "No images found on page"
    with_alt = sum(1 for i in imgs if (i.get("alt") or "").strip())
    ratio = with_alt / len(imgs)
    return round(ratio, 2), f"{with_alt}/{len(imgs)} images have alt text"


def _check_description_depth(soup, products_sample=None):
    # If we have real product data from /products.json, use it. Otherwise fall
    # back to visible body text length as a rough proxy.
    if products_sample:
        lengths = [len((p.get("body_html") or "")) for p in products_sample]
        avg = sum(lengths) / len(lengths) if lengths else 0
        if avg >= 600:
            return 1.0, f"Rich product descriptions (avg ~{int(avg)} chars)"
        if avg >= 200:
            return 0.5, f"Thin product descriptions (avg ~{int(avg)} chars)"
        return 0.0, "Product descriptions very thin or missing"
    text = soup.get_text(" ", strip=True)
    words = len(text.split())
    if words >= 400:
        return 1.0, f"Page has substantial text ({words} words)"
    if words >= 150:
        return 0.5, f"Page text is light ({words} words)"
    return 0.0, f"Very little page text ({words} words)"


def _check_faq(soup):
    text = soup.get_text(" ", strip=True).lower()
    # FAQPage schema is the strongest signal
    for s in soup.find_all("script", type="application/ld+json"):
        if s.string and "faqpage" in s.string.lower():
            return 1.0, "FAQPage schema found"
    hints = ["frequently asked", "faq", "q&a", "questions & answers"]
    if any(h in text for h in hints):
        return 0.5, "FAQ-style content mentioned (no schema)"
    return 0.0, "No FAQ / Q&A content detected"


def score_store(html, robots_txt="", llms_txt_present=False, products_sample=None):
    """
    Main entry point.
      html               : raw HTML of the store homepage (or a product page)
      robots_txt         : contents of robots.txt (string), optional
      llms_txt_present   : bool — did /llms.txt return 200?
      products_sample    : list of product dicts from /products.json, optional
    Returns: dict with 'score' (0-100) and 'breakdown' (list of check results)
    """
    soup = BeautifulSoup(html or "", "html.parser")

    raw = {
        "structured_data":  _check_structured_data(soup),
        "meta_description": _check_meta_description(soup),
        "title_tag":        _check_title(soup),
        "open_graph":       _check_open_graph(soup),
        "image_alt":        _check_image_alt(soup),
        "description_depth": _check_description_depth(soup, products_sample),
        "llms_txt":         (1.0 if llms_txt_present else 0.0,
                             "llms.txt present" if llms_txt_present else "No llms.txt file"),
        "faq_content":      _check_faq(soup),
    }

    breakdown = []
    total = 0.0
    for key, weight, label in CHECKS:
        frac, detail = raw[key]
        earned = frac * weight
        total += earned
        breakdown.append({
            "label": label,
            "earned": round(earned, 1),
            "max": weight,
            "detail": detail,
            "status": "pass" if frac >= 0.99 else ("partial" if frac > 0 else "fail"),
        })

    return {"score": round(total), "breakdown": breakdown}
