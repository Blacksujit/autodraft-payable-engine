import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.audit import audit_file
from erp import erp_book
for name in ["DU-03","INV-06","INV-13","INV-34"]:
    pdf=Path("documents")/(name+".pdf")
    out=Path("output")/(name+".json")
    r=audit_file(str(pdf), str(out))
    print("###", name, "status", r["status"])
    for i in r["issues"][:12]:
        print("   issue:", i)
    if out.exists():
        d=json.load(open(out, encoding="utf-8"))
        for p in (d.get("payables") or [])[:2]:
            if p.get("_declined"):
                print("   DECLINED:", p.get("reason"))
                continue
            for k in ("gross_total","subtotal","total_tax_amount","discount_amount","freight_charges","_placement","_declined","reason"):
                if k in p: print(f"   {k}={p[k]!r}")
            print("   n_lines:", len(p.get("line_items") or []), "sum:", p.get("_line_sum") or (lambda s: sum(float(x.get("total") or 0) for x in s))(p.get("line_items") or []))
