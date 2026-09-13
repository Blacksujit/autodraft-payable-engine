import sys, pymupdf, re
sys.path.insert(0,".")
from autodraft.pipeline import _render_page, _extract_doc
from autodraft.render import render_page_layout
from autodraft.fields import _extract_totals, _extract_taxes, _extract_line_items, _is_summary_row
from autodraft.oracle import build_payable, _fill_totals, _booked, _matches
from erp import erp_book

pdf = "documents/INV-34.pdf"
d = pymupdf.open(pdf)
print("pages:", d.page_count)
for i in range(d.page_count):
    text = _render_page(pdf, i)
    print("=== PAGE", i, "text (first 1200 chars) ===")
    print(text[:1200])
    lo = render_page_layout(pdf, i)
    footer = lo.footer_text
    header = lo.header_text
    print("--- header:", repr((header or "")[:200]))
    print("--- footer:", repr((footer or "")[:200]))
    # totals (no line_sum yet)
    try:
        g, used = _extract_totals(header, footer, None, {})
        print("--- totals:", g, "used labels:", used)
    except Exception as e:
        print("totals err:", e)
    # taxes
    try:
        taxes = _extract_taxes(header, footer, g)
        print("--- taxes:", [(x.tax_type, x.tax_name, x.tax_rate, x.tax_amount) for x in taxes])
    except Exception as e:
        print("taxes err:", e)

print("\n=== MERGED ext ===")
ext, _ = _extract_doc(pdf)
if ext is not None:
    print("gross:", ext.gross, "subtotal:", ext.subtotal, "tax_total:", ext.tax_total,
          "discount:", ext.discount_amount, "freight:", ext.freight_charges,
          "invoice:", ext.invoice_number, "country:", ext.buyer_country)
    print("taxes:", [(x.tax_type, x.tax_name, x.tax_rate, x.tax_amount) for x in ext.taxes])
    print("lines:")
    for li in ext.line_items:
        print(" -", repr(li.description)[:40], "q=", li.quantity, "u=", li.unit_price, "t=", li.total, "tax_r=", li.tax_rate, "tax_a=", li.tax_amount)
    print("\n=== oracle ===")
    p = build_payable(ext)
    print("placement:", p.get("_placement"))
    print("taxes:", p.get("taxes"))
    print("gross_total:", p.get("gross_total"))
    from erp import erp_book as eb
    r = eb(p)
    print("erp_book:", r)

