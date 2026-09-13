import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
for name in ("INV-16","INV-34",):
    for i in (1,2,3):
        p=f".work/pages/{name}_p{i}.png"
        if not os.path.exists(p): continue
        w = ocr_words(p)
        lay = build_layout(p,0,w)
        t = lay.table
        if not t: continue
        print("=====", name, "p"+str(i), "cols:", [(c.index, round(c.center,1)) for c in t.columns], "money:", t.money_cols, "hdr:", t.header_row)
        for r in sorted(t.rows):
            print("   r",r,"DESCR=",repr(t.cell(r,-1))[:60], "|", " | ".join(f"c{c.index}={t.cell(r,c.index)!r}" for c in t.columns if t.cell(r,c.index)))
