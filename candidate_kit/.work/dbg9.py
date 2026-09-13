import sys, os, json
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
import autodraft.oracle as O
import erp as ERP
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")

for f in ["INV-11","INV-13","INV-14","INV-16"]:
    exts = P._extract_doc("documents/%s.pdf"%f)
    e = exts if not isinstance(exts, tuple) else exts[0]
    print("="*70)
    print("==== %s: gross=%r inv=%s" % (f, e.gross, e.invoice_number))
    print("  subtotal=%r tax_total=%r discount=%r freight=%r ins=%r extra=%r excise=%r" % (
        e.subtotal, e.tax_total, e.discount_amount, e.freight_charges,
        e.insurance_charges, e.extra_charges, e.excise_duties))
    print("  declared doc_type=%r" % e.invoice_type)
    # Run variants directly
    variants = [("keep", O._variant_keep(e))]
    if any([e.discount_amount, e.freight_charges, e.insurance_charges, e.extra_charges, e.excise_duties]):
        variants.append(("no_header_mods", O._variant_no_header_mods(e)))
    variants.append(("solo_total", O._variant_solo_total(e)))
    variants.append(("solo_gross", O._variant_solo_gross(e)))
    if e.invoice_type == "CREDIT_MEMO":
        variants.append(("header_taxes", O._variant_header_taxes(e)))
    if e.taxes:
        variants.append(("header_amount", O._variant_header_amount(e)))
        variants.append(("header_rate", O._variant_header_rate(e)))
        variants.append(("line_rate", O._variant_line_rate(e)))
    for name, p in variants:
        try:
            r = ERP.erp_book(p)
            nb = r["will_book_gross"]
        except Exception as ex:
            nb = "ERR %s"%ex
        print("  variant %-14s booked_gross=%s (%d li %d tax)" % (name, nb, len(p["line_items"]), len(p["taxes"] or [])))
        for li in p["line_items"][:6]:
            print("     li desc=%r q=%r u=%r t=%r d=%r tx=%s" % (li["description"][:40], li["quantity"], li["unit_price"], li["total"], li["discount"], [(x.get("tax_rate"),x.get("tax_amount")) for x in li["taxes"]]))
        if p.get("taxes"):
            print("     H.TAX:", [(x.get("tax_rate"),x.get("tax_amount")) for x in p["taxes"]])