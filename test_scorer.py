from scorer import score_store

# ---- A well-optimized store ----
GOOD = """
<html>
<head>
  <title>Nordic Wool Co — Premium Merino Base Layers</title>
  <meta name="description" content="Ethically sourced merino wool base layers designed for cold-weather performance. Free shipping over $80.">
  <meta property="og:title" content="Nordic Wool Co">
  <meta property="og:description" content="Premium merino base layers for the outdoors.">
  <script type="application/ld+json">
  {"@type":"Organization","name":"Nordic Wool Co"}
  </script>
  <script type="application/ld+json">
  {"@type":"Product","name":"Merino Crew Base Layer","offers":{"price":"89.00"}}
  </script>
  <script type="application/ld+json">
  {"@type":"FAQPage","mainEntity":[]}
  </script>
</head>
<body>
  <h1>Merino Crew Base Layer</h1>
  <img src="crew.jpg" alt="Grey merino wool crew base layer front view">
  <img src="crew-back.jpg" alt="Merino crew base layer back view">
  <p>Our flagship merino crew is knitted from 18.5 micron ethically sourced
  Australian merino wool. It regulates temperature across a wide range,
  resists odour naturally, and is soft enough to wear all day next to skin.
  Machine washable, reinforced flatlock seams, and designed to layer cleanly
  under a shell. Backed by our 60-day comfort guarantee.</p>
  <h2>Frequently Asked Questions</h2>
  <p>How do I wash it? Cold machine wash, lay flat to dry.</p>
</body>
</html>
"""

GOOD_PRODUCTS = [{"body_html": "x" * 700}, {"body_html": "y" * 650}]

# ---- A typical un-optimized store ----
BAD = """
<html>
<head><title>Home</title></head>
<body>
  <img src="1.jpg">
  <img src="2.jpg">
  <p>Buy now. Best product. Add to cart.</p>
</body>
</html>
"""

print("=" * 55)
print("GOOD STORE")
res = score_store(GOOD, llms_txt_present=True, products_sample=GOOD_PRODUCTS)
print(f"SCORE: {res['score']}/100\n")
for c in res["breakdown"]:
    mark = {"pass": "PASS", "partial": "~", "fail": "FAIL"}[c["status"]]
    print(f"  [{mark:>4}] {c['earned']}/{c['max']}  {c['label']}")
    print(f"         -> {c['detail']}")

print("\n" + "=" * 55)
print("BAD STORE")
res = score_store(BAD, llms_txt_present=False)
print(f"SCORE: {res['score']}/100\n")
for c in res["breakdown"]:
    mark = {"pass": "PASS", "partial": "~", "fail": "FAIL"}[c["status"]]
    print(f"  [{mark:>4}] {c['earned']}/{c['max']}  {c['label']}")
    print(f"         -> {c['detail']}")
