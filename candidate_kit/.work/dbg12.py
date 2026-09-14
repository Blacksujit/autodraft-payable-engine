import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.pipeline as P
import autodraft.oracle as O
from decimal import Decimal
doc, texts = P._extract_doc(str(Path("documents")/"INV-06.pdf"))
print("doc.gross=",doc.gross,"sub=",doc.subtotal,"tax=",doc.tax_total,"disc=",doc.discount_amount,"freight=",doc.freight_charges)
print("line_items:",len(doc.line_items))
s=Decimal("0")
for li in doc.line_items:
    t=li.total
    d=Decimal(str(t)) if t else Decimal("0")
    s+=d
    print("   ",repr(li.description)[:45], "q=",li.quantity, "u=",li.unit_price, "t=",li.total, "tax=",li.tax_amount)
print("SUM line totals =", s)
orig_book=O._booked
def book(p):
    r=orig_book(p)
    net=Decimal("0")
    for li in p.get("line_items",[]):
        t=li.get("total")
        if t: net+=Decimal(str(t))
    print(f"   booked={r} net(li)={net} sub={p.get('subtotal')} tax={p.get('total_tax_amount')} disc={p.get('discount_amount')} fri={p.get('freight_charges')} gross={p.get('gross_total')} nli={len(p.get('line_items',[]))}")
    return r
O._booked=book
res=O.build_payable(doc)
print("RESULT:", res.get("_declined"), res.get("reason"))
