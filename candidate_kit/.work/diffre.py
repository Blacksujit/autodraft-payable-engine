import json, os, pathlib
def load(d):
    p = pathlib.Path(d)
    out = {}
    for f in p.glob('*.json'):
        try:
            out[f.stem] = json.load(open(f, encoding='utf-8'))
        except Exception:
            pass
    return out
mine = load('.work/reout2')
base = load('.work/reout_nomine')
changed = []
for k in sorted(set(mine) & set(base)):
    a, b = mine[k], base[k]
    def sig(o):
        if isinstance(o, dict):
            keep = ('payables','declined')
            return json.dumps({kk: o.get(kk) for kk in keep}, sort_keys=True)
        return json.dumps(o, sort_keys=True)
    # only compare gross/subtotal/tax/discount/line counts/taxes existence
    sa, sb = [], []
    for o in (a, b):
        s = []
        for p in (o.get('payables') or []):
            s.append((p.get('gross_total'), p.get('subtotal'), p.get('total_tax_amount'),
                      p.get('discount_amount'), len(p.get('line_items') or []),
                      [[ (li.get('total'), bool(li.get('taxes'))) for li in p.get('line_items') or [] ]]))
        sa.append(s)
    if sa != sb:
        changed.append((k, sa, sb))
print('docs whose payables changed:', [c[0] for c in changed])
