import json, glob, os, sys
sys.path.insert(0, "."); sys.path.insert(0, os.path.join("autodraft", "autodraft"))
from autodraft.oracle import build_payable, oracle_gate
from erp import erp_book
for f in sorted(glob.glob("output/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    for i, p in enumerate(d.get("payables") or []):
        r = erp_book(p)
        g = p.get("gross_total"); gd = None
        try: gd = float(g)
        except Exception: pass
        diff = None if gd is None else round(r["will_book_gross"] - gd, 2)
        bad = [ (t.get("tax_rate"), t.get("tax_amount"), t.get("tax_type")) for t in (p.get("taxes") or []) if (t.get("tax_rate") or "") and not (t.get("tax_amount") or "") ]
        lines_rate_amt = [li.get("description","") for li in (p.get("line_items") or []) for t in (li.get("taxes") or []) if (t.get("tax_rate") or "") and not (t.get("tax_amount") or "")]
        print(f'{os.path.basename(f):<10} {i:<2} erp={r["will_book_gross"]:>10.2f} printed={gd if gd is None else f"{gd:>8.2f}"} {"OK" if (diff is None or abs(diff)<0.005) else f"MISMATCH {diff:+}":<13} hdr_rate-only-taxes={bad} lines_rate-noamt={lines_rate_amt if lines_rate_amt else ""}')
