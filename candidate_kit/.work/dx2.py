import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _extract_du_pages
extracts = _extract_du_pages("documents/DU-03.pdf")
for i, ext in enumerate(extracts):
    if i < 2: continue
    print("=== page", i, "inv=", ext.invoice_number, "gross=", ext.gross, "sub=", ext.subtotal, "tax_total=", ext.tax_total)
    txt = ext.page_text or ""
    print(txt[:1100])
