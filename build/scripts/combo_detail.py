import json,sys,os,glob
for f in sorted(glob.glob(os.path.join(sys.argv[1],"*_combos.json"))):
    r=json.load(open(f))["results"]; print("=====",os.path.basename(f))
    for v in r["included"]:
        print("## "+" + ".join(u["card"]["name"] for u in v["uses"]))
        for k in ("easyPrerequisites","notablePrerequisites","manaNeeded","description"):
            if v.get(k): print(f"  {k}: "+v[k].replace("\n"," | "))
    print("-- almost (1 card away), excluding infinite-irrelevant:")
    for v in r["almostIncluded"][:60]:
        names=[u["card"]["name"] for u in v["uses"]]
        prod=", ".join(p["feature"]["name"] for p in v["produces"][:3])
        print("  * "+" + ".join(names)+" => "+prod)
