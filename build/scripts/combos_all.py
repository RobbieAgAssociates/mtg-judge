import json,sys,gzip,io,base64,collections
path,datapath,out=sys.argv[1],sys.argv[2],sys.argv[3]
mine=set()
S=json.load(open(datapath))
for cards in S["decks"].values():
    for c in cards: mine.add(c["name"])
dec=json.JSONDecoder()
f=open(path,encoding="utf-8"); buf=f.read(4_000_000)
i=buf.find('"variants"'); i=buf.find("[",i)+1
combos=[]; total=0; stats=collections.Counter(); desc_kept=0
def flush_ws(b,i):
    while i<len(b) and b[i] in " \r\n\t,": i+=1
    return i
while True:
    i=flush_ws(buf,i)
    if i>=len(buf)-2_000_000:
        more=f.read(8_000_000)
        if more: buf=buf[i:]+more; i=0; continue
    if i>=len(buf) or buf[i]=="]": break
    try: v,j=dec.raw_decode(buf,i)
    except json.JSONDecodeError:
        more=f.read(8_000_000)
        if not more: break
        buf=buf[i:]+more; i=0; continue
    i=j; total+=1
    if v.get("status")!="OK" or not (v.get("legalities") or {}).get("commander"): stats["notlegal"]+=1; continue
    names=[u["card"]["name"] for u in v["uses"]]
    if len(names)>4: stats["big"]+=1; continue
    prod=[p["feature"]["name"] for p in v.get("produces",[])][:4]
    req=[r["template"]["name"] for r in v.get("requires",[])]
    rec=[names,prod,v.get("bracketTag") or "",v.get("popularity") or 0,v.get("identity") or ""]
    if req: rec.append(req)
    else: rec.append([])
    if mine.intersection(names):
        rec.append((v.get("easyPrerequisites") or "")[:300]+"\n"+(v.get("notablePrerequisites") or "")[:300]+"\n"+(v.get("description") or "")[:1200]); desc_kept+=1
    combos.append(rec)
combos.sort(key=lambda r:-r[3])
raw=json.dumps(combos,ensure_ascii=False,separators=(",",":")).encode()
b=io.BytesIO()
with gzip.GzipFile(fileobj=b,mode="wb",compresslevel=9,mtime=0) as g: g.write(raw)
open(out,"w").write(base64.b64encode(b.getvalue()).decode())
print("total",total,"kept",len(combos),"with steps",desc_kept,dict(stats),"raw MB",round(len(raw)/1e6,1),"gz MB",round(len(b.getvalue())/1e6,2))
print(combos[0][:5])
