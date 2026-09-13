import sys
sys.path.insert(0,".")
import autodraft.pipeline as pl
import erp
from pathlib import Path
files = ["DU-03","INV-06","INV-14","INV-15","INV-34"]
for f in files:
    r, ext, raw, _, _ = pl.process_pdf_detail("documents/%s.pdf"%f)
    print("="*60, f)
    if not raw:
        print(r)
        continue
    keys = ["invoice_number","gross_total","subtotal","total_tax_amount","freight_charges","discount_amount","excise_duties","extra_charges","insurance_charges","currency","payment_term_id","duty_declaration_amount"]
    for k in keys:
        v = raw.get(k,"")
        if v: print(k, "=", v)
    print("lines:", len(raw.get("line_items",[])), "taxes:", len(raw.get("taxes",[])))
    print("erp_book:", erp.erp_book(raw))
