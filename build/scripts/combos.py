import json,sys,os,urllib.request
S=json.load(open(sys.argv[1])); outdir=sys.argv[2]
for deck,cards in S["decks"].items():
    body={"commanders":[{"card":c["name"]} for c in cards if c["commander"]],
          "main":[{"card":c["name"],"quantity":c["count"]} for c in cards if not c["commander"]]}
    req=urllib.request.Request("https://backend.commanderspellbook.com/find-my-combos",data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"deck-analysis/1.0"})
    try:
        r=json.load(urllib.request.urlopen(req,timeout=60))
    except Exception as e:
        print(deck,"ERR",e, getattr(e,'read',lambda:b'')()[:300]); continue
    json.dump(r,open(os.path.join(outdir,deck.replace(" ","_")+"_combos.json"),"w"))
    res=r.get("results",r)
    print("=====",deck, {k:len(v) for k,v in res.items() if isinstance(v,list)})
    for v in res.get("included",[]):
        uses=" + ".join(u["card"]["name"] for u in v["uses"])
        req2="; ".join(t["template"]["name"] for t in v.get("requires",[]))
        prod=", ".join(p["feature"]["name"] for p in v["produces"])
        print(f"- {uses}{' [needs: '+req2+']' if req2 else ''} => {prod} | bracket:{v.get('bracketTag')}")
