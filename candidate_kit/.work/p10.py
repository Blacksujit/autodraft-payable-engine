import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
res, ext, raw, placement, note = process_pdf_detail("documents/INV-10.pdf")
print("placement=", placement, "note=", note)
print("=== EXT FIELDS ===")
for k in ("invoice_number","invoice_date","due_date","supplier_name","currency","gross","subtotal","tax_total","discount_amount","freight_charges","tax_rate","tax_amount","line_items","taxes"):
    print(" ", k, "=", getattr(ext, k, None))
print("=== RAW ===")
print(str(raw)[:1200])
print("=== DECLINE ===")
for d in res.get("declined", []):
    print(d.get("reason"))
