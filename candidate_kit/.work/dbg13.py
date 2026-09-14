import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.pipeline as P
doc, texts = P._extract_doc(str(Path("documents")/"INV-06.pdf"))
print("taxes:", [(t.tax_rate, t.tax_amount, t.tax_name) for t in doc.taxes])
print("tax_total:", doc.tax_total, "disc:", doc.discount_amount, "freight:", doc.freight_charges, "gross:", doc.gross, "ground:", repr(doc.ground))
txts=doc.txt or {}
for k,v in (txts.items() if isinstance(txts, dict) else []):
    if isinstance(v,str) and ("Sub-total" in v or "VAT" in v):
        print("==",k,"=="); print(v[:900]); break
