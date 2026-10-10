import sys,os,re,json,gzip,io,base64
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rn import text
SETS=[("innistrad-remastered","Innistrad Remastered","2025-01-24"),("aetherdrift","Aetherdrift","2025-02-14"),("tarkir-dragonstorm","Tarkir: Dragonstorm","2025-04-11"),("final-fantasy","Final Fantasy","2025-06-13"),("edge-of-eternities","Edge of Eternities","2025-08-01"),("spider-man","Marvel's Spider-Man","2025-09-26"),("avatar-the-last-airbender","Avatar: The Last Airbender","2025-11-21"),("lorwyn-eclipsed","Lorwyn Eclipsed","2026-01-23"),("teenage-mutant-ninja-turtles","Teenage Mutant Ninja Turtles","2026-03-06"),("secrets-of-strixhaven","Secrets of Strixhaven","2026-04-24"),("marvel-super-heroes","Marvel Super Heroes","2026-06-26"),("the-hobbit","The Hobbit","2026-08-14"),("reality-fracture","Reality Fracture","2026-10-02")]
out=[]
for slug,name,date in SETS:
    t=text(os.path.join(sys.argv[1],slug+".html"))
    i=t.find("## GENERAL NOTES")
    if i<0: i=t.upper().find("GENERAL NOTES\n")
    j=t.upper().find("CARD-SPECIFIC NOTES",i+20)
    body=t[i:j] if i>=0 and j>i else ""
    body=re.sub(r"## GENERAL NOTES\s*","",body).strip()
    # split into sections on headings
    secs=[];cur=None
    for line in body.split("\n"):
        if line.startswith("## "):
            cur={"title":line[3:].strip(),"text":""}; secs.append(cur)
        elif cur is not None: cur["text"]+=line+"\n"
        elif line.strip(): cur={"title":"Overview","text":line+"\n"}; secs.append(cur)
    secs=[{"title":s["title"],"text":re.sub(r"\n{3,}","\n\n",s["text"]).strip()} for s in secs if s["text"].strip()]
    out.append({"set":name,"date":date,"url":f"https://magic.wizards.com/en/news/feature/{slug}-release-notes","sections":secs})
    print(f"{name}: {len(body)//1024} KB, {len(secs)} sections: {[s['title'] for s in secs][:6]}")
raw=json.dumps(out,ensure_ascii=False,separators=(",",":")).encode()
buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode="wb",compresslevel=9,mtime=0) as g: g.write(raw)
open(sys.argv[2],"w").write(base64.b64encode(buf.getvalue()).decode())
print("total raw KB",len(raw)//1024,"gz KB",len(buf.getvalue())//1024)
