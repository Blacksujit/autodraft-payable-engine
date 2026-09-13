import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.fields import _extract_taxes
from autodraft.pipeline import process_pdf_detail
res, ext, raw, placement, note = process_pdf_detail("documents/INV-10.pdf")
items, total = _extract_taxes("", ext.page_text, {})
print("total=", total)
for t in items:
    print(t.tax_name, repr(t.tax_rate), repr(t.tax_amount))
