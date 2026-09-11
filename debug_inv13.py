import json, sys
sys.path.insert(0, 'D:/candidate_kit/candidate_kit')
from erp import erp_book, _line_base, _line_taxes, num, round2

data = json.load(open('D:/candidate_kit/candidate_kit/output/INV-13.json'))
p = data['payables'][0]

# Trace every line
total_base = 0.0
total_tax = 0.0
for i, li in enumerate(p['line_items']):
    base = _line_base(li)
    tax = _line_taxes(li, base)
    total_base += base
    total_tax += tax
    print(f"Line {i:2d}: qty={li['quantity']:>10} price={li['unit_price']:>12} base={base:>12.4f} tax={tax:>10.4f}  {li['description'][:40]}")

net_base = total_base - num(p.get('discount_amount') or 0)
print(f"\nitem_discounted_total: {total_base:.4f}")
print(f"header_discount:       {num(p.get('discount_amount') or 0):.4f}")
print(f"net_base:              {net_base:.4f}")
print(f"line_tax_total:        {total_tax:.4f}")
print(f"header_taxes:          0.0000")
print(f"other_charges:         0.0000")
erp_result = erp_book(p)
print(f"\nERP gross:  {erp_result['will_book_gross']}")
print(f"Doc gross:  {p['gross_total']}")
print(f"Delta:      {erp_result['will_book_gross'] - float(p['gross_total']):.4f}")
print(f"\nDoc subtotal:    {p.get('subtotal', '')}")
print(f"Doc total_tax:   {p.get('total_tax_amount', '')}")
print(f"Subtotal + Tax:  {float(p.get('subtotal','0')) + float(p.get('total_tax_amount','0')):.2f}")
