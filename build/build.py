import sys,os
D=sys.argv[1]; t=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"template.html")).read()
rd=lambda p:open(os.path.join(D,p)).read()
sub={"__DATA__":rd("pagedata.json").replace("</","<\\/"),"__CR__":rd("cr/cr.json").replace("</","<\\/"),"__EDHREC__":rd("edhrec.json").replace("</","<\\/"),
"__DECKMETA__":rd("deckmeta.json").replace("</","<\\/"),"__SYMBOLS__":rd("symbols.json"),"__ART__":rd("art.json").replace("</","<\\/"),
"__PRECONS__":rd("bulk/precons.b64"),"__RELEASENOTES__":rd("bulk/releasenotes.b64"),"__JUDGES__":rd("bulk/judges.b64"),"__CARDDATE__":"October 10, 2026"}
for k,v in sub.items():
    assert k in t,k; t=t.replace(k,v)
open(sys.argv[2],"w").write(t); print(len(t)//1024,"KB")
