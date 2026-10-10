import json,sys,collections
S=json.load(open(sys.argv[1])); deck=sys.argv[2]
cards=S["cards"]; BASIC={"Plains","Island","Swamp","Mountain","Forest","Wastes"}
def txt(c):
    if "card_faces" in c and "oracle_text" not in c:
        return " /// ".join(f"[{f['name']} {f.get('mana_cost','')} {f['type_line']}] {f.get('oracle_text','')}" for f in c["card_faces"])
    return c.get("oracle_text","")
lands=0; curve=collections.Counter(); flags=[]; total=0
for e in S["decks"][deck]:
    c=cards[e["name"].split(" // ")[0]]; total+=e["count"]
    tl=c["type_line"]
    if c["legalities"]["commander"]!="legal": flags.append((c["name"],c["legalities"]["commander"]))
    if c.get("game_changer"): flags.append((c["name"],"GAME CHANGER"))
    if "Land" in tl.split("//")[0]: lands+=e["count"]
    else: curve[int(c["cmc"])]+=0 if e["commander"] else 1
    if e["name"] in BASIC: continue
    pt=f" {c['power']}/{c['toughness']}" if "power" in c else ""
    print(f"* {c['name']} {c.get('mana_cost','')} | {tl}{pt}{' | COMMANDER CI='+''.join(c['color_identity']) if e['commander'] else ''}\n  "+txt(c).replace("\n"," ¶ "))
print("TOTAL",total,"LANDS",lands,"CURVE",sorted(curve.items()),"FLAGS",flags)
