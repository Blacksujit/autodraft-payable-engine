import sys, os, json
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
import autodraft.oracle as O
import erp as ERP
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")

for f in ["INV-11","INV-14","INV-16"]:
    exts = P._extract_doc("documents/%s.pdf"%f)
    e = exts if not isinstance(exts, tuple) else exts[0]
    print("==== %s: gross=%r" % (f, e.gross))
    print("  items:", len(e.line_items), "taxes:", len(e.taxes))
    p = O._variant_keep(e)
    try:
        r = ERP.erp_book(p)
        print("  keep: will_book=%s items=%d" % (r["will_book_gross"], len(p["line_items"])))
    except Exception as ex:
        print("  keep: ERROR", ex)
    for li in p["line_items"][:5]:
        print("    li:", dict(li))
    if p.get("taxes"):
        print("    taxes:", p["taxes"])
    print()
