import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.audit import _extract_doc
from autodraft.oracle import build_payable
doc=_extract_doc(str(Path("documents")/"DU-03.pdf"))
print("doc.gross:", repr(doc.gross), "sub:", repr(doc.subtotal), "tax:", repr(doc.tax_total), "lines:", len(doc.line_items))
pt=(doc.page_text or "").replace("\n"," | ")
for probe in ["722.76","1040.06","TOTAL GST","Total Due","Invoice","Amount Due"]:
    idx=pt.find(probe)
    print(f"  probe {probe!r}: {'NO' if idx<0 else '...'+pt[max(0,idx-60):idx+40]!r}")
print("page_text head:", repr(pt[:120]))
