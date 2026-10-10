import re,sys,json
L=[l.rstrip("\r\n").replace(" "," ").strip() for l in open(sys.argv[1],encoding="utf-8-sig")]
eff=next(l for l in L if l.startswith("These rules are effective"))
g=[i for i,l in enumerate(L) if l=="Glossary"]; c=[i for i,l in enumerate(L) if l=="Credits"]
start=next(i for i in range(c[0]+1,len(L)) if L[i]=="1. Game Concepts")
body=L[start:g[1]]; gloss=L[g[1]+1:c[1]]
chapters=[];sections=[];rules=[]
for l in body:
    if not l: continue
    m=re.match(r"^(\d)\. (.+)$",l)
    if m: chapters.append({"n":m.group(1),"t":m.group(2)}); continue
    m=re.match(r"^(\d{3})\. (.+)$",l)
    if m: sections.append({"n":m.group(1),"t":m.group(2),"ch":chapters[-1]["n"]}); continue
    m=re.match(r"^(\d{3}\.\d+[a-z]?)\.? (.+)$",l)
    if m: rules.append({"n":m.group(1),"t":m.group(2)}); continue
    if rules: rules[-1]["t"]+="\n"+l
glos=[];cur=None
for l in gloss:
    if not l: cur=None; continue
    if cur is None: cur={"term":l,"def":""}; glos.append(cur)
    else: cur["def"]+=("\n" if cur["def"] else "")+l
json.dump({"effective":eff,"chapters":chapters,"sections":sections,"rules":rules,"glossary":glos},open(sys.argv[2],"w"),ensure_ascii=False,separators=(",",":"))
print(eff,len(chapters),len(sections),len(rules),len(glos))
r={x["n"]:x["t"] for x in rules}
for k in ["104.3a","302.6","608.2b","903.10a","704.5f","117.3b","603.8"]: print(k,"|",r.get(k,"MISSING")[:140])
print([s for s in sections if s["n"] in ("702","800","806","811","903")])
print(glos[0],glos[-1]["term"])
