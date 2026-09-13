import sys, os, traceback
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import process_pdf_detail
for name in ("INV-06","INV-03","INV-34","INV-10","INV-26","INV-13"):
    try:
        r = process_pdf_detail(f"documents/{name}.pdf")
    except Exception as e:
        print("ERR", name, e); continue
    res, ext = r[0], r[1]
    pays = res.get("payables") or []
    decs = res.get("declined") or []
    print("="*34, name)
    if decs:
        print("  DECLINED:", decs)
    for p in pays:
        print("  gross_total:", p.get("gross_total"), "| subtotal:", p.get("subtotal"), "| tax_total:", p.get("total_tax_amount"), "| disc:", p.get("discount_amount"))
        print("  taxes:", p.get("taxes"))
        for li in p.get("line_items") or []:
            print("   LI", repr(li.get("description"))[:45], "|q", li.get("quantity"), "|u", li.get("unit_price"), "|t", li.get("total"), "|v", li.get("tax_rate"), "|va", li.get("tax_amount"), "|tx", li.get("taxes"))
