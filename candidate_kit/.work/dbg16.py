import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.pipeline as P
doc, texts = P._extract_doc(str(Path("documents")/"DU-03.pdf"))
print("PIPELINE doc: gross=",doc.gross,"sub=",doc.subtotal,"tax=",doc.tax_total,"disc=",doc.discount_amount,"fri=",doc.freight_charges)
print("ground:", doc.ground)
print("N pages texts:", len(texts))
for i,t in enumerate(texts):
    hits=[]
    for kw in ("GST","total","Total","Total","amount","Amount","AMT","TOTAL"):
        pass
    lines=[ln for ln in t.splitlines() if any(k in ln for k in ("GST","Total","AMT","778252","Invoice","invoice"))]
    if lines:
        print(f"-- p{i} --")
        for ln in lines[:6]: print("   ",ln[:150])
