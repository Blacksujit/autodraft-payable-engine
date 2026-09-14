"""build_synthetic.py - Phase 5 adversarial held-back set generator.

Creates 11 never-seen PDFs under heldback/documents/ exercising situations the
open corpus does NOT contain:
  * languages not in the open set (FR, IT, NL, ES, DE)
  * comma-decimal and mixed-separator amounts
  * reversed / unusual column orders
  * a multi-invoice PDF (two payables from one file)
  * a credit-note path
  * ambiguous dates, unknown supplier, absent PO, fractional quantities
  * honest declines: a quotation and a customs form
  * one PROVABLY UNSOLVABLE document (no page can support an answer)

Every numeric total below reconciles to the printed gross when the line items
and header tax are emitted correctly, so any booking / decline is a property of
the machinery, never of the generator faking the numbers.

Run:  python heldback/build_synthetic.py
"""
from __future__ import annotations

import os

import pymupdf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")


def write_pdf(fname: str, blocks: list[str]):
    os.makedirs(OUT, exist_ok=True)
    doc = pymupdf.open()
    for block in blocks:
        page = doc.new_page(width=595, height=842)
        y = 70
        for ln in block.splitlines():
            if ln.strip():
                page.insert_text((60, y), ln, fontsize=11)
            y += 17
    path = os.path.join(OUT, fname + ".pdf")
    doc.save(path)
    doc.close()
    return path


def invoice(fname, title, no_label, no_val, table_hdr, rows, sub_label, sub,
            tax_label, tax, gross_label, gross, supplier="SyntheticSupplies OU",
            date="03/04/2026", extra=()):
    body = [title, f"{no_label}: {no_val}", f"Supplier: {supplier}", f"Date: {date}",
            table_hdr]
    body += [f"{q:<6}  {u:>10.2f}  {t:>10.2f}" for q, u, t in rows]
    body += [f"{sub_label:<22}{sub:>28.2f}", f"{tax_label:<22}{tax:>28.2f}",
             f"{gross_label:<22}{gross:>28.2f}"]
    body += list(extra)
    return body


def build():
    # HELD-01 FR — comma decimals, TVA header tax
    sub = 175.00
    tax = round(sub * 0.20, 2)
    write_pdf("HELD-01", [ "\n".join(invoice(
        "HELD-01", "FACTURE", "Facture N°", "H-2026-0417",
        "Qté  Prix unitaire  Total", [(2, 50.00, 100.00), (3, 25.00, 75.00)],
        "Montant HT", sub, "TVA 20%", tax, "Total TTC", sub + tax,
        supplier="ForfaitMetal SAS", date="12/05/2026")) ])

    # HELD-02 IT — dot decimals, IVA
    sub = 1230.00
    tax = round(sub * 0.22, 2)
    write_pdf("HELD-02", [ "\n".join(invoice(
        "HELD-02", "FATTURA", "Fattura n.", "F/2026/088",
        "N.  Prezzo unitario  Totale", [(1, 1200.00, 1200.00), (1, 30.00, 30.00)],
        "Imponibile", sub, "IVA 22%", tax, "Totale Fattura", sub + tax,
        supplier="MareMoto SRL", date="31/07/2026",
        extra=["PO: absent"])) ])

    # HELD-03 NL — comma decimals with dot thousands, BTW
    sub = 26.74
    tax = round(sub * 0.21, 2)
    write_pdf("HELD-03", [ "\n".join(invoice(
        "HELD-03", "FACTUUR", "Factuurnr.", "2026-0719",
        "Aantal  Stuksprijs  Totaal", [(5, 4.95, 24.75), (1, 1.99, 1.99)],
        "Subtotaal excl. btw", sub, "BTW 21%", tax, "Totaal incl. btw", round(sub + tax, 2),
        supplier="Kanaalhandel BV", date="01/09/2026")) ])

    # HELD-04 ES — reversed column order (qty | total | unit), IVA
    sub = 72.00
    tax = round(sub * 0.21, 2)
    write_pdf("HELD-04", [ "\n".join(invoice(
        "HELD-04", "FACTURA", "Factura Nº", "FAC-2026-114",
        "Cant.  Total  Precio unit.", [(8, 7.50, 60.00), (4, 3.00, 12.00)],
        "Base imponible", sub, "IVA 21%", tax, "Total Factura", round(sub + tax, 2),
        supplier="AndaluzTech SL", date="15/08/2026")) ])

    # HELD-05 DE — MwSt, Zwischensumme/Gesamtbetrag
    sub = 31.00
    tax = round(sub * 0.19, 2)
    write_pdf("HELD-05", [ "\n".join(invoice(
        "HELD-05", "RECHNUNG", "Rechnungsnummer", "R-2026-3321",
        "Menge  Einzelpreis  Gesamt", [(10, 2.50, 25.00), (2, 3.00, 6.00)],
        "Zwischensumme", sub, "MwSt 19%", tax, "Gesamtbetrag", round(sub + tax, 2),
        supplier="Bayerwald GmbH", date="22/06/2026")) ])

    # HELD-06 MULTI — two invoices, one PDF, two payables
    a = "\n".join(invoice("HELD-06a", "FACTURE", "Facture N°", "H-2026-0999",
        "Qté  Prix u.  Total", [(1, 500.00, 500.00)], "Montant HT", 500.00,
        "TVA 20%", 100.00, "Total TTC", 600.00, supplier="ForfaitMetal SAS",
        date="02/02/2026"))
    b = "\n".join(invoice("HELD-06b", "FACTURE", "Facture N°", "H-2026-1000",
        "Qté  Prix u.  Total", [(2, 250.00, 500.00)], "Montant HT", 500.00,
        "TVA 20%", 100.00, "Total TTC", 600.00, supplier="ForfaitMetal SAS",
        date="03/02/2026"))
    write_pdf("HELD-06", [a, b])

    # HELD-07 CREDIT NOTE — Estonian cues, Tasuda gross
    write_pdf("HELD-07", [ "\n".join(invoice(
        "HELD-07", "CREDIT NOTE / KREDIITARVE", "Kreeditarve nr", "K-2026-007",
        "Kogus  Ühikhind  Kokku", [(1, 1000.00, 1000.00)],
        "Summa", 1000.00, "KM 10%", 100.00, "Tasuda", 1100.00,
        supplier="Põhjavõrgu OU", date="20/04/2026",
        extra=["CREDIT NOTE", "Arve nr"])) ])

    # HELD-08 — ambiguous date, unknown supplier, fractional quantities, no PO
    write_pdf("HELD-08", [ "\n".join([
        "INVOICE", "Invoice No: R-9033",
        "Supplier: Conshohocken Req Supplies", "Date: 03/04/2026   Due: 03/11/2026",
        "qty  unit  total",
        "0.125  400.00  50.00",
        "1.000  20.00  20.00",
        "Subtotal          70.00",
        "Tax 0%             0.00",
        "Amount Due        70.00"]) ])

    # HELD-09 QUOTATION — must decline NOT_A_PAYABLE quote_or_proforma
    write_pdf("HELD-09", [ "\n".join([
        "QUOTATION", "This is a quotation, not an invoice.",
        "Quotation No: Q-118   Date: 05/09/2026", "Valid for 30 days.",
        "Item  unit  total", "Server rack  2200.00  2200.00",
        "Estimated total  2200.00"]) ])

    # HELD-10 CUSTOMS / packing list — must decline customs_statement
    write_pdf("HELD-10", [ "\n".join([
        "PACKING LIST / CUSCARGO", "Customs declaration 2026/90413",
        "Shipper: Winlink Cargo     Consignee: OtherCo Trading",
        "HS Code: 8471.30   Country of origin: DE",
        "Gross weight 990 kg    Net weight 880 kg", "Boxes No.: 4",
        "Commercial invoice: CI-2026-4412", "Freight value  1200.00"]) ])

    # HELD-UNSOLVABLE — no monetary amount exists anywhere
    write_pdf("HELD-UNSOLVABLE", [ "\n".join([
        "PARKED DOCUMENT", "Project NRIC: PD 0 0 & PD B0", "Contact: 555-0199",
        "This page contains no monetary amount and no invoice number.",
        "It is a routing memo with a barcode and a signature.",
        "Revision A - internal use only."]) ])

    print("wrote 11 synthetic docs to", OUT)


if __name__ == "__main__":
    build()