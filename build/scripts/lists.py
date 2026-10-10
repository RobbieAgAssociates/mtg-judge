import json,sys,os
d=sys.argv[1]
for f in ["EternalMight_DRC","LivingEnergy_DRC","CounterIntelligence_EOC","WorldShaper_EOC"]:
    x=json.load(open(os.path.join(d,f+".json")))["data"]
    print("=====",x["name"])
    for sec in ["commander","displayCommander","mainBoard","sideBoard"]:
        cards=x.get(sec) or []
        if not cards: continue
        tot=sum(c["count"] for c in cards)
        print("--",sec,tot)
        for c in cards:
            print(c["count"],c["name"])
