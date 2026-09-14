import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.fields as F
import autodraft.pipeline as P
class Tap:
    def __init__(self): self.log=[]
    def __call__(self,*a,**k):
        r=F._label_amount_orig(*a,**k)
        pat=a[1] if len(a)>1 else k.get("labels")
        fam="?"
        for n,v in F.__dict__.items():
            if isinstance(v,list) and len(v) and hasattr(v[0],"search") and v is pat: fam=n
        txt=a[0] if len(a)>0 else k.get("text","")
        lines=txt.splitlines()
        mark = "***HIT***" if r else ""
        # record the first 3 lines only for brevity
        self.log.append((fam, len(lines), repr(r), mark, [repr(x[:90]) for x in lines[:4]]))
        return r
F._label_amount_orig=F._label_amount
tap=Tap(); F._label_amount=tap
inv,txt=P._extract_doc(str(Path("documents")/"INV-06.pdf"))
print("RESULT gross=",repr(inv.gross),"sub=",repr(inv.subtotal),"tax=",repr(inv.tax_total))
seen=set()
for x in tap.log:
    key=(x[0],x[1],x[2],x[4][0] if x[4] else "")
    if key in seen: continue
    seen.add(key)
    if x[3] or x[0] in ("_STRONG_TOTAL_LABELS","_BAL_LABELS"):
        print("  CALL", x[0], "nlines=",x[1], "res=",x[2], x[3])
        for ln in x[4]: print("       ", ln)
