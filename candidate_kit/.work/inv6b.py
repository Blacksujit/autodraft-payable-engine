import sys, os, json
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
from autodraft.audit import _extract_doc, _extract_page_numbers
pdf="documents/INV-06.pdf"
res, ext, raw, placement, note = process_pdf_detail(pdf)
p = (res.get("payables") or [{}])[0]
lines=[]
for i,li in enumerate(p.get("line_items",[])):
    lines.append(f"LI {i}: {json.dumps(li,ensure_ascii=False)}")
open(".work/inv6_lines.txt","w",encoding="utf-8").write("\n".join(lines))
doc = _extract_doc(pdf)
open(".work/inv6_pagetext.txt","w",encoding="utf-8").write(doc.page_text or "")
print("nli=", len(p.get("line_items",[])))
print("placement=", placement, "note=", note)
print("gross=", p.get("gross_total"), "sub=", p.get("subtotal"), "ttax=", p.get("total_tax_amount"), "disc=", p.get("discount_amount"))
for t in p.get("taxes",[]): print("TAX", json.dumps(t,ensure_ascii=False))
