import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.fields as F
orig=F._extract_totals
def tap(*a,**k):
    r=orig(*a,**k)
    gt,st,tt,dc,fr=r
    if any(x for x in (gt,st,tt,dc,fr)):
        print("EXTRACT_TOTALS -> gross=",repr(gt),"sub=",repr(st),"tax=",repr(tt),"disc=",repr(dc),"freight=",repr(fr))
        txt=a[1] or a[0] if False else (a[1] or a[0])
        print("   txt(first 300):", repr((a[0] or a[1] or "")[:300]))
        print("   footer(first 300):", repr((a[1] or "")[:300]))
        print("   line_sum=",a[2], "taxes=",[ (t.tax_amount,t.tax_rate,t.tax_rate) for t in a[3]])
    return r
F._extract_totals=tap
import autodraft.pipeline as P
P._extract_doc(str(Path("documents")/"INV-06.pdf"))
