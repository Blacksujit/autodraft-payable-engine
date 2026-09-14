import sys, os, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import process_pdf_detail
from autodraft.fields import LineItemExt
out=[]
for d in sorted(Path('documents').glob('*.pdf')):
    res = {}
    try:
        res, ext, raw, placement, note = process_pdf_detail(str(d))
    except Exception as e:
        out.append(f"{d.stem}: EXC {type(e).__name__} {e}")
        continue
    if 'error' in res:
        out.append(f"{d.stem}: ERROR {res['error']}")
        continue
    pay = res.get('payables') or []
    decl = res.get('declined') or []
    if pay:
        p = pay[0]
        taxes = json.dumps([{k:t.get(k) for k in ('tax_type','tax_name','tax_rate','tax_amount')} for t in p.get('taxes',[])], ensure_ascii=False)
        out.append(f"{d.stem}: PASS gt={p.get('gross_total')} sub={p.get('subtotal')} ttax={p.get('total_tax_amount')} place={placement} taxes={taxes} nli={len(p.get('line_items',[]))}")
    else:
        out.append(f"{d.stem}: DEC {decl[0].get('reason','')[:80] if decl else '?'}")
print("\n".join(out))
