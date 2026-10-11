"""Export the site's saved data as grep-friendly text files for the mtg-judge Claude Code agent.

Usage, from the repo root:
    python3 build/export_agent_data.py ~/.claude/agents/mtg-judge-data

Writes:
  cards.tsv    name, mana cost, type, P/T or loyalty, Commander legality, Game Changer, color identity, price, Oracle text
  rulings.tsv  card name, date, source (Wizards/Scryfall), ruling
  cr.txt       one Comprehensive Rules entry per line ("702.19b <text>"), then the glossary ("GLOSSARY <term>: <definition>")
  topics.txt   the hand-checked rules index (topic, answer, rules)
  info.txt     dates and counts
"""
import base64, gzip, json, os, sys

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

info = json.load(open(os.path.join(HERE, "data", "info.json")))
with open(os.path.join(out, "info.txt"), "w") as f:
    f.write(f"Data saved {info['data_date']}; {cr['effective']}\n{len(cards):,} cards, {sum(len(v) for v in rulings.values()):,} rulings, {len(cr['rules']):,} rules, {len(topics)} topics.\n")
print("wrote", out, "|", len(cards), "cards,", sum(len(v) for v in rulings.values()), "rulings,", len(cr["rules"]), "rules")
