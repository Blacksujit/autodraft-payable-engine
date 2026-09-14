import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _extract_doc
ext, texts = _extract_doc("documents/INV-06.pdf")
print("ground:", ext.ground)
print("fields: gross=%r sub=%r tax=%r disc=%r freight=%r" % (ext.gross, ext.subtotal, ext.tax_total, ext.discount_amount, ext.freight_charges))
print("page_text(first 400):", (ext.page_text or "")[:400])
print("n lines:", len(ext.line_items))
print("taxes:", [(t.tax_type,t.tax_rate,t.tax_amount) for t in ext.taxes])
s = sum(float(li.total or 0) for li in ext.line_items)
print("line sum:", round(s,2), "n lines total set:", sum(1 for li in ext.line_items if li.total))
