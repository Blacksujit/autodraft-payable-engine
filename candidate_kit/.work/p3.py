import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
res, ext, raw, placement, note = process_pdf_detail("documents/DU-03.pdf")
print("placement=", placement)
print("note=", str(note)[:400])
print("=== EXT ===")
for k in ("invoice_number","invoice_date","supplier_name","currency","gross","subtotal","tax_total","discount_amount","freight_charges","duty_declaration_amount","line_items","taxes"):
    v = getattr(ext, k, None)
    print(" ", k, "=", v)
print("=== RAW keys ===", list(raw.keys()) if raw else None)
print("=== PAGE TEXT ===")
print(ext.page_text[:2000])
