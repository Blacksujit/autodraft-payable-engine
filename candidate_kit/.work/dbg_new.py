import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
DOC=Path("documents"); WORK=Path(".work")/"pages"
def dump(name):
    import pymupdf
    d=pymupdf.open(str(DOC/(name+".pdf"))); pc=len(d); d.close()
    for pg in range(pc):
        pp=WORK/f"{name}_p{pg+1}.png"
        w=ocr_words(str(pp))
        lay=build_layout(str(pp), pg, w)
        e=extract(lay)
        g=e.ground or {}
        def tail(t,n=300): return (t or "").replace("\n"," | ")[-n:]
        print(f"== {name} p{pg}: gross={e.gross!r} ground={g.get('gross')!r} sub={e.subtotal!r} tax={e.tax_total!r} disc={e.discount_amount!r}")
        print("   page_text tail:", tail(e.page_text, 260))
for n in ["DU-03","INV-06","INV-34","INV-13"]:
    dump(n)
