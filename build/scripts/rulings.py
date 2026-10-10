import gzip,json,sys,io,base64,collections
names={}
for line in gzip.open(sys.argv[1],"rt",encoding="utf-8"):
    line=line.strip().rstrip(",")
    if not line or line in "[]": continue
    c=json.loads(line)
    if c.get("oracle_id"): names.setdefault(c["oracle_id"],c["name"])
R=collections.defaultdict(list); n=0
for line in gzip.open(sys.argv[2],"rt",encoding="utf-8"):
    line=line.strip().rstrip(",")
    if not line or line in "[]": continue
    r=json.loads(line); nm=names.get(r.get("oracle_id"))
    if not nm: continue
    R[nm].append([r["published_at"],r["comment"],"W" if r.get("source")=="wotc" else "S"]); n+=1
for v in R.values(): v.sort()
raw=json.dumps(R,ensure_ascii=False,separators=(",",":")).encode()
buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode="wb",compresslevel=9,mtime=0) as g: g.write(raw)
open(sys.argv[3],"w").write(base64.b64encode(buf.getvalue()).decode())
print(n,"rulings for",len(R),"cards; raw MB",round(len(raw)/1e6,1),"gz MB",round(len(buf.getvalue())/1e6,2))
print("Kilo:",R.get("Kilo, Apogee Mind",[])[:1])
