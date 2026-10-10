"""Rebuild MTG Judge: the claude.ai page (mtg-judge.html) and the public GitHub Pages site (website/index.html).

Usage, from the website folder (the git repo):
    python3 build/make_site.py
Writes website/index.html and, one level up, mtg-judge.html for the claude.ai page.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)            # the website folder / git repo
ROOT = os.path.dirname(SITE)            # the MTG Judge folder
SITE_URL = "https://robbieagassociates.github.io/mtg-judge/"
DESCRIPTION = ("An unofficial Magic: The Gathering rules judge, game tracker and Commander deck guide, "
               "built on the Comprehensive Rules and every card's official text and rulings.")

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
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MTG: The Judge">
<meta property="og:title" content="MTG: The Judge">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}img/temmet-naktamun-s-will-art.jpg">
<meta name="twitter:card" content="summary_large_image">
</head><body>"""


def main():
    page = os.path.join(ROOT, "mtg-judge.html")
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "build.py"), os.path.join(HERE, "data"), page], check=True)
    body = open(page, encoding="utf-8").read()
    out = os.path.join(SITE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(HEAD + body + "</body></html>\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
