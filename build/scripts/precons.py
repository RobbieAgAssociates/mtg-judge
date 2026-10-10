import json,sys,os,glob,gzip,base64,io,collections
out=[]
for f in sorted(glob.glob(os.path.join(sys.argv[1],"*.json"))):
    x=json.load(open(f))["data"]
    cnt=collections.OrderedDict(); cmd=[]
    for sec in ("commander","mainBoard"):
        for c in x.get(sec) or []:
            if sec=="commander": cmd.append(c["name"])
            cnt[c["name"]]=cnt.get(c["name"],0)+c["count"]
    disp=[c["name"] for c in (x.get("displayCommander") or [])]
    out.append({"name":x["name"],"code":x["code"],"date":x["releaseDate"],"commander":cmd or disp,"cards":[[n,k] if n!=1 else k for k,n in cnt.items()]})
out.sort(key=lambda d:d["date"],reverse=True)
raw=json.dumps(out,ensure_ascii=False,separators=(",",":")).encode()
buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode="wb",compresslevel=9,mtime=0) as g: g.write(raw)
open(sys.argv[2],"w").write(base64.b64encode(buf.getvalue()).decode())
print(len(out),"decks raw KB",len(raw)//1024,"gz KB",len(buf.getvalue())//1024)
print([ (d["name"],d["commander"],sum(c[0] if isinstance(c,list) else 1 for c in d["cards"])) for d in out[:4]])
bad=[(d["name"],sum(c[0] if isinstance(c,list) else 1 for c in d["cards"])) for d in out if sum(c[0] if isinstance(c,list) else 1 for c in d["cards"])!=100]
print("not 100:",len(bad),bad[:8])
