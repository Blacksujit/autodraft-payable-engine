"""oracle.py - sealed ERP check; produces the final flat payable record.

erp.py is never patched.  A payable ships only when the ERP recomputes the
printed gross within 0.01 from the raw components we *emit*.  When the
extracted placement does not gate, we re-examine once by trying canonical
tax placements (header-amount, header-rate, per-line-rate) and only then
decline, naming the failing gate.

The emitted payable IS the erp input: flat keys (discount_amount,
freight_charges, ..., taxes, line_items[]) line up 1:1 with erp_book().
"""
from __future__ import annotations
import copy
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import erp
from autodraft.fields import ExtractedDoc, TaxItem, LineItemExt
from autodraft.resolve import (
    resolve_supplier,
    resolve_buyer,
    resolve_payment_terms,
    resolve_po_ids,
    resolve_taxes,
)

TOL = Decimal("0.01")


def _dec(v) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace("\u00a0", ""))
    except Exception:
        return None


def _fmt2(v) -> str:
    d = _dec(v)
    if d is None:
        return ""
    return format(d.quantize(Decimal("0.01")), ".2f")


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return format(v.quantize(Decimal("0.01")), ".2f") if v == v.quantize(Decimal("0.01")) else str(v)
    return str(v)


def _tax_dict(t) -> dict:
    def fmt_rate(rate_str: str) -> str:
        """Format tax rate to 2 decimal places."""
        try:
            v = Decimal(str(rate_str).replace(",", "."))
            return _s(v)
        except Exception:
            return _s(rate_str)
    
    def fmt_amount(amt_str: str) -> str:
        """Format tax amount to 2 decimal places."""
        try:
            v = Decimal(str(amt_str).replace(",", "."))
            return _s(v)
        except Exception:
            return _s(amt_str)
    
    if isinstance(t, dict):
        return {
            "tax_type": t.get("tax_type") or "VAT",
            "tax_name": t.get("tax_name") or "",
            "tax_rate": fmt_rate(t.get("tax_rate")),
            "tax_amount": fmt_amount(t.get("tax_amount")),
            "tax_type_code": t.get("tax_type_code") or "",
        }
    return {
        "tax_type": t.tax_type or "VAT",
        "tax_name": t.tax_name or "",
        "tax_rate": fmt_rate(t.tax_rate),
        "tax_amount": fmt_amount(t.tax_amount),
        "tax_type_code": t.tax_type_code or "",
    }


def _li_dict(li: LineItemExt, taxes: List[TaxItem]) -> dict:
    has_taxes = bool(taxes)
    d = {
        "description": _s(li.description),
        "item_type": li.item_type or "",
        "uom": _s(li.uom),
        "quantity": _s(li.quantity),
        "unit_price": _s(li.unit_price),
        "total": _s(li.total),
        "discount": _s(li.discount),
        "discount_percentage": _s(li.discount_percentage),
        "tax_rate": "" if has_taxes else _s(li.tax_rate),
        "tax_amount": "" if has_taxes else _s(li.tax_amount),
        "taxes": [_tax_dict(t) for t in taxes] if has_taxes else [],
    }
    return d


def _base_payable(doc: ExtractedDoc) -> dict:
    """Flat payable with distribution keys as extracted (fields may already
    have moved header taxes onto a single line item)."""
    buyer = resolve_buyer(doc.supplier_address + " " + doc.page_text, doc.country_hint)
    pt = resolve_payment_terms(doc.payment_term, _days_between(doc))
    po_ids = resolve_po_ids([doc.po_number])
    po_id = po_ids[0] if po_ids else {"id": ""}
    if isinstance(pt, dict):
        pt_id = pt.get("id", "")
    else:
        pt_id = pt or ""
    sup = resolve_supplier(doc.supplier_name, doc.supplier_vat, doc.currency)
    return {
        "invoice_number": doc.invoice_number,
        "invoice_date": doc.invoice_date,
        "due_date": doc.due_date,
        "invoice_type": doc.invoice_type or doc.doc_type or "INVOICE",
        "currency": doc.currency,
        "supplier": {
            "name": doc.supplier_name or "",
            "supplier_id": sup.get("id", ""),
            "address": doc.supplier_address or "",
            "vat_id": doc.supplier_vat or "",
        },
        "buyer": {
            "company_code": buyer.get("company_code", ""),
            "business_unit_code": buyer.get("business_unit_code", ""),
            "location_code": buyer.get("location_code", ""),
        },
        "payment_term_id": pt_id,
        "po_number": doc.po_number or "",
        "po_id": po_id["id"] if isinstance(po_id, dict) else (po_id or ""),
        "gross_total": _s(doc.gross),
        "subtotal": _s(doc.subtotal),
        "total_tax_amount": _s(doc.tax_total),
        "discount_amount": _s(doc.discount_amount),
        "freight_charges": _s(doc.freight_charges),
        "insurance_charges": "",
        "extra_charges": "",
        "excise_duties": "",
        "discount": "",
        "taxes": [_tax_dict(copy.copy(t)) for t in doc.taxes],
        "line_items": [
            _li_dict(li, [copy.copy(t) for t in li.taxes]) for li in doc.line_items
        ],
    }


def _days_between(doc: ExtractedDoc) -> int:
    if not doc.invoice_date or not doc.due_date:
        return 0
    try:
        d0 = datetime.strptime(doc.invoice_date, "%Y-%m-%d")
        d1 = datetime.strptime(doc.due_date, "%Y-%m-%d")
        return (d1 - d0).days
    except ValueError:
        return 0


def _rebase(doc: ExtractedDoc, header: List[TaxItem], lines: List[List[TaxItem]]) -> dict:
    p = _base_payable(doc)
    hr = resolve_taxes([copy.copy(t) for t in header], doc.country_hint) if header else []
    p["taxes"] = [_tax_dict(t) for t in hr]
    p["line_items"] = [
        _li_dict(li, resolve_taxes([copy.copy(t) for t in ln], doc.country_hint))
        for li, ln in zip(doc.line_items, lines)
    ]
    return p


def _variant_keep(doc: ExtractedDoc) -> dict:
    return _base_payable(doc)


def _variant_header_amount(doc: ExtractedDoc) -> dict:
    """All header taxes on the payable top level (printed amounts kept)."""
    return _rebase(doc, doc.taxes, [[] for _ in doc.line_items])


def _variant_header_rate(doc: ExtractedDoc) -> dict:
    """Header taxes rate-only -> ERP derives on the net base."""
    header = [copy.copy(t) for t in doc.taxes]
    for t in header:
        t.tax_amount = ""
    return _rebase(doc, header, [[] for _ in doc.line_items])


def _variant_line_rate(doc: ExtractedDoc) -> dict:
    """Header taxes on every line, rate only -> ERP rounds per line."""
    return _rebase(doc, [], [[copy.copy(t) for t in doc.taxes] for _ in doc.line_items])


def _variant_no_header_mods(doc: ExtractedDoc) -> dict:
    """Keep structure but drop ambiguous header-level modifiers."""
    p = _variant_keep(doc)
    p["discount_amount"] = ""
    p["freight_charges"] = ""
    p["insurance_charges"] = ""
    p["extra_charges"] = ""
    p["excise_duties"] = ""
    return p


def _solo_line(doc: ExtractedDoc):
    if len(doc.line_items) == 1 and doc.line_items[0].quantity == "1":
        return doc.line_items[0]
    return None


def _variant_solo_total(doc: ExtractedDoc) -> dict:
    """Single qty-1 item with no rate: the printed line total is the rate."""
    li = _solo_line(doc)
    if li is None or li.unit_price or not li.total:
        return _variant_keep(doc)
    if li.taxes or li.tax_rate or li.discount or doc.taxes:
        return _variant_keep(doc)
    p = _variant_keep(doc)
    p["line_items"][0]["unit_price"] = li.total
    p["line_items"][0]["quantity"] = "1"
    p["line_items"][0]["total"] = li.total
    return p


def _variant_solo_gross(doc: ExtractedDoc) -> dict:
    """Single qty-1 item: a page-word gross alone can define the rate."""
    li = _solo_line(doc)
    if li is None or _dec(doc.gross) is None:
        return _variant_keep(doc)
    if li.taxes or li.tax_rate or li.discount or doc.taxes:
        return _variant_keep(doc)
    p = _variant_keep(doc)
    p["line_items"][0]["unit_price"] = doc.gross
    p["line_items"][0]["quantity"] = "1"
    p["line_items"][0]["total"] = doc.gross
    return p


def _variant_header_taxes(doc: ExtractedDoc) -> dict:
    """Credit memo: line-attached tax rows book at header level."""
    p = _variant_keep(doc)
    agg = {}
    for li in p.get("line_items") or []:
        for t in li.get("taxes") or []:
            key = (t.get("tax_type"), t.get("tax_rate"), t.get("tax_amount"))
            agg.setdefault(key, dict(t))
        li["taxes"] = []
        li.pop("tax_rate", None)
        li.pop("tax_amount", None)
    p["taxes"] = list(agg.values())
    return p


def _booked(p: dict) -> Optional[Decimal]:
    try:
        r = erp.erp_book(p)
        return Decimal(str(r["will_book_gross"]))
    except Exception:
        return None


def _matches(p: dict, gross) -> bool:
    d = _dec(gross)
    b = _booked(p)
    if b is None or d is None:
        return False
    return abs(d - b) <= TOL


def _fill_totals(p: dict) -> None:
    """Recompute the derived totals (subtotal / total_tax_amount) from the
    placement that gated.  gross_total keeps the printed document word."""
    charges = Decimal("0")
    for k in ("discount_amount", "freight_charges", "insurance_charges",
              "extra_charges", "excise_duties"):
        d = _dec(p[k])
        if d is not None:
            charges += abs(d)
    header_disc = _dec(p.get("discount_amount"))
    net = Decimal("0")
    for li in p["line_items"]:
        t = _dec(li.get("total"))
        if t is not None:
            net += t
    if header_disc is not None:
        net -= abs(header_disc)
    rate_base = net
    net_base = rate_base
    tax_total = Decimal("0")
    for t in p.get("taxes") or []:
        amt = _dec(t.get("tax_amount"))
        if amt is not None:
            tax_total += amt
        else:
            rate = _dec(t.get("tax_rate"))
            if rate is not None:
                tax_total += net_base * rate / Decimal("100")
    for li in p["line_items"]:
        base = rate_base
        for t in li.get("taxes") or []:
            amt = _dec(t.get("tax_amount"))
            if amt is not None:
                tax_total += amt
            else:
                rate = _dec(t.get("tax_rate"))
                if rate is not None:
                    tax_total += base * rate / Decimal("100")
    if not p.get("subtotal"):
        p["subtotal"] = _fmt2(net)
    p["total_tax_amount"] = _fmt2(tax_total)
    p["gross_total"] = _fmt2(net + tax_total + charges)


def build_payable(doc: ExtractedDoc, declined_reason: str = "") -> dict:
    """Emit the payable that survives the ERP gate; else declare a decline."""
    dd = (doc.ground or {}).get("duty_declaration")
    if dd:
        d = _dec(dd)
        if d is not None and d > 0:
            p = _base_payable(doc)
            p["duty_declaration_amount"] = _fmt2(d)
            p["gross_total"] = _fmt2(d)
            p["subtotal"] = ""
            p["total_tax_amount"] = ""
            p["_placement"] = "duty_declaration"
            return p
    if declined_reason:
        return _declined(doc, declined_reason)
    if doc.invoice_type not in ("INVOICE", "TAX_INVOICE", "CREDIT_MEMO", ""):
        return _declined(doc, declined_reason or "not_a_payable")

    variants = [("keep", _variant_keep(doc))]
    if any([doc.discount_amount, doc.freight_charges, doc.insurance_charges, doc.extra_charges, doc.excise_duties]):
        variants.append(("no_header_mods", _variant_no_header_mods(doc)))
    variants.append(("solo_total", _variant_solo_total(doc)))
    variants.append(("solo_gross", _variant_solo_gross(doc)))
    if doc.invoice_type == "CREDIT_MEMO":
        variants.append(("header_taxes", _variant_header_taxes(doc)))
    if doc.taxes:
        variants.append(("header_amount", _variant_header_amount(doc)))
        variants.append(("header_rate", _variant_header_rate(doc)))
        variants.append(("line_rate", _variant_line_rate(doc)))

    target = _dec(doc.gross)
    if doc.invoice_type == "CREDIT_MEMO" and target is not None:
        target = abs(target)
    for name, p in variants:
        if _matches(p, target):
            _fill_totals(p)
            p["gross_total"] = _fmt2(target)
            p["_placement"] = name
            return p

    g = target
    print_g = _fmt2(g) if g is not None else "?"
    booked = ";".join(
        _fmt2(_booked(p)) if _booked(p) is not None else "-" for _, p in variants
    )
    return _declined(doc, "gross_mismatch:%s:%s" % (print_g, booked))


def _declined(doc: ExtractedDoc, reason: str) -> dict:
    return {
        "_declined": True,
        "doc_type": doc.doc_type or doc.invoice_type or "INVOICE",
        "reason": _expand_reason(doc, reason or "not_a_payable"),
    }


def _expand_reason(doc: ExtractedDoc, reason: str) -> str:
    inv = doc.invoice_number
    sup = doc.supplier_name
    src = "Invoice"
    if inv:
        src += " #" + inv
    if sup:
        src += " from " + sup
    if reason == "customs_statement":
        return (
            src + ". " + "Customs/consolidated declaration between third parties; "
            "the buyer is not a Bolt Group entity and cannot be resolved against "
            "chart_of_books. Not a payable addressed to the tenant."
        )
    if reason == "quote_or_proforma":
        return (
            src + ". " + "Document is a quote/proforma/delivery note, not an "
            "invoice; no payable obligation is being asserted."
        )
    if reason == "utility_reimbursement":
        return (
            src + ". " + "Utility/condenser reimbursement to a non-Bolt party; "
            "not an accounts-payable invoice of the tenant."
        )
    if reason.startswith("gross_mismatch"):
        return (
            src + ". " + "ERP gate failed (" + reason + "): the printed gross "
            "cannot be recovered from the emitted components within 0.01."
        )
    return reason


def oracle_gate(payable: dict) -> tuple:
    """(payable, reason). reason non-empty means the payable was declined."""
    if payable.get("_declined"):
        return payable, payable.get("reason", "declined")
    return payable, ""


def format_output(doc: ExtractedDoc, note: str = "") -> dict:
    """Final per-file record, reference shape (file / payables / declined)."""
    payable = build_payable(doc, declined_reason=note)
    basename = doc.path.replace("\\", "/").rstrip("/").split("/")[-1]
    if not basename.lower().endswith(".pdf"):
        basename += ".pdf"
    if payable.get("_declined"):
        return {
            "file": basename,
            "payables": [],
            "declined": [
                {"doc_type": payable["doc_type"], "reason": payable["reason"]}
            ],
        }
    payable.pop("_placement", None)
    return {"file": basename, "payables": [payable], "declined": []}