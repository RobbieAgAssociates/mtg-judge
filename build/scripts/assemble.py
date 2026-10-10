import json,sys,os,collections
S=json.load(open(sys.argv[1])); an=sys.argv[2]; out=sys.argv[3]; C=S["cards"]
meta={"Eternal Might":("Aetherdrift Commander (DRC)","2025-02-14","https://magic.wizards.com/en/news/announcements/aetherdrift-commander-decklists"),
"Living Energy":("Aetherdrift Commander (DRC)","2025-02-14","https://magic.wizards.com/en/news/announcements/aetherdrift-commander-decklists"),
"Counter Intelligence":("Edge of Eternities Commander (EOC)","2025-08-01","https://magic.wizards.com/en/news/announcements/edge-of-eternities-commander-decklists"),
"World Shaper":("Edge of Eternities Commander (EOC)","2025-08-01","https://magic.wizards.com/en/news/announcements/edge-of-eternities-commander-decklists")}
order=["Creature","Planeswalker","Instant","Sorcery","Artifact","Enchantment","Land"]
for deck,cards in S["decks"].items():
    cmd=[e for e in cards if e["commander"]][0]["name"]
    groups=collections.OrderedDict((k,collections.Counter()) for k in order)
    for e in cards:
        if e["commander"]: continue
        tl=C[e["name"].split(" // ")[0]]["type_line"].split("//")[0]
        g=next(k for k in order if k in tl)
        groups[g][e["name"]]+=e["count"]
    lines=[f"# {deck} (Commander deck)","",
        f"- Commander: {cmd}",f"- Product: {meta[deck][0]}, released {meta[deck][1]}",
        f"- Official decklist: {meta[deck][2]}",
        "- Status: unmodified precon. Update this file if the user swaps cards.",
        "- Analyzed: 2026-10-10 (Scryfall Oracle text, Commander Spellbook combos)",""]
    lines.append(open(os.path.join(an,deck.replace(" ","_")+".txt")).read().rstrip())
    lines+=["","## Decklist (100 cards)","",f"Commander (1): {cmd}"]
    for g,cnt in groups.items():
        if not cnt: continue
        lines+=["",f"{g} ({sum(cnt.values())}):"]
        lines+=[f"{n} {k}" for k,n in sorted(cnt.items())]
    fn=os.path.join(out,deck.lower().replace(" ","-")+".txt")
    open(fn,"w").write("\n".join(lines)+"\n"); print(fn, sum(e["count"] for e in cards))
