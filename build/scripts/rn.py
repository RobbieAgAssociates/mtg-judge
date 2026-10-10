import sys,re
from html.parser import HTMLParser
class P(HTMLParser):
    BLOCK={"p","div","li","h1","h2","h3","h4","h5","br","tr","section","article","ul","ol","blockquote"}
    def __init__(s): super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in("script","style","noscript","svg"): s.skip+=1
        if t in s.BLOCK: s.out.append("\n")
        if t=="li": s.out.append("• ")
        if t in("h1","h2","h3","h4"): s.out.append("## ")
    def handle_endtag(s,t):
        if t in("script","style","noscript","svg"): s.skip=max(0,s.skip-1)
        if t in s.BLOCK: s.out.append("\n")
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
def text(path):
    p=P(); p.feed(open(path,encoding="utf-8").read())
    t="".join(p.out); t=re.sub(r"[ \t ]+"," ",t); t=re.sub(r"\n\s*\n+","\n\n",t); return t
if __name__=="__main__":
    t=text(sys.argv[1])
    i=t.find("General Notes"); j=t.find("Card-Specific Notes",i+20)
    print(len(t),i,j); print(t[i:i+2500]); print("....."); print(t[j-600:j+100])
