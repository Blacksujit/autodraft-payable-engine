"""
INV-13 has 24% VAT lines. ERP derives tax amounts via round2(base * 0.24),
accumulates them, and gets 25023.13. Document says 25023.12.

The document's tax total was computed differently (possibly round2 applied to aggregate).
We need to supply explicit tax_amounts that sum to 25023.12.

Option 1: Find which line to reduce by 0.01 to make the sum work.
Option 2: Read the document's actual per-line tax figures.

Since we can't re-read the image right now, let's use the mathematically correct approach:
The document subtotal is 127564.34, total tax is 25023.12.
If the tax was computed as round2(127564.34 * 0.24) = ?
"""
from decimal import Decimal, ROUND_HALF_UP

def r2(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# Check if tax = round2(subtotal * rate) pattern
subtotal = 127564.34
tax_doc = 25023.12

# Per-line sum approach (what ERP does)
lines_24pct = [
    63479.69, -12695.94, 3173.98, 234.86,
    # (13528.54 and 8897.68 are 0% VAT)
    6976.80, 21380.06, -4276.01, 1069.00,
    # (875.10 is 0% VAT)
    1939.80, 1075.86, -215.17, 53.79, 119.00,
    20711.63, -2946.89, 736.70, 1952.18, -1108.87, 160.85, 2379.20,
    50.00, 12.50
]

per_line_tax_sum = sum(r2(b * 0.24) for b in lines_24pct)
print(f"Sum of round2(base*0.24) per line: {per_line_tax_sum:.4f}")
print(f"Document stated tax: {tax_doc}")
print(f"Delta: {per_line_tax_sum - tax_doc:.4f}")

# What if taxes are computed at group level (per parking provider group)?
# Let's try: apply tax to NET of each group
groups = {
    "EUROPARK": [63479.69, -12695.94, 3173.98, 234.86, 6976.80],  # 24% only
    "EUROPARK_0": [13528.54, 8897.68],  # 0%
    "UHISTEENUSED": [21380.06, -4276.01, 1069.00, 1939.80],  # 24%
    "UHISTEENUSED_0": [875.10],  # 0%
    "AVALIKUD": [1075.86, -215.17, 53.79, 119.00],  # 24%
    "SNABB": [20711.63, -2946.89, 736.70, 1952.18, -1108.87, 160.85, 2379.20],  # 24%
    "MAHTRA": [50.00, 12.50],  # 24%
}

print("\nGroup-level tax calculation:")
total_tax_grouped = 0
for name, prices in groups.items():
    if '_0' in name:
        continue
    net = sum(prices)
    tax = r2(net * 0.24)
    total_tax_grouped += tax
    print(f"  {name}: net={net:.2f}, tax={tax:.4f}")
print(f"Total grouped tax: {total_tax_grouped:.4f}")

# Try aggregate approach
agg = subtotal - (13528.54 + 8897.68 + 875.10)  # subtract 0% items
print(f"\nAggregate 24% base: {agg:.2f}")
print(f"Tax on aggregate: {r2(agg * 0.24):.4f}")

# The document likely computed tax as round2(SUM_OF_24PCT_LINES * 0.24)
sum_24pct_bases = sum(lines_24pct)
print(f"\nSum of 24% bases: {sum_24pct_bases:.2f}")
print(f"Tax = round2(sum * 0.24): {r2(sum_24pct_bases * 0.24):.4f}")
