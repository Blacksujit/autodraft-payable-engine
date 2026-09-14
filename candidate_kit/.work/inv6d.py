import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _render_page, WORK_DIR
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
import pymupdf
pdf="documents/INV-06.pdf"
d=pymupdf.open(pdf); n=len(d); d.close()
for pg in range(n):
    _render_page(pdf, pg)
    pp = WORK_DIR / f"INV-06_p{pg+1}.png"
    lay = build_layout(str(pp), pg, ocr_words(str(pp)))
    ext = extract(lay)
    print(f"=== page {pg}: gross={ext.gross} sub={ext.subtotal} tax={ext.tax_total} disc={ext.discount_amount} nli={len(ext.line_items)}")
    print("  TEXT:", (ext.page_text or "")[:1700].replace("\n"," | "))
    print()
