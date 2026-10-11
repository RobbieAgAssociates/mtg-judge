"""Export the site's saved data as grep-friendly text files for the mtg-judge Claude Code agent.

Usage, from the repo root:
    python3 build/export_agent_data.py ~/.claude/agents/mtg-judge-data

Writes:
  cards.tsv    name, mana cost, type, P/T or loyalty, Commander legality, Game Changer, color identity, price, Oracle text
  rulings.tsv  card name, date, source (Wizards/Scryfall), ruling
  cr.txt       one Comprehensive Rules entry per line ("702.19b <text>"), then the glossary ("GLOSSARY <term>: <definition>")
  topics.txt   the hand-checked rules index (topic, answer, rules)
  cardinfo.tsv name, mana value, legality in 12 formats, Reserved List, Game Changer, EDHREC rank, function tags, keywords,
               printings, first printed (set and date), cheapest and priciest USD, Card Index link
  prints.tsv   every printing: name, set code, set name, date, collector number, rarity, artist, USD, flags, language, image URL
  sets.tsv     every set: code, name, release date, type, card count, digital
  combos.tsv   Commander Spellbook combos: cards, results, color identity, other requirements
  precons.tsv  every Commander precon card: deck, set code, date, commander(s), count, card
  info.txt     dates and counts
"""
import base64, gzip, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
out = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.claude/agents/mtg-judge-data")
os.makedirs(out, exist_ok=True)
unpack = lambda p: json.loads(gzip.decompress(base64.b64decode(open(p).read())))
flat = lambda s: str(s).replace("\t", " ").replace("\r", " ").replace("\n", " / ")
LEGAL = {"L": "legal", "B": "banned", "N": "not legal", "R": "restricted"}

cards = unpack(os.path.join(SITE, "cards.b64.txt"))
with open(os.path.join(out, "cards.tsv"), "w") as f:
    f.write("name\tcost\ttype\tstats\tcommander\tgame_changer\tcolors\tusd\ttext\n")
    for name, cost, typ, text, stats, flags, ci, usd in cards:
        f.write("\t".join(map(flat, [name, cost, typ, stats, LEGAL.get(flags[:1], ""), "yes" if "G" in flags else "", ci or "C", usd, text])) + "\n")

rulings = unpack(os.path.join(SITE, "rulings.b64.txt"))
with open(os.path.join(out, "rulings.tsv"), "w") as f:
    f.write("card\tdate\tsource\truling\n")
    for name, rs in sorted(rulings.items()):
        for date, text, src in rs:
            f.write("\t".join(map(flat, [name, date, "Wizards" if src == "W" else "Scryfall", text])) + "\n")

cr = json.load(open(os.path.join(HERE, "data", "cr", "cr.json")))
with open(os.path.join(out, "cr.txt"), "w") as f:
    f.write(cr["effective"] + "\n")
    for s in cr["sections"]:
        f.write(f"SECTION {s['n']} {s['t']}\n")
    for r in cr["rules"]:
        f.write(f"{r['n']} {flat(r['t'])}\n")
    for g in cr["glossary"]:
        f.write(f"GLOSSARY {g['term']}: {flat(g['def'])}\n")

topics = json.load(open(os.path.join(HERE, "data", "topics.json")))
with open(os.path.join(out, "topics.txt"), "w") as f:
    for t in topics:
        f.write(f"TOPIC {t['title']}: {t['answer']} (CR {', '.join(t['rules'])}) Coach: {t.get('coach','')}\n")

pr = unpack(os.path.join(SITE, "prints.b64.txt"))
sets, artists, roles, formats = pr["sets"], pr["artists"], pr["roles"], pr["formats"]
RAR = {"c": "common", "u": "uncommon", "r": "rare", "m": "mythic", "s": "special", "b": "bonus"}
FLAGS = {"d": "double-faced", "D": "digital", "P": "promo", "n": "no image", "F": "foil only", "x": "full art", "b": "borderless"}
uuid = lambda h: f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
img = lambda h: f"https://cards.scryfall.io/normal/front/{h[0]}/{h[1]}/{uuid(h)}.jpg"
INDEX = "https://robbieagassociates.github.io/mtg-judge/cards/#card/"
n_prints = 0
with open(os.path.join(out, "prints.tsv"), "w") as fp, open(os.path.join(out, "cardinfo.tsv"), "w") as fc:
    fp.write("name\tset\tset_name\tdate\tnumber\trarity\tartist\tusd\tflags\tlang\timage\n")
    fc.write("name\tmv\t" + "\t".join(formats) + "\treserved\tgame_changer\tedhrec_rank\troles\tkeywords\tprintings\tfirst_printed\tmin_usd\tmax_usd\tindex\n")
    for name, mv, leg, flags, rank, rl, kw, default, prints in pr["cards"]:
        usd = [float(p[5]) for p in prints if p[5]]
        first = prints[-1]
        fs = sets[first[0]] if first[0] >= 0 else ["?", "?", ""]
        fc.write("\t".join(map(flat, [name, f"{mv:g}", *[LEGAL.get(c, c) for c in leg], "yes" if "R" in flags else "", "yes" if "G" in flags else "",
                 rank or "", ", ".join(roles[i] for i in rl), ", ".join(kw), len(prints), f"{fs[1]} ({first[8] if len(first) > 8 else fs[2]})",
                 f"{min(usd):.2f}" if usd else "", f"{max(usd):.2f}" if usd else "", INDEX + urllib.parse.quote(name)])) + "\n")
        for p in prints:
            st = sets[p[0]] if p[0] >= 0 else ["?", "?", ""]
            fp.write("\t".join(map(flat, [name, st[0], st[1], p[8] if len(p) > 8 else st[2], p[1], RAR.get(p[3], p[3]), artists[p[4]], p[5],
                     ", ".join(FLAGS[f] for f in p[6] if f in FLAGS), p[7], "" if "n" in p[6] else img(p[2])])) + "\n")
            n_prints += 1
with open(os.path.join(out, "sets.tsv"), "w") as f:
    f.write("code\tname\tdate\ttype\tcards\tdigital\n")
    for code, nm, date, typ, icon, parent, digital, count in sets:
        f.write("\t".join(map(flat, [code, nm, date, typ, count, "yes" if digital else ""])) + "\n")

combos = unpack(os.path.join(SITE, "combos.b64.txt"))
with open(os.path.join(out, "combos.tsv"), "w") as f:
    f.write("cards\tresults\tcolors\talso_needs\n")
    for r in combos:
        f.write("\t".join(map(flat, [" + ".join(r[0]), "; ".join(r[1]), r[4] or "C", "; ".join(r[5] or [])])) + "\n")
precons = unpack(os.path.join(HERE, "data", "bulk", "precons.b64"))
with open(os.path.join(out, "precons.tsv"), "w") as f:
    f.write("deck\tset\tdate\tcommander\tcount\tcard\n")
    for d in precons:
        for c in d["cards"]:
            n, name = c if isinstance(c, list) else (1, c)
            f.write("\t".join(map(flat, [d["name"], d["code"], d["date"], " / ".join(d["commander"]), n, name])) + "\n")

info = json.load(open(os.path.join(HERE, "data", "info.json")))
with open(os.path.join(out, "info.txt"), "w") as f:
    f.write(f"Data saved {info['data_date']}; {cr['effective']}\n{len(cards):,} cards, {sum(len(v) for v in rulings.values()):,} rulings, {len(cr['rules']):,} rules, {len(topics)} topics, {n_prints:,} printings in {len(sets):,} sets.\n")
print("wrote", out, "|", len(cards), "cards,", sum(len(v) for v in rulings.values()), "rulings,", len(cr["rules"]), "rules,", n_prints, "printings")
