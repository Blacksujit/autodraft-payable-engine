"""
INV-13 fix: The document computes tax as one aggregate round2(sum_of_24pct_bases * 0.24) = 25023.12
This is a HEADER-level tax, not per-line. Moving it to header where it belongs structurally.

The document shows subtotal 127564.34 and total KM (tax) 25023.12 as aggregate footer entries.
No per-line tax column exists in the document.
This means the tax is applied once at header level on the net subtotal of 24%-taxable lines.

Note: 2 lines are KM 0% (KESKLINN, SÜDALINN, TARTU) so we need to handle mixed rates.
But since the document only shows ONE aggregate tax amount (25023.12), and the base for that
is the sum of 24% lines = 104263.02, we supply the tax_amount explicitly.

ERP with header tax = round2(net_base * rate/100):
net_base = 127564.34 (all lines)
But 24% only applies to 104263.02 of that, not all of it.
So we must supply explicit tax_amount = 25023.12 (as printed on document).
"""
import json
from decimal import Decimal, ROUND_HALF_UP
import sys
sys.path.insert(0, 'D:/candidate_kit/candidate_kit')
from erp import erp_book

def r2(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# Load and modify
data = json.load(open('D:/candidate_kit/candidate_kit/output/INV-13.json'))
p = data['payables'][0]

# Remove per-line taxes - the document shows them at aggregate footer level
for li in p['line_items']:
    li['taxes'] = []
    li['tax_rate'] = ''
    li['tax_amount'] = ''

# Add header-level tax with explicit amount (as printed on document)
p['taxes'] = [
    {
        "tax_type": "VAT",
        "tax_name": "KM 24%",
        "tax_rate": "24",
        "tax_amount": "25023.12",  # explicit amount as printed on document
        "tax_type_code": "EST_240_VAT"
    }
]

# Verify with ERP
result = erp_book(p)
print(f"ERP gross: {result['will_book_gross']}")
print(f"Doc gross: {p['gross_total']}")
print(f"Match: {abs(result['will_book_gross'] - float(p['gross_total'])) < 0.005}")

# Wait - the header tax base would be ALL lines (127564.34), not just 24% lines.
# We need explicit amount since the base isn't the plain net.
# With explicit amount=25023.12, ERP uses that directly. Let's check.
