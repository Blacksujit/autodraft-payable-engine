import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.structure import build_layout
from autodraft.ocr import ocr_words
w = ocr_words(r".work/pages/INV-06_p2.png")
lay = build_layout(r".work/pages/INV-06_p2.png", 1, w)
t = lay.table
for r in sorted(t.rows):
    print("R", r, [ (c,(t.cell(r,c) or "")) for c in sorted(t.rows[r]) ])
print("header_row=", t.header_row)
