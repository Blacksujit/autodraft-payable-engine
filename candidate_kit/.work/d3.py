import json
def dump(d, name):
    o = json.load(open(f'{d}/{name}.json', encoding='utf-8'))
    p = (o.get('payables') or [None])[0]
    print('---', d, name, 'payables?', len(o.get('payables') or []))
    if p:
        for k in ('invoice_number','gross_total','subtotal','total_tax_amount','discount_amount'):
            print('   ', k, repr(p.get(k)))
        print('   taxes:', p.get('taxes'))
        for i, li in enumerate(p.get('line_items') or []):
            print('   li', i, {k: li.get(k) for k in ('quantity','unit_price','total','discount','tax_rate','tax_amount','taxes')})
dump('.work/reout_nomine', 'INV-03')
dump('.work/reout2', 'INV-03')
