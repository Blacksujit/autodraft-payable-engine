import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
DOC=Path("documents"); WORK=Path(".work")/"pages"
name="INV-06"
import pymupdf
d=pymupdf.open(str(DOC/(name+".pdf"))); pc=len(d); d.close()
print("pages:",pc)
for pg in range(pc):
    pp=WORK/f"{name}_p{pg+1}.png"
    w=ocr_words(str(pp))
    lay=build_layout(str(pp), pg, w)
    e=extract(lay)
    gg=(e.ground or {}).get("gross")
    pt=(e.page_text or "").replace("\n"," | ")
    print(f"p{pg}: gross={e.gross!r} ground={gg!r} sub={e.subtotal!r} tax={e.tax_total!r} disc={e.discount_amount!r} lnx={len(pt)}")
    print("   head:", repr(pt[:110]))
    for probe in ["169.83","1683.98","1633.98","199.98","176.98","725.90","23.00","50.00"]:
        i=pt.find(probe.replace(",",""))
        if i>=0: print(f"     has {probe}: ...{pt[max(0,i-40):i+30]!r}")
