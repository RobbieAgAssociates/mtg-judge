"""Refresh MTG: The Judge's saved data from its sources, then run make_site.py to rebuild.

Usage, from the repo root:
    python3 build/refresh_data.py            # everything
    python3 build/refresh_data.py cards cr   # only some steps

Steps: cards (Scryfall Oracle cards), rulings (Scryfall rulings), prints (every printing, for the Card Index), cr (Comprehensive Rules),
precons (MTGJSON Commander decklists + commander art + set symbols), combos (Commander Spellbook),
edhrec (picks for the four decks' commanders), tips (MTG Judges' Rules Tips index).
Wizards' release notes are not refreshed here; add new sets' notes by hand.
"""
import base64, datetime, gzip, html, io, json, os, re, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
UA = {"User-Agent": "mtg-judge-refresh/1.0 (+https://robbieagassociates.github.io/mtg-judge/)", "Accept": "application/json;q=0.9,*/*;q=0.8"}
slug = lambda n: re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def get(url, data=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url, **kw):
    return json.loads(get(url, **kw))


def download(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def pack(obj):
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(raw)
    return base64.b64encode(buf.getvalue()).decode()


def jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line and line not in "[]":
                yield json.loads(line)


def bulk_uri(kind):
    for b in get_json("https://api.scryfall.com/bulk-data")["data"]:
        if b["type"] == kind:
            return b.get("jsonl_download_uri") or b.get("download_uri")
    raise RuntimeError("no bulk file " + kind)


def resize(path, width=520):
    """Shrink a downloaded art crop if Pillow or macOS sips is available; otherwise keep it as is."""
    try:
        from PIL import Image
        im = Image.open(path)
        if im.width > width:
            im = im.convert("RGB").resize((width, round(im.height * width / im.width)))
        im.convert("RGB").save(path, "JPEG", quality=62, optimize=True)
        return
    except Exception:
        pass
    if sys.platform == "darwin":
        os.system(f'sips -Z {width} -s formatOptions 60 "{path}" --out "{path}" >/dev/null 2>&1')


# ---------- steps ----------
ORACLE = {}  # name -> Scryfall card, filled by the cards step and reused by later steps


def flatten(c):
    """A reversible card ('X // X', two printings of the same card) is really one card: use its front face."""
    if c.get("layout") != "reversible_card" or not c.get("card_faces"):
        return c
    f = c["card_faces"][0]
    flat = {k: v for k, v in c.items() if k != "card_faces"}
    flat.update({k: f[k] for k in ("name", "mana_cost", "type_line", "oracle_text", "power", "toughness", "loyalty", "defense", "image_uris", "artist") if k in f})
    flat["layout"] = "normal"
    return flat


def remember(c):
    """Index a card by full and front-face name."""
    for key in {c["name"], c["name"].split(" // ")[0]}:
        ORACLE.setdefault(key, c)


def step_cards(tmp):
    path = os.path.join(tmp, "oracle.jsonl.gz")
    download(bulk_uri("oracle_cards"), path)
    skip = {"token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"}
    rows = []
    for c in jsonl(path):
        c = flatten(c)
        if c.get("layout") in skip or c.get("set_type") in ("memorabilia", "token", "minigame") or c.get("lang", "en") != "en":
            continue   # art-series cards, tokens and the like aren't playable cards (and their names collide with real ones)
        remember(c)
        faces = c.get("card_faces") if "oracle_text" not in c else None
        text = c.get("oracle_text", "") if not faces else "\n—\n".join(
            f"{f['name']} {f.get('mana_cost','')}\n{f.get('type_line','')}\n{f.get('oracle_text','')}" + (f"\n{f['power']}/{f['toughness']}" if "power" in f else "")
            for f in faces)
        stats = f"{c['power']}/{c['toughness']}" if "power" in c else (f"Loyalty {c['loyalty']}" if "loyalty" in c else (f"Defense {c['defense']}" if "defense" in c else ""))
        leg = c.get("legalities", {}).get("commander", "")
        prices = c.get("prices") or {}
        rows.append([c["name"], c.get("mana_cost") or " // ".join(f.get("mana_cost", "") for f in (c.get("card_faces") or [])),
                     c.get("type_line", ""), text, stats,
                     {"legal": "L", "banned": "B", "not_legal": "N", "restricted": "R"}.get(leg, "N") + ("G" if c.get("game_changer") else ""),
                     "".join(c.get("color_identity", [])), prices.get("usd") or prices.get("usd_foil") or ""])
    rows.sort(key=lambda r: r[0])
    open(os.path.join(SITE, "cards.b64.txt"), "w").write(pack(rows))
    print(f"cards: {len(rows):,}")
    return path


def step_rulings(tmp, oracle_path=None):
    if not oracle_path:
        oracle_path = os.path.join(tmp, "oracle.jsonl.gz")
        download(bulk_uri("oracle_cards"), oracle_path)
    names = {c["oracle_id"]: c["name"] for c in jsonl(oracle_path) if c.get("oracle_id")}
    path = os.path.join(tmp, "rulings.jsonl.gz")
    download(bulk_uri("rulings"), path)
    out = {}
    for r in jsonl(path):
        nm = names.get(r.get("oracle_id"))
        if nm:
            out.setdefault(nm, []).append([r["published_at"], r["comment"], "W" if r.get("source") == "wotc" else "S"])
    for v in out.values():
        v.sort()
    open(os.path.join(SITE, "rulings.b64.txt"), "w").write(pack(out))
    print(f"rulings: {sum(len(v) for v in out.values()):,} for {len(out):,} cards")


def step_cr(tmp):
    page = get("https://magic.wizards.com/en/rules").decode("utf-8", "replace")
    links = re.findall(r'https://media\.wizards\.com/[^"\']+?\.txt', page)
    if not links:
        raise RuntimeError("no Comprehensive Rules .txt link found")
    lines = [l.rstrip("\r\n").replace(" ", " ").strip() for l in get(links[0].replace(" ", "%20")).decode("utf-8-sig").split("\n")]   # split on real line breaks only (the file contains U+2028)
    eff = next(l for l in lines if l.startswith("These rules are effective"))
    g = [i for i, l in enumerate(lines) if l == "Glossary"]
    c = [i for i, l in enumerate(lines) if l == "Credits"]
    start = next(i for i in range(c[0] + 1, len(lines)) if lines[i] == "1. Game Concepts")
    chapters, sections, rules = [], [], []
    for l in lines[start:g[1]]:
        if not l:
            continue
        m = re.match(r"^(\d)\. (.+)$", l)
        if m:
            chapters.append({"n": m.group(1), "t": m.group(2)}); continue
        m = re.match(r"^(\d{3})\. (.+)$", l)
        if m:
            sections.append({"n": m.group(1), "t": m.group(2), "ch": chapters[-1]["n"]}); continue
        m = re.match(r"^(\d{3}\.\d+[a-z]?)\.? (.+)$", l)
        if m:
            rules.append({"n": m.group(1), "t": m.group(2)}); continue
        if rules:
            rules[-1]["t"] += "\n" + l
    glossary, cur = [], None
    for l in lines[g[1] + 1:c[1]]:
        if not l:
            cur = None; continue
        if cur is None:
            cur = {"term": l, "def": ""}; glossary.append(cur)
        else:
            cur["def"] += ("\n" if cur["def"] else "") + l
    if len(rules) < 2000:
        raise RuntimeError(f"Comprehensive Rules parse looks wrong ({len(rules)} rules)")
    json.dump({"effective": eff, "chapters": chapters, "sections": sections, "rules": rules, "glossary": glossary},
              open(os.path.join(DATA, "cr", "cr.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    # every rule number the hand-checked topics cite must still exist
    have = {r["n"] for r in rules}
    missing = [(t["id"], n) for t in json.load(open(os.path.join(DATA, "topics.json"))) for n in t["rules"] if n not in have]
    print(f"cr: {eff} {len(rules):,} rules; topic rules missing: {missing}")


def step_precons(tmp):
    decks = [d for d in get_json("https://mtgjson.com/api/v5/DeckList.json")["data"] if d["type"] == "Commander Deck"]

    def fetch(d):
        x = get_json(f"https://mtgjson.com/api/v5/decks/{d['fileName']}.json")["data"]
        cnt, cmd = {}, []
        for sec in ("commander", "mainBoard"):
            for c in x.get(sec) or []:
                if sec == "commander":
                    cmd.append(c["name"])
                cnt[c["name"]] = cnt.get(c["name"], 0) + c["count"]
        cmd = cmd or [c["name"] for c in (x.get("displayCommander") or [])]
        return {"name": x["name"], "code": x["code"], "date": x["releaseDate"], "commander": cmd,
                "cards": [[n, k] if n != 1 else k for k, n in cnt.items()]}

    with ThreadPoolExecutor(8) as ex:
        out = list(ex.map(fetch, decks))
    out.sort(key=lambda d: d["date"], reverse=True)
    open(os.path.join(DATA, "bulk", "precons.b64"), "w").write(pack(out))

    if not ORACLE:  # commander colors and art need card data
        p = os.path.join(tmp, "oracle.jsonl.gz")
        download(bulk_uri("oracle_cards"), p)
        for c in jsonl(p):
            c = flatten(c)
            if c.get("layout") not in ("token", "double_faced_token", "emblem", "art_series") and c.get("set_type") not in ("memorabilia", "token"):
                remember(c)
    sets = {s["code"]: s for s in get_json("https://api.scryfall.com/sets")["data"]}
    meta, art, new_art = [], {}, 0
    for p in out:
        ci = set()
        for nm in p["commander"]:
            c = ORACLE.get(nm) or ORACLE.get(nm.split(" // ")[0])
            if c:
                ci |= set(c.get("color_identity", []))
        lead = (p["commander"] or [""])[0]
        c = ORACLE.get(lead) or ORACLE.get(lead.split(" // ")[0])
        if c:
            iu = c.get("image_uris") or (c.get("card_faces") or [{}])[0].get("image_uris") or {}
            f = f"img/cmdr/{slug(c['name'])}.jpg"
            if iu.get("art_crop"):
                if not os.path.exists(os.path.join(SITE, f)):
                    download(iu["art_crop"], os.path.join(SITE, f)); resize(os.path.join(SITE, f)); new_art += 1; time.sleep(0.08)
                art[c["name"]] = {"img": f, "artist": c.get("artist", "")}
        code = p["code"].lower()
        if code in sets and not os.path.exists(os.path.join(SITE, f"img/set/{code}.svg")):
            open(os.path.join(SITE, f"img/set/{code}.svg"), "wb").write(get(sets[code]["icon_svg_uri"]))
        meta.append({"id": slug(p["name"]) + "-" + code, "name": p["name"], "code": p["code"],
                     "set": sets[code]["name"] if code in sets else p["code"],
                     "setsym": f"img/set/{code}.svg" if code in sets else "", "date": p["date"], "commander": p["commander"],
                     "ci": "".join(x for x in "WUBRG" if x in ci), "lead": c["name"] if c else lead})
    json.dump({"decks": meta, "art": art}, open(os.path.join(DATA, "precon_meta.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"precons: {len(out)} decks, {new_art} new commander art")


def step_combos(tmp):
    path = os.path.join(tmp, "variants.json")
    download("https://json.commanderspellbook.com/variants.json", path)
    mine = {c["name"] for d in json.load(open(os.path.join(DATA, "pagedata.json")))["decks"] for c in d["cards"]}
    dec = json.JSONDecoder()
    combos = []
    with open(path, encoding="utf-8") as f:
        buf = f.read(4_000_000)
        i = buf.find("[", buf.find('"variants"')) + 1
        while True:
            while i < len(buf) and buf[i] in " \r\n\t,":
                i += 1
            if i >= len(buf) - 2_000_000:
                more = f.read(8_000_000)
                if more:
                    buf, i = buf[i:] + more, 0
                    continue
            if i >= len(buf) or buf[i] == "]":
                break
            try:
                v, j = dec.raw_decode(buf, i)
            except json.JSONDecodeError:
                more = f.read(8_000_000)
                if not more:
                    break
                buf, i = buf[i:] + more, 0
                continue
            i = j
            if v.get("status") != "OK" or not (v.get("legalities") or {}).get("commander"):
                continue
            names = [u["card"]["name"] for u in v["uses"]]
            if len(names) > 4:
                continue
            rec = [names, [p["feature"]["name"] for p in v.get("produces", [])][:4], v.get("bracketTag") or "",
                   v.get("popularity") or 0, v.get("identity") or "", [r["template"]["name"] for r in v.get("requires", [])]]
            if mine.intersection(names):
                rec.append((v.get("easyPrerequisites") or "")[:300] + "\n" + (v.get("notablePrerequisites") or "")[:300] + "\n" + (v.get("description") or "")[:1200])
            combos.append(rec)
    combos.sort(key=lambda r: -r[3])
    open(os.path.join(SITE, "combos.b64.txt"), "w").write(pack(combos))
    os.remove(path)
    print(f"combos: {len(combos):,}")


def step_edhrec(tmp):
    decks = json.load(open(os.path.join(DATA, "pagedata.json")))["decks"]
    try:
        old = json.load(open(os.path.join(DATA, "edhrec.json")))
    except Exception:
        old = {}
    out = {}
    for d in decks:
        s = (old.get(d["name"]) or {}).get("commander_slug") or slug(re.sub(r"[’']", "", d["commander"]))
        jd = get_json(f"https://json.edhrec.com/pages/commanders/{s}.json")["container"]["json_dict"]
        lists = {}
        for cl in jd.get("cardlists", []):
            if cl.get("header") in ("Lands", "New Cards"):
                continue
            lists[cl["header"]] = [[c["name"], round(100 * c["num_decks"] / c["potential_decks"]) if c.get("potential_decks") else None,
                                    round(100 * (c.get("synergy") or 0))] for c in cl.get("cardviews", [])]
        out[d["name"]] = {"commander_slug": s, "decks": jd.get("card", {}).get("num_decks") or 0,
                          "url": "https://edhrec.com/commanders/" + s, "lists": lists}
        time.sleep(0.3)
    json.dump(out, open(os.path.join(DATA, "edhrec.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"edhrec: {len(out)} commanders")


def step_tips(tmp):
    base = "https://blogs.magicjudges.org/rulestips/wp-json/wp/v2/"
    posts, names, page = [], {}, 1
    while True:
        try:
            batch = get_json(f"{base}posts?per_page=100&page={page}&_fields=title,link,date,categories,tags")
        except Exception:
            break
        if not batch:
            break
        posts += batch; page += 1
    for kind, prefix in (("tags", "t"), ("categories", "c")):
        page = 1
        while True:
            try:
                batch = get_json(f"{base}{kind}?per_page=100&page={page}&_fields=id,name")
            except Exception:
                break
            if not batch:
                break
            for x in batch:
                names[prefix + str(x["id"])] = html.unescape(x["name"])
            page += 1
    if len(posts) < 1000:
        raise RuntimeError(f"only {len(posts)} judges' tips found")
    out = []
    for p in posts:
        labels = [names.get("c" + str(i)) for i in p.get("categories", [])] + [names.get("t" + str(i)) for i in p.get("tags", [])]
        labels = [l for l in labels if l and l.lower() not in ("uncategorized", "rules tips", "rules")]
        out.append([html.unescape(p["title"]["rendered"]), p["link"], p["date"][:10], labels[:10]])
    out.sort(key=lambda r: r[2], reverse=True)
    open(os.path.join(DATA, "bulk", "judges.b64"), "w").write(pack(out))
    print(f"tips: {len(out):,}")


# The Card Index's function tags (Scryfall Tagger oracle tags, children included) and their labels.
ROLES = [("ramp", "Ramp"), ("mana-rock", "Mana rock"), ("mana-dork", "Mana creature"), ("cost-reducer", "Cost reducer"), ("ritual", "Ritual"),
         ("card-advantage", "Card advantage"), ("draw", "Card draw"), ("cantrip", "Cantrip"), ("tutor", "Tutor"), ("library-manipulation", "Library manipulation"),
         ("removal", "Removal"), ("sweeper", "Board wipe"), ("counterspell", "Counterspell"), ("burn", "Burn"), ("bounce", "Bounce"),
         ("theft", "Steal"), ("tapper", "Tapper"), ("pinger", "Pinger"), ("hand-disruption", "Hand disruption"), ("hate", "Hate"),
         ("recursion", "Recursion"), ("reanimate", "Reanimation"), ("mill", "Mill"), ("sacrifice-outlet", "Sacrifice outlet"),
         ("repeatable-token-generator", "Token maker"), ("anthem", "Anthem"), ("evasion", "Evasion"), ("gives-evasion", "Gives evasion"),
         ("combat-trick", "Combat trick"), ("protection", "Protection"), ("cheat-death", "Cheat death"), ("fog", "Fog"), ("lifegain", "Lifegain"),
         ("copy", "Copy"), ("flicker", "Flicker"), ("untapper", "Untapper"), ("extra-turn", "Extra turn"), ("mana-sink", "Mana sink"),
         ("typal", "Typal"), ("counters-matter", "Counters matter"), ("lands-matter", "Lands matter"), ("synergy-artifact", "Artifact synergy"),
         ("cards-in-graveyard-matter", "Graveyard matters"), ("group-slug", "Group slug"), ("multiplayer", "Multiplayer"), ("utility-land", "Utility land")]
FORMATS = ["standard", "pioneer", "modern", "legacy", "vintage", "commander", "pauper", "historic", "timeless", "brawl", "oathbreaker", "penny"]


def step_prints(tmp):
    """Every printing of every card (Scryfall default_cards) for the Card Index, plus formats, function tags and sets."""
    tags = {}
    path = os.path.join(tmp, "otags.jsonl.gz")
    download(bulk_uri("oracle_tags"), path)
    by_id = {}
    for line in gzip.open(path, "rt", encoding="utf-8"):
        line = line.strip().rstrip(",")
        if line and line not in "[]":
            t = json.loads(line); by_id[t["id"]] = t
    by_slug = {t["slug"]: t for t in by_id.values()}

    def tagged(t, seen):
        if t["id"] in seen:
            return set()
        seen.add(t["id"])
        s = {x["oracle_id"] for x in t["taggings"]}
        for c in t["child_ids"]:
            if c in by_id:
                s |= tagged(by_id[c], seen)
        return s
    for i, (sl, _) in enumerate(ROLES):
        for oid in tagged(by_slug[sl], set()) if sl in by_slug else ():
            tags.setdefault(oid, []).append(i)

    sets = sorted(get_json("https://api.scryfall.com/sets")["data"], key=lambda s: (s.get("released_at") or "9999", s["code"]))
    set_ix = {s["code"]: i for i, s in enumerate(sets)}
    path = os.path.join(tmp, "default.jsonl.gz")
    download(bulk_uri("default_cards"), path)
    skip = {"token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"}
    main_types = {"expansion", "core", "commander", "masters", "draft_innovation", "starter", "duel_deck", "funny", "eternal"}
    known = {r[0] for r in json.loads(gzip.decompress(base64.b64decode(open(os.path.join(SITE, "cards.b64.txt")).read())))}
    cards, artists, art_ix, used_sets = {}, [], {}, set()
    for c in jsonl(path):
        c = flatten(c)
        name = c["name"]
        if c.get("layout") in skip or c.get("set_type") in ("token", "minigame") or name not in known:
            continue   # same cards as the cards step (theme cards, tokens and the like are left out)
        card = cards.get(name)
        if card is None:
            leg = c.get("legalities", {})
            card = cards[name] = {"mv": c.get("cmc", 0), "leg": "".join({"legal": "L", "banned": "B", "restricted": "R"}.get(leg.get(f), "N") for f in FORMATS),
                                  "flags": ("R" if c.get("reserved") else "") + ("G" if c.get("game_changer") else ""),
                                  "rank": c.get("edhrec_rank"), "roles": sorted(tags.get(c.get("oracle_id"), [])),
                                  "kw": c.get("keywords", []), "prints": []}
        elif c.get("edhrec_rank") and not card["rank"]:
            card["rank"] = c["edhrec_rank"]
        a = c.get("artist") or ""
        if a not in art_ix:
            art_ix[a] = len(artists); artists.append(a)
        faces = c.get("card_faces") or []
        p = c.get("prices") or {}
        fl = ("d" if len(faces) > 1 and all("image_uris" in f for f in faces) else "") + ("D" if c.get("digital") else "") + \
             ("P" if c.get("promo") else "") + ("n" if c.get("image_status") in ("missing", "placeholder") else "") + \
             ("F" if c.get("finishes") == ["foil"] else "") + ("x" if c.get("full_art") else "") + ("b" if c.get("border_color") == "borderless" else "")
        card["prints"].append([set_ix.get(c["set"], -1), c["collector_number"], c["id"].replace("-", ""), (c.get("rarity") or "c")[0],
                               art_ix[a], p.get("usd") or p.get("usd_foil") or p.get("usd_etched") or "", fl, c.get("lang", "en"), c.get("released_at", "")])
        used_sets.add(c["set"])
    rows = []
    for name in sorted(cards):
        card = cards[name]
        pr = sorted(card["prints"], key=lambda x: (x[8], x[0]), reverse=True)
        # the picture shown in grids: the newest regular English paper printing with an image
        def good(x):
            st = sets[x[0]]["set_type"] if x[0] >= 0 else ""
            return x[7] == "en" and "D" not in x[6] and "n" not in x[6] and "P" not in x[6] and st in main_types
        default = next((i for i, x in enumerate(pr) if good(x) and "x" not in x[6] and "b" not in x[6]), None)
        if default is None:
            default = next((i for i, x in enumerate(pr) if good(x)), None)
        if default is None:
            default = next((i for i, x in enumerate(pr) if "n" not in x[6]), 0)
        # keep a printing's own release date only when it differs from its set's (Secret Lair drops, The List)
        rows.append([name, card["mv"], card["leg"], card["flags"], card["rank"], card["roles"], card["kw"], default,
                     [x[:8] + ([x[8]] if x[0] >= 0 and x[8] != (sets[x[0]].get("released_at") or "") else []) for x in pr]])
    set_rows = [[s["code"], s["name"], s.get("released_at") or "", s["set_type"], os.path.basename(s["icon_svg_uri"]).split(".")[0] if s.get("icon_svg_uri") else "",
                 s.get("parent_set_code") or "", 1 if s.get("digital") else 0, s.get("card_count", 0)] for s in sets]
    out = {"date": datetime.date.today().isoformat(), "formats": FORMATS, "roles": [label for _, label in ROLES],
           "sets": set_rows, "artists": artists, "cards": rows}
    open(os.path.join(SITE, "prints.b64.txt"), "w").write(pack(out))
    print(f"prints: {sum(len(r[8]) for r in rows):,} printings of {len(rows):,} cards in {len(used_sets):,} sets")


STEPS = ["cards", "rulings", "prints", "cr", "precons", "combos", "edhrec", "tips"]

if __name__ == "__main__":
    want = sys.argv[1:] or STEPS
    unknown = [s for s in want if s not in STEPS]
    if unknown:
        sys.exit(f"unknown steps: {unknown}; choose from {STEPS}")
    info_path = os.path.join(DATA, "info.json")
    info = json.load(open(info_path))
    today = datetime.date.today().isoformat()
    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        oracle_path = None
        for s in STEPS:
            if s not in want:
                continue
            try:
                if s == "cards":
                    oracle_path = step_cards(tmp)
                elif s == "rulings":
                    step_rulings(tmp, oracle_path)
                else:
                    globals()["step_" + s](tmp)
                if s in ("cards", "rulings", "prints", "combos"):
                    info["data_date"] = today
                if s == "edhrec":
                    info["edhrec_date"] = today
            except Exception as e:  # keep the old data for a step that fails
                failed.append(s)
                print(f"{s}: FAILED ({e}); keeping the previous data")
    json.dump(info, open(info_path, "w"))
    if failed:
        print("failed steps:", failed)
        sys.exit(1 if len(failed) == len(want) else 0)
