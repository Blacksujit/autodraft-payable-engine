import sys, os, json
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
from autodraft.audit import _extract_doc, _extract_page_numbers
from decimal import Decimal
pdf="documents/INV-06.pdf"
res, ext, raw, placement, note = process_pdf_detail(pdf)
p = (res.get("payables") or [{}])[0]
for k in ("gross_total","subtotal","total_tax_amount","discount_amount","freight_charges","insurance_charges","extra_charges","excise_duties"):
    print(k, "=", p.get(k))
for t in p.get("taxes",[]): print("TAX", json.dumps(t,ensure_ascii=False))
for i,li in enumerate(p.get("line_items",[])):
    print("LI",i, json.dumps(li,ensure_ascii=False))
doc = _extract_doc(pdf)
print("AUDIT page_text page:\n", (doc.page_text or "")[:3500])
nums = sorted(_extract_page_numbers(doc.page_text or ""))
print("NUMBERS:", [str(n) for n in nums])
