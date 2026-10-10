# Building MTG Judge

Everything needed to rebuild the site lives in this folder.

- `template.html`: the site's source (design, code and the Judge's instructions). Placeholders like `__DATA__` are filled in at build time.
- `make_site.py`: run `python3 build/make_site.py` from the repo root. It rebuilds `index.html` (the public site) and writes `mtg-judge.html` one folder up for the claude.ai page.
- `build.py`: the step that fills the template with the data (called by `make_site.py`).
- `data/`: deck data and stats, the Comprehensive Rules, EDHREC picks, and compressed pre-built decklists, release notes and judges' tips.
- `scripts/`: the scripts that downloaded and packed the data from Scryfall, MTGJSON, Commander Spellbook and Wizards' release notes.

The big data files the page loads (`cards.b64.txt`, `rulings.b64.txt`, `combos.b64.txt`) and the card images in `img/` sit in the repo root next to `index.html`.

After rebuilding, commit and push; GitHub Pages republishes in about a minute.
