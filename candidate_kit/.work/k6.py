import sys, json
sys.path.insert(0,".")
import autodraft.pipeline as pl
r = pl.process_pdf("documents/DU-03.pdf")
def walk(o, p=""):
    if isinstance(o, dict):
        for k,v in o.items():
            if isinstance(v,(dict,list)) and k not in ("line_items","taxes","supplier","buyer","po"):
                walk(v, p+"/"+k)
            else:
                print(p+"/"+k, "=", str(v)[:120])
    elif isinstance(o, list):
        for i,v in enumerate(o[:3]):
            walk(v, p+"/[%d]"%i)
with open(".work/r3.json","w",encoding="utf-8") as fh: json.dump(r,fh,indent=1,default=str)
walk(r)
