import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import process_pdf
from decimal import Decimal
def num(x):
    try: return float(x)
    except: return None
rows={}
for d in sorted(Path("documents").glob("*.pdf")):
    r = process_pdf(str(d))
    if r.get("error"):
        rows[d.stem]={"error": r["error"]}; continue
    ps=r.get("payables") or []
    ds=r.get("declined") or []
    entry={"payables":[], "declined":ds, "invoice_number":r.get("invoice_number","")}
    for p in ps:
        li=[[num(x.get("quantity")),num(x.get("unit_price")),num(x.get("total")),num(x.get("tax_rate")),num(x.get("tax_amount")),[ [num(t.get("tax_rate")),num(t.get("tax_amount"))] for t in x.get("taxes") or [] ]] for x in p.get("line_items") or []]
        entry["payables"].append({
          "gross":num(p.get("gross_total")), "subtotal":num(p.get("subtotal")), "tax_total":num(p.get("total_tax_amount")),
          "discount":num(p.get("discount_amount")), "taxes":[[num(t.get("tax_rate")),num(t.get("tax_amount"))] for t in p.get("taxes") or []],
          "line_items":li})
    rows[d.stem]=entry
json.dump(rows, open(".work/base_before.json","w"), indent=0, default=str)
ok=sum(1 for v in rows.values() if v["payables"])
dec=sum(1 for v in rows.values() if v["declined"] and not v["payables"])
err=sum(1 for v in rows.values() if "error" in v)
print("PASS",ok,"DECLINED",dec,"ERR",err,"of",len(rows))
for k,e in rows.items():
    if e["declined"] and not e["payables"]:
        print("DECLINED", k, e["declined"][0].get("reason","")[:80])
