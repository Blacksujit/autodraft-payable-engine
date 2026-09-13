import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import process_pdf_detail
names = sys.argv[1:] or ["INV-04"]
for name in names:
    p = Path("documents")/(name+".pdf")
    print("="*78); print("##", name)
    r = process_pdf_detail(str(p))
    result = r[0]
    if not isinstance(result, dict) or result.get("error"):
        print("RESULT:", result); continue
    pays = result.get("payables") or []; decs = result.get("declined") or []
    print("payables:", len(pays), "declined:", len(decs))
    for d in decs: print("  DECLINED:", json.dumps(d, ensure_ascii=False))
    for pl in pays:
        print("  PAYABLE gross=%s inv=%s invdate=%s duedate=%s cur=%s type=%s sup=%s" % (pl.get("gross_total"), pl.get("invoice_number"), pl.get("invoice_date"), pl.get("due_date"), pl.get("currency"), pl.get("invoice_type"), (pl.get("supplier") or {}).get("name")))
    ext = r[1]
    if ext is not None:
        print("  gross=%r subtotal=%r tax_total=%r discount=%r freight=%r inv=%r invdate=%r duedate=%r cur=%r sup=%r" % (ext.gross, ext.subtotal, ext.tax_total, ext.discount_amount, ext.freight_charges, ext.invoice_number, ext.invoice_date, ext.due_date, ext.currency, ext.supplier_name))
        print("  doc_type=%r ground=%s" % (getattr(ext,'doc_type',None), json.dumps(ext.ground, ensure_ascii=False)[:260]))
        print("  taxes:", [(t.tax_type,t.tax_name,t.tax_rate,t.tax_amount) for t in ext.taxes])
        for i,li in enumerate(ext.line_items[:14]):
            print("    li[%d] %r qty=%r unit=%r total=%r rate=%r amt=%r" % (i, str(li.description)[:42], li.quantity, li.unit_price, li.total, li.tax_rate, li.tax_amount))
