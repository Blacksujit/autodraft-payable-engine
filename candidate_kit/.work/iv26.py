import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import _render_page
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
from autodraft.pipeline import WORK_DIR
import re
pdf = "documents/INV-26.pdf"
import pymupdf
d = pymupdf.open(pdf); n = len(d); d.close()
for pg in range(n):
    _render_page(pdf, pg)
txt_parts=[]
for pg in range(n):
    pp = WORK_DIR / f"INV-26_p{pg+1}.png"
    words = ocr_words(str(pp))
    layout = build_layout(str(pp), pg, words)
    ext = extract(layout)
    print(f"=== p{pg} gross={ext.gross} sub={ext.subtotal} inv={ext.invoice_number} inv_type={ext.invoice_type} nli={len(ext.line_items)} ftax={[ (t.tax_rate,t.tax_amount) for t in ext.taxes ]}")
    print("FOOTER:", (layout.footer_text or "")[:600])
    print("HEADER:", (layout.header_text or "")[:300])
    print("PAGE:", (ext.page_text or "")[:600].replace("\n"," | "))
    print()
