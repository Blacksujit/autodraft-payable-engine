import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.structure import build_layout
from autodraft.ocr import ocr_words
import autodraft.fields as F
w = ocr_words(r".work/pages/INV-06_p1.png")
lay = build_layout(r".work/pages/INV-06_p1.png", 0, w)
doc = F.extract(lay)
print("gross=",doc.gross,"sub=",doc.subtotal,"tax=",doc.tax_total,"disc=",doc.discount_amount,"freight=",doc.freight_charges)
print("taxes:",[(t.tax_type,t.tax_name,t.tax_rate,t.tax_amount) for t in doc.taxes])
print("LIS:",[(li.description,li.quantity,li.unit_price,li.total) for li in doc.line_items])
p=doc.gross; print("ground gross?", doc.ground)
