"""Fill build/template.html with the saved data. Usage: build.py <data dir> <output html>"""
import sys, os, json, gzip, base64, datetime
D = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
t = open(os.path.join(HERE, "template.html")).read()
rd = lambda p: open(os.path.join(D, p)).read()
js = lambda p: rd(p).replace("</", "<\\/")          # safe inside <script>
unpack = lambda b64: json.loads(gzip.decompress(base64.b64decode(b64)))

def pretty(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"

# Counts and dates shown on the page come from the data, so a refresh updates them.
info = json.load(open(os.path.join(D, "info.json")))
cards = unpack(open(os.path.join(SITE, "cards.b64.txt")).read())
rulings = unpack(open(os.path.join(SITE, "rulings.b64.txt")).read())
combos = unpack(open(os.path.join(SITE, "combos.b64.txt")).read())
precons = json.load(open(os.path.join(D, "precon_meta.json")))["decks"]
notes = unpack(rd("bulk/releasenotes.b64"))
tips = unpack(rd("bulk/judges.b64"))
dates = sorted(p["date"] for p in precons)
stats = {
    "cards": len(cards), "rulings": sum(len(v) for v in rulings.values()), "rulingCards": len(rulings),
    "combos": len(combos), "precons": len(precons),
    "preconFirst": dates[0][:4], "preconLast": datetime.date.fromisoformat(dates[-1]).strftime("%B %Y"),
    "dataDate": pretty(info["data_date"]), "edhrecDate": pretty(info.get("edhrec_date", info["data_date"])),
    "releaseSets": len(notes), "releaseFirst": notes[0]["set"] if notes else "", "releaseLast": notes[-1]["set"] if notes else "",
    "judgeTips": len(tips),
}
sub = {"__DATA__": js("pagedata.json"), "__CR__": js("cr/cr.json"), "__EDHREC__": js("edhrec.json"),
       "__DECKMETA__": js("deckmeta.json"), "__SYMBOLS__": rd("symbols.json"), "__ART__": js("art.json"),
       "__PRECONMETA__": js("precon_meta.json"), "__TOPICS__": js("topics.json"), "__STATS__": json.dumps(stats),
       "__PRECONS__": rd("bulk/precons.b64"), "__RELEASENOTES__": rd("bulk/releasenotes.b64"), "__JUDGES__": rd("bulk/judges.b64"),
       "__CARDDATE__": stats["dataDate"]}
for k, v in sub.items():
    assert k in t, k
    t = t.replace(k, v)
open(sys.argv[2], "w").write(t)
print(len(t) // 1024, "KB", json.dumps(stats))
