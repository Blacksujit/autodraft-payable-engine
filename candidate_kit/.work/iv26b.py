import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import _render_page, WORK_DIR
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
from decimal import Decimal
pdf="documents/INV-26.pdf"
import pymupdf
d=pymupdf.open(pdf); n=len(d); d.close()
for pg in range(n): _render_page(pdf, pg)
total = Decimal(0)
for pg in range(n):
    pp = WORK_DIR / f"INV-26_p{pg+1}.png"
    layout = build_layout(str(pp), pg, ocr_words(str(pp)))
    ext = extract(layout)
    print(f"--- page {pg}: {len(ext.line_items)} lines")
    for li in ext.line_items:
        print("   ", repr(li.description), "qty=", li.quantity, "up=", li.unit_price, "tot=", li.total)
        try: total += Decimal(str(li.total).replace(",","."))
        except: pass
print("LINE SUM =", total)
