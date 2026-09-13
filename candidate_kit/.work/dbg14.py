import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
import autodraft.fields as F
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")

P._render_page('documents/INV-14.pdf', 0)
words = ocr_words(str(P.WORK_DIR/'INV-14_p1.png'))
lay = build_layout(str(P.WORK_DIR/'INV-14_p1.png'), 0, words)
g = {}
from autodraft.fields import assign_roles, _is_summary_row, _is_tax_label, _split_qty_uom, _money_token
tb = lay.table
roles = assign_roles(tb)
print("roles:", roles)
for r in sorted(tb.rows):
    if r == tb.header_row: continue
    desc = tb.cell(r, tb.DESCR)
    q = tb.cell(r, roles["qty"]) if roles["qty"]>=0 else ""
    u = tb.cell(r, roles["unit"]) if roles["unit"]>=0 else ""
    t = tb.cell(r, roles["total"]) if roles["total"]>=0 else ""
    d = tb.cell(r, roles["discount"]) if roles["discount"]>=0 else ""
    print("row %d desc=%r q=%r u=%r t=%r d=%r"%(r, desc, q,u,t,d))
    print("   is_summary:", _is_summary_row(desc,q,u,t), " is_tax:", _is_tax_label(desc))
    print("   money qty:", _split_qty_uom(q), " unit:", _money_token(u) if u else None, " total:", _money_token(t) if t else None)