import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _extract_du_pages, WORK_DIR
from pathlib import Path
extracts = _extract_du_pages("documents/DU-03.pdf")
print("num extracts:", len(extracts))
for i, ext in enumerate(extracts):
    print("=== page", i, "inv=", ext.invoice_number, "gross=", ext.gross, "sub=", ext.subtotal, "tax_total=", ext.tax_total, "freight=", ext.freight_charges)
    txt = ext.page_text or ""
    print(txt[:1500])
    print("---- lines:", len(ext.line_items))
