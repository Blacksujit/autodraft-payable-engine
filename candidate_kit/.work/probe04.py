import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
for name in ("INV-04", "INV-07"):
    res, ext, raw, placement, note = process_pdf_detail(f"documents/{name}.pdf")
    print("====", name, "placement=", placement, "note=", note)
    p = res.get("payables")[0] if res.get("payables") else (raw if raw and not raw.get("_declined") else None)
    if not p:
        print("  no payable")
        continue
    print("  header:", {k: p.get(k) for k in ("invoice_number","gross_total","subtotal","total_tax_amount","discount_amount","currency")})
    print("  header taxes:", p.get("taxes"))
    for i, li in enumerate(p.get("line_items") or []):
        print("  li", i, {k: li.get(k) for k in ("description","quantity","unit_price","total","tax_rate","tax_amount","taxes")})
