# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MTG: The Judge, an unofficial Magic: The Gathering rules judge, game tracker and Commander deck guide. It is a single static page published two ways:

- **GitHub Pages** (this repo, `main` branch, root): https://robbieagassociates.github.io/mtg-judge/. Pushing to `main` republishes in about a minute.
- **claude.ai artifact** (private to the owner): built from `../mtg-judge.html` (one folder up, outside the repo) and published with Claude Code's Artifact tool to https://claude.ai/artifact/GzhaE7nhieQyF3NMrM5PUL. Pass that URL when republishing so the link stays the same.

There is no package manager, bundler or test suite. Everything is plain HTML/CSS/JS in one template, filled in by Python.

## Commands

```bash
# Rebuild index.html (public site), cards/index.html (Card Index) and ../mtg-judge.html (claude.ai page) from build/
python3 build/make_site.py

# Refresh the data from Scryfall, Wizards, MTGJSON, Commander Spellbook, EDHREC and the judges' blog
# (all steps, or name some: cards rulings prints cr precons combos edhrec tips); then rebuild
python3 build/refresh_data.py && python3 build/make_site.py

# Export grep-friendly copies of the data for the mtg-judge and mtg-cards Claude Code agents
python3 build/export_agent_data.py ~/.claude/agents/mtg-judge-data

# Serve locally (the page fetches data files, so file:// won't work)
python3 -m http.server 8766 --bind 127.0.0.1

# Syntax-check the page's main script (no node on this machine; uses macOS JavaScriptCore)
python3 -I -c 'import re,sys;t=open("index.html").read();open(sys.argv[1],"w").write(re.findall(r"<script>(.*?)</script>",t,re.S)[-1])' "$TMPDIR/c.js" \
  && osascript -l JavaScript -e 'ObjC.import("Foundation"); var s=$.NSString.stringWithContentsOfFileEncodingError("'"$TMPDIR"'/c.js",$.NSUTF8StringEncoding,null).js; try{ new Function(s); "SYNTAX OK" }catch(e){ "SYNTAX ERROR: "+e }'
```

A rebuild with no source changes must leave `git status` clean; use that to confirm the build is reproducible.

## Architecture

**Build pipeline.** `build/template.html` is the whole site (CSS, markup, JS). `build/build.py` replaces `__PLACEHOLDER__` tokens with JSON or base64 from `build/data/` (`__DATA__` decks and notes, `__CR__` Comprehensive Rules, `__EDHREC__`, `__DECKMETA__`, `__SYMBOLS__`, `__ART__`, `__PRECONMETA__`, plus base64-gzip blobs for precons, release notes and judges' tips). `build/make_site.py` runs it, then wraps the result in a `<!doctype>` head with favicon, Open Graph tags and canonical URL to produce `index.html`. The claude.ai copy is the unwrapped body, because the artifact host adds its own skeleton. Any JSON injected into a `<script>` must have `</` escaped as `<\/` (build.py does this).

**Data loading.** Small datasets are inlined as base64 gzip in `<script type="text/plain" id="data-…">` tags. The three big ones sit next to the page as `cards.b64.txt` (all ~34.6k cards' Oracle text, legality, color identity, USD price), `rulings.b64.txt` (~80k official rulings) and `combos.b64.txt` (~104k Commander Spellbook combos). `loadData(name)` in the template reads the inline tag if present, otherwise fetches `name.replace(".json.gz",".b64.txt")`, then decodes and gunzips with `DecompressionStream`. Files are base64 `.txt` because the artifact host refuses `.gz`.

**App structure.** A single-page app with hash routing. `state.view` holds the current view; `go(view)` sets it, updates the hash and calls `renderTabs()` and `render()`, which rebuild `#main`. Views: `home`, `ask`, `game`, `ideas`, `comparison` (Decks), `precons`, `all` (Search), `lookup` (Cards), `rules`, `sources`, the four deck ids, and `pc-<id>` for each precon. View builders (`homeEl`, `deckPageEl`, `chatEl`, `gameEl`, `ideasEl`, `preconsEl`, `preconPageEl`, `rulesPage`, …) return DOM nodes and wire events in a `queueMicrotask`. Those callbacks must null-check their elements, because a fast view switch can remove them first.

**The Judge: two modes.** `window.claude.use("sample")` is only available inside the claude.ai artifact. There, chat, game checks, recaps and deck ideas call Claude with page-defined tools (`TOOLS`: rule search, card lookup, rulings, combos, precon lists, EDHREC, release notes, judges' tips, game state). On GitHub Pages, and for signed-out claude.ai viewers, `chat.sample` is null, so the same features fall back to **lookup mode** (`lookupChat`, `lookupMove`, `lookupRecap`, `lookupIdeas`), which builds Markdown answers from the saved data with no AI. `IN_CLAUDE` gates "sign in to claude.ai" wording so the public site never shows it. Keyword rules come from `KEYWORDS`, built from CR 701/702 titles. Card names that are also keywords (Flash, Haste) are excluded from card matching so the keyword wins.

**Layered card previews.** `linkCards(root)` wraps known deck card names (plus unambiguous short legend names via `ALIAS`) in `.cardref` buttons. Hovering or tapping any `[data-card]` shows `#peek` with the card image (deck cards) or text (others, via `lookupCard`). Call `linkCards` on any newly rendered notes or answers.

**Per-viewer state** lives in `localStorage` (`mtgjudge.chat`, `mtgjudge.game`, `mtgjudge.ideas`), always wrapped in try/catch.

**Rules index.** `build/data/topics.json` holds hand-checked answers to common questions (deathtouch + trample, responding, the stack, commander tax/damage/zone, copies, triggers…), each with the CR rules it comes from and a Coach tip. `matchTopics()` uses it in lookup answers, game checks, the Rules page's "Quick answers", and Claude's `rules_index` tool. `refresh_data.py cr` reports any topic rule number that disappears from a new CR.

**Answer format.** Chat answers are: restated question with an inferred answer, Judge check, Coach check, Final call (Judge) with a confidence percentage and reasons. Lookup mode picks the inferred answer from (in order) a deck note naming every card asked about, a rules-index topic, an official ruling, or the best-matching rule sentence.

**Card Index** (`cards/index.html`, built by `build/make_index.py` from `build/index_template.html`). A separate page for every card and every printing, with images hot-linked from Scryfall's CDN (`cards.scryfall.io`, URL built from the printing's id; nothing is downloaded). It fetches `../cards.b64.txt` (Oracle text), `../prints.b64.txt` (every printing: set, number, Scryfall id, rarity, artist, price, flags, plus per-card legality in 12 formats, EDHREC rank and Scryfall Tagger function tags), and lazily `../rulings.b64.txt` and `../combos.b64.txt`; precons are inlined. Hash routes: `#card/<name>?print=<set>/<number>`, `#search?q=&sort=&mode=&page=`, `#sets`, `#set/<code>`, `#artist/<name>`, `#random`. Search is a Scryfall-style syntax parsed in `parseQuery`/`makeFilter`. The main site links to it via `CARD_INDEX` (the absolute public URL inside the claude.ai copy, which doesn't carry `cards/`). The `prints` step of `refresh_data.py` builds `prints.b64.txt` from Scryfall's `default_cards`, `oracle_tags` and sets.

**Deck Builder** (`#build` in the Card Index; `DECK_FORMATS`, `BRACKETS`, `THEMES`, `VARIANTS`, `buildDeck`, `checkDeck` in `index_template.html`). Builds up to four decks per request (Focused, Crowd favorites, Budget, Wildcard) from every card legal in the chosen format: Commander and Brawl (100-card singleton within the commander's color identity, bracket limits on Game Changers, mass land destruction, extra turns and two-card infinite combos via Commander Spellbook data) or 60-card formats (up to 4 copies, 1 if restricted, 15-card sideboard). Cards are scored by theme fit (regexes, Scryfall function tags, creature types), commander synergy words and EDHREC popularity; Commander decks fill role targets first (10 ramp, 10 draw, 8 removal, 3 wipes, 2 protection), then the theme; lands are the most-played fixing lands plus basics split by mana symbols. `checkDeck` re-checks every finished deck against the format's rules and shows the result. Settings live in the hash (`#build?f=&c=&col=&t=&ty=&b=&br=&n=`), so a link reproduces a build (with some randomness in the Wildcard and Budget variants); built decks can be edited (`fitsDeck`, `deckLimit`, `addCard`, `changeCard`, `editDeck`): the add-card search offers only cards legal in the deck's format (and color identity for Commander and Brawl) under the copy limit, and `checkDeck` re-runs after every change. Saved decks (localStorage `mtgcards.decks`) store the exact edited list and reopen with `#build?saved=<id>`.

**MTG Cards app** (`mtg-cards-app/`). A local chat app for the `mtg-cards` Claude Code agent (`~/.claude/agents/mtg-cards.md`), not part of the Pages site. `server.py` (stdlib only, 127.0.0.1:8790) serves `app.html` and runs each question with `claude -p --agent mtg-cards --output-format stream-json`, streaming progress and the answer as NDJSON; follow-ups pass `--resume <session>`. The agent runs in `~/.claude/agents/mtg-judge-data/` with `--add-dir` and an allow-list of read-only tools; `APP_PROMPT` keeps its commands within that list (no `cd`, variables, `$'...'` or python). Start with `python3 mtg-cards-app/server.py` or `Start MTG Cards.command`.

**Automation.** `.github/workflows/refresh-data.yml` runs the refresh monthly (and on demand), commits changes and asks Pages to rebuild. Counts and dates on the page come from the data at build time (`__STATS__` in `build.py`), not from the template.

## Data and sources

- `build/data/pagedata.json`: the user's four decks (Eternal Might, Living Energy, Counter Intelligence, World Shaper) with card text, mana value, image paths and analysis sections. Generated by `build/scripts/pagedata.py` from the deck analysis files in `~/.claude/agents/mtg-judge-decks/` (the companion Claude Code agent, repo RobbieAgAssociates/claude-agents).
- `build/data/deckmeta.json`: hand-written per-deck tagline, stats, bracket and key-card list used by the dashboard.
- `build/scripts/`: the one-off scripts that downloaded and packed the data (Scryfall bulk Oracle cards and rulings, MTGJSON decklists, Commander Spellbook's `variants.json`, Wizards release notes, the CR text). They take input and output paths as arguments; the raw downloads are not kept in the repo.
- Images live in `img/` (deck card images, `img/art/` art crops, `img/cmdr/` precon commander art, `img/sym/` mana symbols, `img/set/` set symbols). Scryfall requires a `User-Agent` and `Accept` header on API calls, and it blocks WebFetch.

## Gotchas

- The claude.ai artifact holds at most 511 files per version and is already near the cap, so precon commander art (`img/cmdr/`) is not uploaded there. Only the public site shows it.
- `${…}` interpolation only works inside backtick template literals. Several edits have broken the script by adding `${}` inside a `"…"` string, so run the syntax check after editing.
- Keep Commander and Standard rules separate in any Judge instructions. Official sources (CR, rulings, release notes) outrank community ones (EDHREC, Commander Spellbook, judges' blog).
- The footer carries the Wizards of the Coast Fan Content Policy notice. Keep it on every published version.
