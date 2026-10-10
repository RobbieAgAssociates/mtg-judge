import json,sys,collections,re
S=json.load(open(sys.argv[1])); C=S["cards"]
def mv(c):
    if c.get("layout") in ("split","adventure") and "card_faces" in c:
        f=c["card_faces"][0]["mana_cost"]
        n=0
        for s in re.findall(r"\{([^}]*)\}",f):
            n+= int(s) if s.isdigit() else (0 if s=="X" else 1)
        return n
    return int(c["cmc"])
for deck,cards in S["decks"].items():
    cur=collections.Counter(); tot=0; n=0; pips=collections.Counter(); lands=0; types=collections.Counter()
    for e in cards:
        c=C[e["name"].split(" // ")[0]]; tl=c["type_line"].split("//")[0]
        if "Land" in tl: lands+=e["count"]; continue
        if e["commander"]: continue
        m=mv(c); cur[min(m,7)]+=e["count"]; tot+=m*e["count"]; n+=e["count"]
        cost=c.get("mana_cost") or "".join(f.get("mana_cost","") for f in c.get("card_faces",[]))
        for s in re.findall(r"\{([^}]*)\}",cost):
            for col in "WUBRG":
                if col in s: pips[col]+=1
        for t in ("Creature","Artifact","Enchantment","Instant","Sorcery","Planeswalker"):
            if t in tl: types[t]+=e["count"]
    print(deck,"lands",lands,"nonland",n,"avgMV %.2f"%(tot/n),"curve",[cur[i] for i in range(8)],"pips",dict(pips),"types",dict(types))
