import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import process_pdf_detail
from autodraft.pipeline import _render_page, WORK_DIR
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.fields import extract
import pymupdf

def dump(doc):
    res, ext, raw, placement, note = process_pdf_detail("documents/"+doc+".pdf")
    p = (res.get("payables") or [{}])[0]
    print("="*30, doc, "placement=", placement)
    if p:
        print(" gross=", p.get("gross_total"), "sub=", p.get("subtotal"), "ttax=", p.get("total_tax_amount"), "disc=", p.get("discount_amount"))
        for t in p.get("taxes",[]):
            print("   TAX", json.dumps(t, ensure_ascii=False))
        for i, li in enumerate(p.get("line_items",[])):
            print("   LI", i, json.dumps(li, ensure_ascii=False))
    d = pymupdf.open("documents/"+doc+".pdf"); n=len(d); d.close()
    for pg in range(n):
        _render_page("documents/"+doc+".pdf", pg)
        pp = WORK_DIR / f"{doc}_p{pg+1}.png"
        ext = extract(build_layout(str(pp), pg, ocr_words(str(pp))))
        print(f"  --p{pg} gross={ext.gross} sub={ext.subtotal} tax={ext.tax_total} disc={ext.discount_amount}")
        print("   footer:", (ext.page_text or "")[:700].replace("\n"," | "))
    print()

for d in ["INV-34","INV-03"]:
    dump(d)
