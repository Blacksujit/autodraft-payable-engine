import sys, os
sys.path.insert(0, os.getcwd())
from decimal import Decimal
from autodraft.structure import build_layout
from autodraft.ocr import ocr_words
import autodraft.fields as F
w = ocr_words(r".work/pages/INV-06_p1.png")
lay = build_layout(r".work/pages/INV-06_p1.png", 0, w)
doc = F.extract(lay)
print("TAXES:", [(t.tax_type,t.tax_name,t.tax_rate,t.tax_amount) for t in doc.taxes])
print("LIS:", [(li.description, li.quantity, li.unit_price, li.total) for li in doc.line_items])
# replicate summary_rows_text
sr=[]
try:
    for r in sorted(lay.table.rows):
        cells=[lay.table.cell(r,c) for c in sorted(lay.table.rows[r])]
        numcells=[c for c in cells if c and any(ch.isdigit() for ch in c)]
        if len(numcells)>=2:
            desc=numbits=[x for x in numcells if any(ch.isalpha() for ch in x)]
            pass
except Exception as e:
    print("sumerr",e)
print("summary rows func out (via summary keyword):")
t=lay.table
rr=[]
for r in sorted(t.rows):
    rowcells=[t.cell(r,c) for c in sorted(t.rows[r])]
    rr.append(" | ".join((x or "").strip() for x in rowcells))
print("\n".join("  "+x for x in rr))
# manually build summary text the same way fields does (sub-total/delivery/total/vat labels)
import re
def summary_text():
    out=[]
    for r in sorted(t.rows):
        rowcells=[(t.cell(r,c) or "").strip() for c in sorted(t.rows[r])]
        num=[x for x in rowcells if re.search(r"\d",x)]
        if len(num)>=2:
            desc=" ".join(x for x in rowcells if not re.search(r"\d",x))
            moneys=[str(F._money_token(x)) for x in num if F._money_token(x) is not None]
            out.append((desc+" "+" ".join(moneys)).strip())
    return "\n".join(out)
st=summary_text()
print("=== summary_text ==="); print(st)
from decimal import Decimal as D
line_sum=sum((D(li.total or "0") for li in doc.line_items), D(0))
g={}
res=F._extract_totals(lay.header_text, lay.footer_text, line_sum, doc.taxes, g, st)
print("=== _extract_totals result:", res)
print("ground:", g)
