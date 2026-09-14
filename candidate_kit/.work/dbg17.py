import sys, os, re
sys.path.insert(0, os.getcwd())
from autodraft.structure import build_layout
from autodraft.ocr import ocr_words
from autodraft.fields import extract
w = ocr_words(r".work/pages/INV-06_p1.png")
lay = build_layout(r".work/pages/INV-06_p1.png", 0, w)
print("HDR:", lay.header_text[:400].replace("\n"," | "))
print("TBL rows:")
for r in sorted(lay.table.rows if lay.table else []):
    cells=[lay.table.cell(r,c) for c in sorted(lay.table.rows[r])]
    print("  ", " | ".join((x or "").strip() for x in cells)[:160])
print("FTR:", lay.footer_text[:600].replace("\n"," | "))
