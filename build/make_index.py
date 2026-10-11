"""Build the Card Index page (website/cards/index.html) from build/index_template.html.

Usage, from the website folder (make_site.py also runs it):
    python3 build/make_index.py
The page fetches ../cards.b64.txt, ../prints.b64.txt, ../rulings.b64.txt and ../combos.b64.txt at run time,
so run `python3 build/refresh_data.py cards prints` first if those are missing or stale.
"""
import base64, gzip, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
URL = "https://robbieagassociates.github.io/mtg-judge/cards/"
DESCRIPTION = "Every Magic: The Gathering card and every printing, with images, formats, rulings, combos and a quick analysis."
FAVICON = ("data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%230d1015'/%3E"
           "%3Cpath d='M16 3 29 16 16 29 3 16Z' fill='none' stroke='%23ebe8e1' stroke-width='2'/%3E"
           "%3Cpath d='M16 8v16M10 13h12M11 13l-3 6h6zM21 13l-3 6h6z' fill='none' stroke='%23d8ad55' "
           "stroke-width='1.6' stroke-linejoin='round'/%3E%3C/svg%3E")
HEAD = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0d1015">
<link rel="icon" href="{FAVICON}">
<link rel="canonical" href="{URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MTG: The Judge">
<meta property="og:title" content="Card Index · MTG: The Judge">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}../img/temmet-naktamun-s-will-art.jpg">
<meta name="twitter:card" content="summary_large_image">
</head><body>"""


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main():
    page = open(os.path.join(HERE, "index_template.html"), encoding="utf-8").read()
    symbols = {k: "../" + v for k, v in json.load(open(os.path.join(DATA, "symbols.json"))).items()}
    precons_b64 = open(os.path.join(DATA, "bulk", "precons.b64")).read().strip()
    precons = json.loads(gzip.decompress(base64.b64decode(precons_b64)))
    ids = {(m["name"], m["code"]): m["id"] for m in json.load(open(os.path.join(DATA, "precon_meta.json")))["decks"]}
    page = (page.replace("__SYMBOLS__", js(symbols))
                .replace("__PRECONIDS__", js([ids.get((p["name"], p["code"]), "") for p in precons]))
                .replace("__PRECONS__", precons_b64))
    os.makedirs(os.path.join(SITE, "cards"), exist_ok=True)
    out = os.path.join(SITE, "cards", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(HEAD + page + "</body></html>\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
