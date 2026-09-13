import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")
for f in ["INV-11","INV-13","INV-14","INV-16"]:
    exts = P._extract_doc("documents/%s.pdf"%f)
    if exts is None:
        print("==== %s: no extracts" % f)
        continue
    e = exts if not isinstance(exts, tuple) else exts[0]
    print("==== %s: gross=%r sub=%r tax=%r disc=%r fr=%r inv=%s %d items %d taxes" % (
        f, e.gross, e.subtotal, e.tax_total, e.discount_amount, e.freight_charges,
        e.invoice_number, len(e.line_items), len(e.taxes)))
    for li in e.line_items[:8]:
        print("    %-45r q=%r u=%r t=%r tx=%s" % (li.description[:45], li.quantity, li.unit_price, li.total, [(t.tax_rate,t.tax_amount) for t in li.taxes]))
    if e.taxes:
        print("    taxes:", [(t.tax_type,t.tax_rate,t.tax_amount) for t in e.taxes])
