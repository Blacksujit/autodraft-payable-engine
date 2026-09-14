import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
DOC=Path("documents"); WORK=Path(".work")/"pages"
name="DU-03"
import pymupdf
d=pymupdf.open(str(DOC/(name+".pdf"))); pc=len(d); d.close()
for pg in range(pc):
    pp=WORK/f"{name}_p{pg+1}.png"
    w=ocr_words(str(pp))
    lay=build_layout(str(pp), pg, w)
    e=extract(lay)
    gg=(e.ground or {}).get("gross")
    pt=(e.page_text or "").replace("\n"," | ")
    idx=pt.rfind("722")
    ctx=pt[max(0,idx-70):idx+30] if idx>=0 else ""
    print(f"p{pg}: gross={e.gross!r} ground={gg!r} sub={e.subtotal!r} has722={idx>=0} ctx=...{ctx!r}")
