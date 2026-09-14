import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract, _SUBTOTAL_MASK, _BAL_LABELS, _STRONG_TOTAL_LABELS, _GROSS_LABELS
DOC=Path("documents"); WORK=Path(".work")/"pages"
import pymupdf
def show(name):
    d=pymupdf.open(str(DOC/(name+".pdf"))); pc=len(d); d.close()
    for pg in range(pc):
        pp=WORK/f"{name}_p{pg+1}.png"
        w=ocr_words(str(pp))
        lay=build_layout(str(pp), pg, w)
        hdr=lay.header_text or ""; ftr=lay.footer_text or ""
        txt="\n".join(x for x in (hdr,ftr) if x)
        poor=_SUBTOTAL_MASK.sub(" ",txt)
        print(f"== {name} p{pg}: hdr={hdr[:50]!r} ftr={ftr[:50]!r}")
        for lab,pat in [("BAL",_BAL_LABELS),("STRONG",_STRONG_TOTAL_LABELS),("GROSS",_GROSS_LABELS)]:
            for ln in txt.splitlines():
                for p in pat:
                    for m in p.finditer(ln.lower()):
                        print(f"    [{lab}] {ln[:160]!r}  (mtail={ln[m.end():m.end()+40]!r})")
a=list(sys.argv[1:]) or ["DU-03"]
for n in a: show(n)
