import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
import autodraft.oracle as O
ext = P._extract_doc("documents/INV-06.pdf") if False else None

from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
import autodraft.fields as F
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")
exts = []
for pg in range(2):
    P._render_page("documents/INV-06.pdf", pg)
    words = ocr_words(".work/pages/INV-06_p%d.png" % (pg+1))
    layout = build_layout(".work/pages/INV-06_p%d.png" % (pg+1), pg, words)
    e = F.extract(layout)
    exts.append(e)
    print("== p%d gross=%s sub=%s tax=%s fr=%s %s items" % (pg+1, e.gross, e.subtotal, e.tax_total, e.freight_charges, len(e.line_items)))
    for li in e.line_items:
        print("   %-45r q=%-10r u=%-12r t=%-12r taxes=%s" % (li.description[:45], li.quantity, li.unit_price, li.total, [(t.tax_rate, t.tax_amount) for t in li.taxes]))
