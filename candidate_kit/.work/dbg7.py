import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.fields as F
import autodraft.pipeline as P

def fam(a):
    for n,v in F.__dict__.items():
        if isinstance(v,list) and len(v) and hasattr(v[0],"search") and v is a[1]:
            return n
    return "?"

log=[]
_orig_la=F._label_amount; _orig_lg=F._label_ground
def la(*a,**k):
    r=_orig_la(*a,**k)
    if not r: return r
    log.append((fam(a),len(a[0].splitlines()),repr(r)))
    return r
def lg(*a,**k):
    r=_orig_lg(*a,**k)
    log.append(("G:"+fam(a),len(a[0].splitlines()),repr(r)))
    return r
F._label_amount=la; F._label_ground=lg
for name in ["INV-06","DU-03"]:
    log.clear()
    ext, texts = P._extract_doc(str(Path("documents")/(name+".pdf")))
    print("=====", name, "=> gross=",repr(ext.gross)," sub=",repr(ext.subtotal)," tax=",repr(ext.tax_total)," disc=",repr(ext.discount_amount)," nlines=",len(ext.line_items))
    if texts:
        print("     p0head:", repr((texts[0] or "")[:80]))
    uniq=[]
    for x in log:
        if x not in uniq: uniq.append(x)
    for x in uniq[:50]: print("   ",x)
