import gzip,json,sys,collections,base64,io
SKIP={"token","double_faced_token","emblem","art_series","vanguard","scheme","planar","reversible_card"}
out=[];lay=collections.Counter()
for line in gzip.open(sys.argv[1],"rt",encoding="utf-8"):
    line=line.strip().rstrip(",")
    if not line or line in "[]": continue
    c=json.loads(line); lay[c.get("layout")]+=1
    if c.get("layout") in SKIP or c.get("set_type") in ("memorabilia","token","minigame"): continue
    if c.get("lang","en")!="en": continue
    faces=c.get("card_faces") if "oracle_text" not in c else None
    text=c.get("oracle_text","") if not faces else "\n—\n".join(f"{f['name']} {f.get('mana_cost','')}\n{f.get('type_line','')}\n{f.get('oracle_text','')}"+(f"\n{f['power']}/{f['toughness']}" if 'power' in f else "") for f in faces)
    stats=f"{c['power']}/{c['toughness']}" if "power" in c else (f"Loyalty {c['loyalty']}" if "loyalty" in c else (f"Defense {c['defense']}" if "defense" in c else ""))
    leg=c.get("legalities",{}).get("commander","")
    out.append([c["name"],c.get("mana_cost") or " // ".join(f.get("mana_cost","") for f in (c.get("card_faces") or [])),c.get("type_line",""),text,stats,{"legal":"L","banned":"B","not_legal":"N","restricted":"R"}.get(leg,"N")+("G" if c.get("game_changer") else "")])
out.sort(key=lambda x:x[0])
raw=json.dumps(out,ensure_ascii=False,separators=(",",":")).encode()
buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode="wb",compresslevel=9,mtime=0) as g: g.write(raw)
open(sys.argv[2],"w").write(base64.b64encode(buf.getvalue()).decode())
print("cards",len(out),"raw MB",round(len(raw)/1e6,1),"gz MB",round(len(buf.getvalue())/1e6,2),"b64 MB",round(len(buf.getvalue())*4/3/1e6,2))
print(lay.most_common(12))
names={x[0] for x in out}
for n in ["Lightning Bolt","Giant Growth","Sol Ring","Delver of Secrets // Insectile Aberration","Fire // Ice","Cyclonic Rift","Wear // Tear"]: print(n, n in names)
