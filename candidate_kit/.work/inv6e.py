import sys, os, json
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
r = process_pdf_detail("documents/INV-06.pdf")
result, ext, raw, placement, note = r
print("RESULT keys:", list(result.keys()))
print("invoice_number:", result.get("invoice_number"))
print("--- result payables ---")
import pprint
pprint.pprint({k:v for k,v in result.items() if k not in ("line_items","taxes")})
print("gross:", result.get("gross_total"), "sub:", result.get("subtotal"), "tax:", result.get("total_tax_amount"), "disc:", result.get("discount_amount"), "freight:", result.get("freight_charges"))
print("placement:", placement, "note:", note)
print("EXT ground:", ext.ground)
print("EXT doc fields: gross=", ext.gross, "sub=", ext.subtotal, "tax=", ext.tax_total, "disc=", ext.discount_amount, "freight=", ext.freight_charges, "inv=", ext.invoice_number)
print("n lines:", len(ext.line_items))
print("taxes:", [(t.tax_type,t.tax_rate,t.tax_amount) for t in ext.taxes])
