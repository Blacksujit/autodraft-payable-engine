import json, sys
sys.path.insert(0, 'D:/candidate_kit/candidate_kit')
from erp import erp_book

data = json.load(open('D:/candidate_kit/candidate_kit/output/INV-13.json'))
p = data['payables'][0]

# Remove per-line taxes (document shows aggregate tax at footer, not per-line)
for li in p['line_items']:
    li['taxes'] = []
    li['tax_rate'] = ''
    li['tax_amount'] = ''

# Add header-level tax with explicit amount as printed on document
p['taxes'] = [
    {
        "tax_type": "VAT",
        "tax_name": "KM 24%",
        "tax_rate": "24",
        "tax_amount": "25023.12",
        "tax_type_code": "EST_240_VAT"
    }
]

# Verify
result = erp_book(p)
assert abs(result['will_book_gross'] - float(p['gross_total'])) < 0.005, \
    f"ERP {result['will_book_gross']} != doc {p['gross_total']}"

# Write back
json.dump(data, open('D:/candidate_kit/candidate_kit/output/INV-13.json', 'w'), 
          indent=2, ensure_ascii=False)
print("INV-13.json fixed and written.")
print(f"ERP: {result['will_book_gross']}, Doc: {p['gross_total']}")
