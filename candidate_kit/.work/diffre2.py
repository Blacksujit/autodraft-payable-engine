import json, pathlib
def load(d):
    out = {}
    for f in pathlib.Path(d).glob('*.json'):
        try:
            out[f.stem] = json.load(open(f, encoding='utf-8'))
        except Exception:
            pass
    return out
mine = load('.work/reout2')
base = load('.work/reout_nomine')
changed = []
for k in sorted(set(mine) & set(base)):
    def pays(o):
        return [(p.get('gross_total'), p.get('subtotal'), p.get('total_tax_amount'),
                 p.get('discount_amount'), p.get('invoice_number'),
                 [(li.get('quantity'), li.get('unit_price'), li.get('total'), li.get('discount'),
                   li.get('tax_rate'), li.get('tax_amount'),
                   [(t.get('tax_rate'), t.get('tax_amount')) for t in (li.get('taxes') or [])])
                  for li in (p.get('line_items') or [])]) for p in (o.get('payables') or [])]
    a, b = pays(mine[k]), pays(base[k])
    if a and b and a != b:
        changed.append(k)
    elif a != b:
        # one side had payables, other did not
        changed.append(k)
print('dirs with emit diff:', changed)
