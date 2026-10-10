import json,sys,os,re,html
S=json.load(open(sys.argv[1])); deckdir=sys.argv[2]; out=sys.argv[3]; C=S["cards"]
def inline(t):
    t=html.escape(t,quote=False)
    t=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",t)
    t=re.sub(r"`([^`]+)`",r"<code>\1</code>",t)
    t=re.sub(r"(?<![\w*])\*([^*]+)\*(?!\*)",r"<em>\1</em>",t)
    t=re.sub(r"(https?://[^\s)<]+)",r'<a href="\1" target="_blank" rel="noopener">\1</a>',t)
    return t
def md(lines):
    o=[];i=0;stack=[]
    def close(to=0):
        while len(stack)>to: o.append("</li></ul>"); stack.pop()
    while i<len(lines):
        l=lines[i]
        if not l.strip(): close(); i+=1; continue
        if l.startswith("|"):
            close(); rows=[]
            while i<len(lines) and lines[i].startswith("|"):
                cells=[c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c)<=set("-: ") for c in cells): rows.append(cells)
                i+=1
            o.append('<div class="tablewrap"><table><thead><tr>'+"".join(f"<th>{inline(c)}</th>" for c in rows[0])+"</tr></thead><tbody>"+
                "".join("<tr>"+"".join(f"<td>{inline(c)}</td>" for c in r)+"</tr>" for r in rows[1:])+"</tbody></table></div>"); continue
        m=re.match(r"^( *)- (.*)",l)
        if m:
            depth=len(m.group(1))//2+1
            if depth>len(stack):
                while len(stack)<depth: o.append("<ul><li>"); stack.append(1)
            else:
                close(depth); o.append("</li><li>")
            o.append(inline(m.group(2))); i+=1; continue
        close(); o.append(f"<p>{inline(l.strip())}</p>"); i+=1
    close(); return "".join(o).replace("<ul><li></li><li>","<ul><li>")
def sections(text):
    secs=[];cur=None
    for l in text.splitlines():
        if l.startswith("## "):
            cur={"title":l[3:].strip(),"lines":[]}; secs.append(cur)
        elif cur is not None: cur["lines"].append(l)
    return [{"title":s["title"],"html":md(s["lines"])} for s in secs if not s["title"].startswith("Decklist")]
def mvf(c):
    if c.get("layout") in ("split","adventure") and "card_faces" in c:
        n=0
        for s in re.findall(r"\{([^}]*)\}",c["card_faces"][0]["mana_cost"]): n+= int(s) if s.isdigit() else (0 if s=="X" else 1)
        return n
    return int(c.get("cmc",0))
def oracle(c):
    if "card_faces" in c and "oracle_text" not in c:
        return "\n\n".join(f"{f['name']} {f.get('mana_cost','')}\n{f['type_line']}\n{f.get('oracle_text','')}" for f in c["card_faces"])
    return c.get("oracle_text","")
meta={"Eternal Might":("eternal-might","Aetherdrift Commander","2025"),"Living Energy":("living-energy","Aetherdrift Commander","2025"),
"Counter Intelligence":("counter-intelligence","Edge of Eternities Commander","2025"),"World Shaper":("world-shaper","Edge of Eternities Commander","2025")}
order=["Creature","Planeswalker","Instant","Sorcery","Artifact","Enchantment","Land"]
decks=[]
for name,cards in S["decks"].items():
    slug,setname,yr=meta[name]
    txt=open(os.path.join(deckdir,slug+".txt")).read()
    agg={}
    for e in cards:
        k=e["name"]
        if k in agg: agg[k]["count"]+=e["count"]; continue
        c=C[k.split(" // ")[0]]; tl=c["type_line"]
        agg[k]={"name":k,"count":e["count"],"commander":e["commander"],"type":tl,"group":next(g for g in order if g in tl.split("//")[0]),
            "cost":c.get("mana_cost") or " // ".join(f.get("mana_cost","") for f in c.get("card_faces",[])),
            "text":oracle(c),"pt":f"{c['power']}/{c['toughness']}" if "power" in c else "","url":c["scryfall_uri"].split("?")[0],
            "mv":mvf(c),"img":"img/"+re.sub(r"[^a-z0-9]+","-",c["name"].lower()).strip("-")+".jpg"}
    cmd=[v for v in agg.values() if v["commander"]][0]
    decks.append({"id":slug,"name":name,"set":setname,"commander":cmd["name"],"art":"img/"+re.sub(r"[^a-z0-9]+","-",cmd["name"].lower()).strip("-")+"-art.jpg","colors":"".join(C[cmd["name"]]["color_identity"]),
        "sections":sections(txt),"cards":list(agg.values())})
comp=open(os.path.join(deckdir,"comparison.txt")).read()
compsecs=[{"title":"Overview","html":md(comp.split("\n## ")[0].splitlines()[1:])}]+sections(comp)
json.dump({"decks":decks,"comparison":compsecs},open(out,"w"),ensure_ascii=False)
print(os.path.getsize(out))
