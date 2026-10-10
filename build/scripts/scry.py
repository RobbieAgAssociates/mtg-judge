import json,sys,os,time,urllib.request
d=sys.argv[1]
files=["EternalMight_DRC","LivingEnergy_DRC","CounterIntelligence_EOC","WorldShaper_EOC"]
decks={}
names=set()
for f in files:
    x=json.load(open(os.path.join(d,f+".json")))["data"]
    cards=[]
    for sec in ["commander","mainBoard"]:
        for c in x.get(sec) or []:
            cards.append({"name":c["name"],"count":c["count"],"commander":sec=="commander"})
            names.add(c["name"].split(" // ")[0])
    decks[x["name"]]=cards
names=sorted(names)
out={}
for i in range(0,len(names),75):
    body=json.dumps({"identifiers":[{"name":n} for n in names[i:i+75]]}).encode()
    req=urllib.request.Request("https://api.scryfall.com/cards/collection",data=body,headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"deck-analysis/1.0"})
    r=json.load(urllib.request.urlopen(req))
    for c in r["data"]:
        out[c["name"].split(" // ")[0]]=c
    if r.get("not_found"): print("NOT FOUND",r["not_found"])
    time.sleep(0.2)
json.dump({"decks":decks,"cards":out},open(os.path.join(d,"scry.json"),"w"))
print(len(names),len(out))
