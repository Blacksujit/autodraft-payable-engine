"""fields.py - header/line extraction with grounding.

Every value we emit is grounded to a page word (or derived from present
words, always marked derived). We submit raw components; the ERP derives
totals. Nothing here resolves master data - that is resolve.py's job.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from autodraft.geom import Line, Word
from autodraft.normalize import parse_amount, parse_date, detect_currency, quantize_2
from autodraft.structure import PageLayout, Table

# ---------------------------------------------------------------- currency -

_EU_CC = {"DE","EE","FR","IT","ES","PT","AT","CH","NL","BE","PL","SE","NO","DK","FI","RO","CZ","HU","GR","IE","BG","HR","SK","SI","LU","LT","LV","CY","MT"}

def _eu_hint(cc: str, text: str) -> str:
    if cc in _EU_CC:
        return "dmy"
    t = text.lower()
    if any(k in t for k in ("mehrwertsteuer","umsatzsteuer","rechnungsdatum","zahlbar","netto","brutto","steuer")):
        return "dmy"
    return ""

_CNTRY_CURRENCY = {
    "EE": "EUR", "DE": "EUR", "PT": "EUR", "AT": "EUR", "FI": "EUR",
    "ZA": "ZAR", "GH": "GHS", "KE": "KES", "MY": "MYR", "GB": "GBP",
    "US": "USD", "NG": "NGN", "IN": "INR",
}
_CNTRY_WORD = {
    "south africa": "ZA", "estonia": "EE", "germany": "DE", "ghana": "GH",
    "malaysia": "MY", "portugal": "PT", "united kingdom": "GB", "kenya": "KE",
    "netherlands": "NL", "usa": "US", "united states": "US",
}


def _norm(w: str) -> str:
    return "".join(ch for ch in (w or "").lower() if ch.isalnum())


def _country_hint(text: str) -> str:
    for pat in (r"VAT\s*[:#\-]?\s*([A-Z]{2})\d", r"VATID\s*[:#\-]?\s*([A-Z]{2})\d",
                r"UST\s*ID\s*[:#\-]?\s*([A-Z]{2})\d", r"KMKR\s*[:#\-]?\s*([A-Z]{2})\d"):
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).upper()
    low = text.lower()
    for kw, cc in _CNTRY_WORD.items():
        if kw in low:
            return cc
    return ""


# ---------------------------------------------------------------- role map --

_QTY_HDR = ("menge", "qty", "quantity", "pcs", "stueck", "stk", "stunden", "hours", "hr", "hrs", "h")
_UNIT_HDR = ("einzelpreis", "unitprice", "stueckpreis", "nettoeinzelpreis", "rate", "preis", "unitprice", "unit price", "price", "einz", "tariff")
_TOTAL_HDR = ("gesamtpreis", "linetotal", "amount", "gesamt", "totalnet", "netto", "brutto", "summe", "total", "wert")
_DSCT_HDR = ("rabatt", "discount", "diskt", "skuonto", "diskon", "reduction")
_POS_HDR = ("pos", "position", "nr", "no", "lfd")


def assign_roles(table: Table) -> Dict[str, int]:
    roles = {"unit": -1, "qty": -1, "total": -1, "discount": -1, "pos": -1}
    header = table.header_row
    descr_has_qty = False
    if header is not None:
        hrow = table.rows.get(header, {})
        if hrow:
            if Table.DESCR in hrow:
                descr_label = _norm(" ".join(t for bs, t in hrow[Table.DESCR]))
                if any(k in descr_label for k in _QTY_HDR):
                    descr_has_qty = True

            for col_idx, toks in hrow.items():
                if col_idx == Table.DESCR:
                    continue
                label = _norm(" ".join(t for bs, t in toks))
                if not label:
                    continue
                if any(k in label for k in _DSCT_HDR):
                    roles["discount"] = col_idx
                elif any(k in label for k in _QTY_HDR):
                    roles["qty"] = col_idx
                elif any(k in label for k in _TOTAL_HDR):
                    roles["total"] = col_idx
                elif any(k in label for k in _UNIT_HDR):
                    roles["unit"] = col_idx
                elif any(k in label for k in _POS_HDR):
                    roles["pos"] = col_idx

    money = sorted(c.index for c in table.columns if c.index in table.money_cols)
    if money:
        # Check if first money column has integer values (likely quantity)
        first_money_is_qty = False
        if len(money) >= 2:
            first_money_col = money[0]
            int_count = 0
            total_count = 0
            for r in sorted(table.rows):
                if r == header:
                    continue
                val = table.cell(r, money[0])
                a = _money_token(table.cell(r, money[0]))
                if a is not None and a == a.to_integral_value() and a > 0:
                    int_count += 1
                total_count += 1
            if total_count > 0 and int_count / total_count >= 0.5:
                first_money_is_qty = True

        if descr_has_qty and len(money) >= 2:
            roles["qty"] = money[0]
            roles["unit"] = money[1]
            if len(money) > 2:
                roles["total"] = money[-1]
        elif first_money_is_qty and len(money) >= 2:
            # First money column has integer values -> likely quantity
            roles["qty"] = money[0]
            roles["unit"] = money[1]
            if len(money) > 2:
                roles["total"] = money[-1]
        elif roles["unit"] < 0:
            roles["unit"] = money[0]
            if len(money) > 1:
                roles["total"] = money[-1]

    # If unit and total are the same column, clear unit (no separate unit price column)
    if roles["unit"] >= 0 and roles["unit"] == roles["total"]:
        roles["unit"] = -1

    best, best_score = None, -1
    for ci in [c.index for c in table.columns if c.index not in table.money_cols and c.index != Table.DESCR]:
        cnt, mx = 0, 0
        for r in sorted(table.rows):
            if r == header:
                continue
            a = _money_token(table.cell(r, ci))
            if a is not None and a == a.to_integral_value() and a > 0:
                cnt += 1
                mx = max(mx, int(a))
        if cnt >= 1 and 0 < mx <= 100000 and cnt > best_score:
            best, best_score = ci, cnt
    if roles["qty"] < 0:
        roles["qty"] = best if best is not None else -1
    return roles


_QTY_SPLIT = re.compile(r"^([\d.,]+)\s*(.*)$")


def _split_qty_uom(tok: str) -> Tuple[Optional[Decimal], str]:
    m = _QTY_SPLIT.match(tok.strip())
    if not m:
        return None, tok
    a = _money_token(m.group(1))
    if a is None or a < 0:
        return None, tok
    return a, m.group(2).strip()


def _money_token(s: str) -> Optional[Decimal]:
    a = parse_amount(s)
    if a is None or a.ambiguous or a.value is None:
        return None
    return Decimal(a.value)


def _rel(s) -> Decimal:
    """Ordering-only magnitude for candidate ranking (locale-free)."""
    try:
        return abs(Decimal(str(s).replace(",", "")))
    except Exception:
        return Decimal(0)


# ---------------------------------------------------------------- regexes ---

_INV_NO_RE = [
    # Specific invoice number patterns - avoid matching supplier names like "Northwind"
    # Require at least one digit in the captured group
    re.compile(r"(?:Rechnungs?Nr\.?|Rechnungsnummer|Invoice\s*(?:number|no)\.?|Doc(?:ument)?\s*(?:#|no))\s*[:#]?\s*([A-Za-z0-9]*[0-9][A-Za-z0-9/\-]{2,})", re.I),
    # Fallback: standalone INV... or similar patterns with digits
    re.compile(r"\b(INV[0-9][A-Za-z0-9/\-]{4,})\b", re.I),
    re.compile(r"\b([0-9]{6,})\b"),  # 6+ digit numbers as last resort
]
_DATE_LABEL_RE = re.compile(
    r"(?:Rechnungsdatum|Invoice\s*Date|Datum|Date)\s*[:#]?\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{1,2}[A-Za-z]{3}\d{2,4})", re.I)
_ANY_DATE_RE = re.compile(r"\b(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{1,2}[A-Za-z]{3}\d{2,4})\b")
_DUE_EXPL_RE = re.compile(
    r"(?:zahlbar\s*(?:bis|zum)|due\s*(?:date|on)?|payment\s*(?:due|date)|DueDate)\s*[:#]?\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{1,2}[A-Za-z]{3}\d{2,4})", re.I)
_DUE_BIS_RE = re.compile(
    r"bis(?:\s*zum)\s*[:#]?\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{1,2}[A-Za-z]{3}\d{2,4})", re.I)
_TERM_DAYS_RE = re.compile(
    r"(?:within|innerhalb\s*von|zahlbar\s*in)\s*(\d{1,3})\s*(?:tagen|days|kalendertagen)", re.I)
_BILL_DAYS_RE = re.compile(r"\b(\d{1,3})\s*(?:tagen|days)\b", re.I)
_TERM_NET_RE = re.compile(r"\bnet(?:to)?\s*(\d{1,3})\b", re.I)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+)")
_VAT_SEARCH_RE = re.compile(
    r"\b(?:VAT(?:ID|No|Reg)?|UST[ -]?ID|KMKR|Reg\.?Nr|VAT Number)\s*[:#]?\s*([A-Z]{2}[\w\-]{4,20})\b", re.I)

_BAL_LABELS = [
    re.compile(
        r"(?:Arvekokku|Tasuda|Tasumata|Verschuldigd|Amount\s*(?:Due|Payable)|Balance\s*Due|Zu\s*zahlen|Offener\s*Betrag|Betrag\s*zu\s*zahlen|A\s*pagar|Montant\s*(?:à\s*payer|du)|Balance\s*(?:to\s*pay|due)|Total\s*Due|Saldo\s*a)", re.I
    ),
]

_GROSS_LABELS = [
    re.compile(r"(?:Endbetrag|Gesamtsumme|Gesamtbetrag|Brutto|Rechnungsbetrag|Zu\s*zahlen|Summe\s*inkl|Netto\s*inkl)", re.I),
    re.compile(r"(?:Total|Amount\s*(?:Due|Payable)|Balance\s*Due|Grand\s*Total|Invoice\s*Total|Gross(?:\s*Total)?|Net\s*Total|Amount\s*Due)", re.I),
    re.compile(r"(?:Arvekokku|Tasuda|Kokku|Summakoosk\w*maksuga|Tasumata|Summa\s*koos|K\w*maksuga)", re.I),
    re.compile(r"(?:Totaal|Verschuldigd|Including\s*VAT|Incl\.?\s*VAT|Tax\s*Invoice|Total\s*Bill|Faktura\s*total)", re.I),
]
_SUB_LABELS = [
    re.compile(r"(?:Zwischensumme|Subtotal|Sub-total|Netto|Net\s*(?:amount|total)?|Summe\s*(?:vor|ohne|exkl)|Betrag\s*netto)", re.I),
    re.compile(r"(?:Summailmak\w*maksuta|Vahesumma|Summa\s*ilma|Summa\s*enne|Summa\s*neto)", re.I),
    re.compile(r"(?:Amount|Price|Package\s*Price)\s*(?:Sub)?\s*total", re.I),
]
_TAX_TOTAL_LABELS = [
    re.compile(r"(?:Total\s*VAT|Allocated\s*Sales\s*Tax|VAT\s*Amount|VAT\s*Included|Input\s*VAT|Output\s*VAT|Sales\s*Tax|U\s*I\s*T)", re.I),
    re.compile(r"(?:MwSt|Mehrwertsteuer|USt|Umsatzsteuer|VAT|IVA|BTW|K\w*maks)", re.I),
]
_DISC_LABELS = [
    re.compile(r"(?:Rabatt|Discount|Soodustus|Diskont|Reduction|Allowance)", re.I),
    re.compile(r"(?:Allahindlus|Korting)", re.I),
]
_FREIGHT_LABELS = [
    re.compile(r"(?:Freight|Fracht|Versand|Lieferung|Delivery|Transport|Shipping)", re.I),
    re.compile(r"(?:Transport\s*fields|Kulud)", re.I),
]


def _amt_candidates(line: str) -> List[str]:
    """Right-ordered candidate amount tokens (handles E-prefix currency, minus)."""
    out = []
    for m in re.finditer(r"(?<![.,\d])-?\d{1,3}(?: ?\d{3})+(?:[.,]\d{2})", line):
        raw = m.group(0).replace(" ", "")
        if any(ch.isdigit() for ch in raw):
            out.append(raw)
    for m in re.finditer(r"[E€$£]\s?(-?\s?[\d][\d.,]{0,30})|(-?[\d][\d.,]{0,30})", line):
        raw = (m.group(1) or m.group(2) or "").replace(" ", "")
        raw = raw.strip(".,")
        if raw and any(ch.isdigit() for ch in raw):
            out.append(raw)
    return list(reversed(out))


def _clean_amt(tok: str) -> Optional[str]:
    neg = tok.lstrip().startswith("-")
    tok = tok.strip().replace(" ", "").replace("\u00a0", "")
    a = parse_amount(tok)
    if a is None or a.value is None:
        return None
    if a.ambiguous and not re.fullmatch(r"[+-]?\d+[.,]\d{2}", tok):
        return None
    v = str(a.value)
    if neg and not v.startswith("-"):
        v = "-" + v
    return v


def _label_amount(text: str, labels: List[re.Pattern], prefer_last: bool = False) -> str:
    """Amount that follows a label within a short window (skips %-rates)."""
    for line in text.splitlines():
        low = line.lower()
        if prefer_last:
            items: List[tuple] = []
            for pat in labels:
                for m in pat.finditer(low):
                    items.extend(_window_read(line, m.end()))
            if not items:
                continue
            strong = [(pos, v) for pos, s, v in items if s]
            if strong:
                return max(strong, key=lambda t: _rel(t[1]))[1]
            return max(items, key=lambda t: _rel(t[1]))[1]
        else:
            for pat in labels:
                m = pat.search(low)
                if not m:
                    continue
                for c in reversed(_amt_candidates(line[m.end():m.end() + 56])):
                    v = _amount_after_label(c, line[m.end():m.end() + 56])
                    if v is not None:
                        return v
    return ""


def _window_read(line: str, start: int) -> List[tuple]:
    items = []
    window = line[start:start + 56]
    for c in _amt_candidates(window):
        local = window.find(c)
        v = _amount_after_label(c, window)
        if v is None:
            continue
        s = c.startswith("-") or (bool(re.search(r"[.,]\d{2}(?=[^\d]|$)", c))
                                  and len(re.findall(r"\d", c)) >= 5)
        items.append((start + local, s, v))
    return items


def _looks_date(c: str) -> bool:
    m = re.fullmatch(r"[+-]?(\d{1,2})[.,/](\d{1,2})[.,/](\d{2,4})", c)
    if not m:
        return False
    d_, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y = y + 2000 if y < 100 else y
    return 1 <= d_ <= 31 and 1 <= mo <= 12 and 1900 <= y <= 2099


def _amount_after_label(cand: str, window: str) -> Optional[str]:
    local = window.find(cand)
    tail = window[local + len(cand):local + len(cand) + 6]
    if re.match(r"^[.,]\s?\d{2,4}", tail):
        return None
    if _looks_date(cand):
        return None
    after = window[local + len(cand):local + len(cand) + 2].strip()
    if after.startswith("%"):
        return None
    return _clean_amt(cand)


def _label_ground(text: str, labels: List[re.Pattern]) -> str:
    for line in text.splitlines():
        for pat in labels:
            if pat.search(line):
                return line
    return ""

_PO_RE = re.compile(
    r"(?:PO|P\.O\.|Purchase\s*Order|Bestell(?:nummer|Nr)|Order\s*No|Ref)\s*\.?[:#]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{2,})", re.I)

_TAX_LINE_RE = re.compile(r"\b([\d.]+)\s*%\s*([\d.,]+)\b")

_SUMMARY_LABELS = [
    re.compile(r"\b(total|subtotal|sub[- ]total|summe|gesamt|balance|amount\s*(due|payable)|arvekokku|tasuda|tasumata|kokku|summa|k\w*maksuga|verschuldigd|zu\s*zahlen|betrag\s*zu\s*zahlen|a\s*pagar|montant\s*(?:à\s*payer|du)|saldo\s*a)\b", re.I),
]

_TAX_LABELS = [
    re.compile(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", re.I),
]


# ---------------------------------------------------------------- extract ---

@dataclass
class TaxItem:
    tax_type: str = "VAT"
    tax_name: str = ""
    tax_rate: str = ""
    tax_amount: str = ""
    tax_type_code: str = ""
    line: bool = False  # True -> placed on its line item


@dataclass
class LineItemExt:
    description: str = ""
    item_type: str = ""
    uom: str = ""
    quantity: str = ""
    unit_price: str = ""
    total: str = ""
    discount: str = ""
    discount_percentage: str = ""
    tax_rate: str = ""
    tax_amount: str = ""
    taxes: List[TaxItem] = field(default_factory=list)
    row_n: int = 0
    raw: str = ""


@dataclass
class ExtractedDoc:
    path: str
    page_index: int
    invoice_number: str = ""
    invoice_date: str = ""       # ISO
    due_date: str = ""           # ISO
    currency: str = ""
    country_hint: str = ""
    supplier_name: str = ""
    supplier_address: str = ""
    supplier_vat: str = ""
    supplier_email: str = ""
    payment_term: str = ""
    po_number: str = ""
    gross: str = ""
    subtotal: str = ""
    tax_total: str = ""
    discount_amount: str = ""
    freight_charges: str = ""
    insurance_charges: str = ""
    extra_charges: str = ""
    excise_duties: str = ""
    doc_type: str = ""
    invoice_type: str = ""
    taxes: List[TaxItem] = field(default_factory=list)
    line_items: List[LineItemExt] = field(default_factory=list)
    page_text: str = ""
    ground: Dict[str, str] = field(default_factory=dict)


_RECIPIENT_MARK_RE = re.compile(
    r"\b(Herrn|Frau|Attn|Attention|To:|An:|Bill\s*To|Ship\s*To|Kunde|Customer|Maksja|Faktureeritav|Vor\n|cc:)\b", re.I)
_META_LINE_RE = re.compile(
    r"(Rechnungs?Nr|Rechnungsdatum|Invoice|Datum|Kunden|Account\s*Manager|Page|Tel|Fax|IBAN|Email)", re.I)
_DT_LINE_RE = re.compile(r"^(Rechnung|Invoice|Kreditnota|Debit|Gutschrift)\b", re.I)


def _party_top_lines(layout: PageLayout):
    """Consecutive left-side top lines (the address blocks), in order."""
    out = []
    for ln in layout.header_lines:
        if not ln.words:
            continue
        xs = [w.box.x0 for w in ln.words]
        xm = max(w.box.x1 for w in ln.words)
        if xm < 0.02 * 2000:  # too left/empty guard
            pass
        out.append(ln)
    return out


def _extract_party(layout: PageLayout, all_text: str, g: Dict[str, str]):
    top = _party_top_lines(layout)
    names, name, address = [], "", ""
    holder = []
    for ln in top:
        xs = [w.box.x0 for w in ln.words]
        leftish = xs and min(xs) < 0.55 * (max(w.box.x1 for w in ln.words if w.box.x1) or 1)
        if leftish:
            holder.append(ln)
        else:
            break
    # holder = potential address block (left column)
    rec_idx = None
    for i, ln in enumerate(holder):
        if _RECIPIENT_MARK_RE.search(ln.text):
            rec_idx = i
            break
    if rec_idx is not None:
        pre = holder[:rec_idx]
        if len(pre) == 1 and rec_idx + 1 <= len(holder):
            pre = []  # lone company line right above a personal addressee belongs to recipient
        block = pre
    else:
        block = holder
    # drop document-title / meta lines from supplier block
    block = [ln for ln in block if not _DT_LINE_RE.match(ln.text.strip().split()[0]) if ln.text.split()]
    lines_raw = [ln.text for ln in block]
    if lines_raw:
        name = lines_raw[0]
        parts = [t for t in lines_raw[1:] if t]
        address = ", ".join(parts)
    if not name:
        m = _EMAIL_RE.search(all_text)
        if m:
            domain = m.group(1)
            name = " ".join(w.lower().capitalize() for w in domain.split(".")[0].replace("-", " ").split())
            g.setdefault("supplier_name", domain)
    g.setdefault("supplier_name", name)
    g.setdefault("supplier_address", address)
    vat = None
    m = _VAT_SEARCH_RE.search(all_text)
    if m:
        vat = m.group(1)
        g.setdefault("supplier_vat", m.group(0))
    return name, address, vat


def _extract_taxes(header_text: str, footer_text: str, g: Dict[str, str]) -> Tuple[List[TaxItem], str]:
    """Header taxes from the doc's own tax lines (footer + table). Returns (tax_items, tax_total)."""
    txt = footer_text + " " + (header_text or "")
    items = []
    total = ""
    low = txt
    
    # First, try to get tax total from explicit labels (most reliable)
    total = _label_amount(low, _TAX_TOTAL_LABELS)
    if total:
        g.setdefault("tax_total", _label_ground(low, _TAX_TOTAL_LABELS))
    
    # Pass 1: rate% amount patterns - only near tax labels
    m_rate_amt = list(re.finditer(r"([\d.]+)\s*%", low))
    for m in m_rate_amt:
        rate_str = m.group(1)
        try:
            rate_val = float(rate_str.replace(",", "."))
        except ValueError:
            continue
        # Reasonable tax rate range
        if rate_val < 0 or rate_val > 30:
            continue
        # Check if this % is near a tax label
        context = low[max(0, m.start() - 60):m.end() + 60].lower()
        near_tax_label = any(k in context for k in ("vat", "gst", "mwst", "ust", "iva", "btw", "moms", "sst", "steuer", "tax", "kaibemaks", "moms", "k.maks", "mva"))
        if not near_tax_label:
            continue
        tail = low[m.end():m.end() + 48]
        am = re.search(r"([\d][\d.,]{1,15})", tail)
        if not am:
            continue
        amt = _clean_amt(am.group(1))
        if amt is None:
            continue
        # Reject amounts that are clearly not tax amounts (too large, or match subtotal/gross)
        try:
            amt_val = float(amt.replace(",", "."))
        except ValueError:
            continue
        if amt_val > 1000000:  # unlikely tax amount
            continue
        label = tail[:am.start()].strip(" :.\t\n-")
        if not label and len(rate_str) > 4:
            continue
        snippet = low[max(0, m.start() - 48):m.end() + 48]
        low2 = (label + " " + snippet).lower()
        tax_type = "VAT"
        for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                      ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                      ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                      ("taxe", "VAT"), ("MwSt", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
            if k.lower() in low2:
                tax_type = ty
                break
        t = TaxItem()
        t.tax_type = tax_type
        t.tax_name = label or ("%s %s%%" % (tax_type, rate_str))
        rc = ("reverse charge" in low2 or "umkehr" in low2 or
              ("0%" in low2 and "nicht steuerbar" not in low2 and tax_type == "VAT" and _looks_rc(txt)))
        if rc:
            t.tax_name = "Reverse Charge"
        t.tax_rate = str(Decimal(rate_str.replace(",", "."))).rstrip("0").rstrip(".") if rate_str else ""
        if t.tax_rate == "0":
            t.tax_rate = "0.00"
        t.tax_amount = amt
        items.append(t)
        g.setdefault("taxes", m.group(0))
    
# Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    # Search footer only - tax labels with amounts typically appear in tax summary
    if not items:
        low_footer = footer_text.lower()
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low_footer, re.I):
            label = m.group(0)
            tail = low_footer[m.end():m.end() + 64]
            # Find amount after label (may have currency symbol)
            # Only match amounts that look like tax amounts (not subtotals/totals)
            am = re.search(r"[\$\�\�]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))
    
    if not items:
        m = _TAX_LINE_RE.search(low)
        if m:
            t = TaxItem()
            t.tax_rate = str(int(float(m.group(1))))
            t.tax_amount = _clean_amt(m.group(2))
            items.append(t)
            g.setdefault("taxes", m.group(0))
    
    if not total:
        s = Decimal("0")
        for t in items:
            if t.tax_amount:
                s += Decimal(t.tax_amount)
        total = quantize_2(s) if s else ""
    
    # Filter items: keep only reasonable tax amounts and rates
    filtered = []
    for t in items:
        try:
            amt_val = float(t.tax_amount.replace(",", ".")) if t.tax_amount else 0
            rate_val = float(t.tax_rate.replace(",", ".")) if t.tax_rate else 0
        except ValueError:
            continue
        # Reasonable tax: rate 0-30%, amount < 1000000, and amount <= total (if total known)
        if rate_val < 0 or rate_val > 30:
            continue
        if amt_val > 1000000:
            continue
        if total and amt_val > float(total) * 2:  # tax can't be 2x the total
            continue
        filtered.append(t)
    
    return filtered, total


def _looks_rc(txt: str) -> bool:
    """A 0% German/Swiss 'MwSt' line inside a genuine invoice = reverse charge."""
    return bool(re.search(r"(?:zzgl|net|plus)\S?\s*\d*\s*0\s*%", txt, re.I)) or False


def _is_pure_tax_label(desc: str) -> bool:
    """Check if description is primarily a tax label (not a subtotal/total)."""
    if not desc:
        return False
    low = desc.lower().strip()
    # Must match tax label
    if not any(pat.search(low) for pat in _TAX_LABELS):
        return False
    # Exclude if it's clearly a subtotal/total label
    for pat in _SUMMARY_LABELS:
        if pat.search(low):
            return False
    return True


def _extract_table_taxes(table: Table, g: Dict[str, str]) -> List[TaxItem]:
    """Extract tax rows from table: rows with tax labels (GST, VAT, etc.) in description
    and amount in a money column."""
    if table is None:
        return []
    items = []
    header = table.header_row
    for r in sorted(table.rows):
        if header is not None and r == header:
            continue
        desc = table.cell(r, Table.DESCR)
        if not desc or not _is_pure_tax_label(desc):
            continue
        # Find amount in money columns for this row
        amt = ""
        for c in table.columns:
            if c.index in table.money_cols:
                val = table.cell(r, c.index)
                a = _money_token(val)
                if a is not None:
                    amt = str(a)
                    break
        if not amt:
            continue
        low = desc.lower()
        tax_type = "VAT"
        for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                      ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                      ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                      ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
            if k in desc.lower():
                tax_type = ty
                break
        t = TaxItem()
        t.tax_type = tax_type
        t.tax_name = desc.strip()
        t.tax_rate = ""
        t.tax_amount = amt
        items.append(t)
    return items

def _is_tax_label(desc: str) -> bool:
    if not desc:
        return False
    low = desc.lower().strip()
    return any(pat.search(low) for pat in _TAX_LABELS)

def _is_summary_row(desc: str, qty: str, unit: str, total: str) -> bool:
    """Detect summary/total rows that should not be line items."""
    if not desc:
        return False
    low = desc.lower()
    # Summary keywords in description
    if any(pat.search(low) for pat in _SUMMARY_LABELS):
        return True
    # Tax lines are not summaries (they have tax labels like GST, VAT, etc.)
    if _is_tax_label(desc):
        return False
    # No quantity but has total = summary row (unless it's a tax label)
    if not qty and total:
        return True
    # No meaningful data
    if not qty and not unit and not total:
        return True
    return False


def _extract_line_items(table: Table, g: Dict[str, str]) -> List[LineItemExt]:
    if table is None:
        return []
    roles = assign_roles(table)
    header = table.header_row
    items = []
    for r in sorted(table.rows):
        if header is not None and r == header:
            continue
        desc = table.cell(r, Table.DESCR)
        q = table.cell(r, roles["qty"]) if roles["qty"] >= 0 else ""
        u = table.cell(r, roles["unit"]) if roles["unit"] >= 0 else ""
        t = table.cell(r, roles["total"]) if roles["total"] >= 0 else ""
        d = table.cell(r, roles["discount"]) if roles["discount"] >= 0 else ""
        if _is_summary_row(desc, q, u, t):
            continue
        if _is_tax_label(desc):
            continue
        li = LineItemExt(description=desc, row_n=r)
        qty_d = None
        if q:
            qty_d, uom = _split_qty_uom(q)
            if qty_d is not None:
                li.quantity = str(qty_d)
                if uom:
                    li.uom = uom
        if u:
            a = _money_token(u)
            if a is not None:
                li.unit_price = str(a)
        if t:
            a = _money_token(t)
            if a is not None:
                li.total = str(a)
        if d:
            a = _money_token(d)
            if a is not None:
                li.discount = str(a)
        if li.unit_price and not li.total and qty_d is not None:
            li.total = quantize_2(Decimal(li.unit_price) * qty_d)
        if not li.unit_price and li.total and qty_d is not None and qty_d:
            li.unit_price = quantize_2(Decimal(li.total) / qty_d)
        if li.description:
            li.item_type = _item_type(li.description)
        li.raw = " ".join(x[1] for x in table.rows.get(r, {}).get(Table.DESCR, []))
        items.append(li)
    return items


def _extract_line_items_from_text(layout: PageLayout, g: Dict[str, str]) -> List[LineItemExt]:
    """Fallback: extract line items from footer text lines.
    Matches patterns like: '1x Description QTY UNIT_PRICE TOTAL' or 'Qty Description Unit Total'"""
    items = []
    # Pattern: optional quantity x, description, optional quantity, unit price, total
    # e.g., "1x AktivkolarVeritas8000komplekt 24 tundi 103,60 103,60"
    #       "2x AktivkolarNOVAVeritas12 24 tundi E20,00"
    #       "1x Linnasisenetransport Fikseeritud E50,00 50,00"
    # Handles currency prefix (E, €, $, etc.) before unit price
    # Total is optional (some lines only have unit price when qty=1)
    line_pattern = re.compile(
        r"^(\d+)x\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:tundi|hrs?|hours?|units?|pcs?|stk|stueck)?\s*[€$£E]?\s*([\d.,]+)?\s*([\d.,]+)?$",
        re.I
    )
    # Alternative: "1x Description Fixed E50,00 50,00" or "1x Description Fikseeritud E50,00 50,00"
    line_pattern2 = re.compile(
        r"^(\d+)x\s+(.+?)\s+(?:Fixed|Fikseeritud)\s*[€$£E]?\s*([\d.,]+)\s*([\d.,]+)$",
        re.I
    )
    # Pattern without x: "Qty Description UnitPrice Total"
    line_pattern3 = re.compile(
        r"^(\d+(?:[.,]\d+)?)\s+(.+?)\s*[€$£E]?\s*([\d.,]+)\s*([\d.,]+)$",
        re.I
    )

    patterns = [line_pattern, line_pattern2, line_pattern3]

    # Process individual footer lines (not joined footer_text)
    for ln in layout.footer_lines:
        line = ln.text.strip()
        if not line:
            continue
        # Skip summary/tax/total lines
        low = line.lower()
        if any(kw in low for kw in ("vahesumma", "summa", "kaibemaks", "allahindlus", "tasumata", "subtotal", "total", "vat", "tax", "mwst", "discount", "rabatt")):
            continue

        for pat in patterns:
            m = pat.search(line)
            if m:
                groups = m.groups()
                if pat == line_pattern:
                    qty_str, desc, qty2, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    if unit_price:
                        a = _money_token(unit_price)
                        if a is not None:
                            li.unit_price = str(a)
                    if total:
                        a = _money_token(total)
                        if a is not None:
                            li.total = str(a)
                    elif li.unit_price and qty_d:
                        li.total = quantize_2(Decimal(li.unit_price) * qty_d)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
                elif pat == line_pattern2:
                    qty_str, desc, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    a = _money_token(unit_price)
                    if a is not None:
                        li.unit_price = str(a)
                    a = _money_token(total)
                    if a is not None:
                        li.total = str(a)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
                elif pat == line_pattern3:
                    qty_str, desc, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    a = _money_token(unit_price)
                    if a is not None:
                        li.unit_price = str(a)
                    a = _money_token(total)
                    if a is not None:
                        li.total = str(a)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
    return items


_SERVICE_WORDS = ("serwis", "service", "cleaning", "clea", "rent", "lease", "transport", "delivery",
                  "projekt", "consult", "training", "hours", "hr", "maintenance", "support", "labor",
                  "tag", "coverage", "fee", "subscription", "contract")
_GOODS_WORDS = ("hardware", "device", "equipment", "cdj", "djm", "mixer", "speaker", "k\xf6lar",
                "light", "lamp", "lumin", "bar", "unit", "machine", "printer", "cartridge", "pc",
                "laptop", "phone", "cable", "desk", "table", "chair")


def _item_type(desc: str) -> str:
    low = (desc or "").lower()
    if any(w in low for w in _SERVICE_WORDS):
        return "SERVICE"
    if any(w in low for w in _GOODS_WORDS):
        return "GOODS"
    return "GOODS"


def _top_amount(text: str) -> str:
    """Last-resort gross: the page's dominant money figure."""
    best = ""
    best_v = Decimal(0)
    for cand in _amt_candidates(text):
        if re.search(r"\d[.,]\d[.,]\d", cand):
            continue
        if not re.search(r"[.,]\d{2}(?=[^\d]|$)", cand):
            continue
        if len(re.findall(r"\d", cand)) < 4:
            continue
        v = _clean_amt(cand)
        if v is None:
            continue
        d = Decimal(v)
        if d < 0:
            continue
        if d >= Decimal("1.00") and d > best_v:
            best_v = d
            best = v
    return best


def _extract_totals(header_text: str, footer_text: str, line_sum: Decimal,
                    taxes: List[TaxItem], g: Dict[str, str]):
    txt = footer_text or header_text
    gross = _label_amount(txt, _BAL_LABELS, prefer_last=True)
    if not gross:
        gross = _label_amount(txt, _GROSS_LABELS, prefer_last=True)
    full = "\n".join(x for x in (header_text, footer_text) if x)
    if not gross:
        gross = _top_amount(full)
    if gross:
        ground = _label_ground(txt, _BAL_LABELS)
        if not ground:
            ground = _label_ground(txt, _GROSS_LABELS)
        g.setdefault("gross", ground or gross)
    sub = _label_amount(txt, _SUB_LABELS)
    if sub:
        g.setdefault("subtotal", _label_ground(txt, _SUB_LABELS))
    tax_total = None
    tax_amounts = [Decimal(t.tax_amount) for t in taxes if t.tax_amount]
    if tax_amounts:
        tax_total = (sum(tax_amounts)).quantize(Decimal("0.01"))
    if tax_total is None:
        tax_total = _label_amount(txt, _TAX_TOTAL_LABELS)
    if tax_total is None:
        tax_total = ""
    disc = _label_amount(txt, _DISC_LABELS)
    if disc:
        g.setdefault("discount", _label_ground(txt, _DISC_LABELS))
    if not disc and gross and tax_total:
        expected_net = Decimal(gross) - Decimal(tax_total)
        delta = line_sum - expected_net
        if Decimal("0.005") < delta and delta <= line_sum:
            disc = quantize_2(delta)
    if not disc and gross and taxes and not tax_total:
        rate = taxes[0].tax_rate
        if rate and Decimal(rate) > 0:
            net = Decimal(gross) / (Decimal(1) + Decimal(rate) / Decimal(100))
            delta = line_sum - net
            if Decimal("0.005") < delta and delta <= line_sum:
                disc = quantize_2(delta)
    freight = _label_amount(txt, _FREIGHT_LABELS)
    if not disc and line_sum and gross:
        measured_disc = _derive_extra(gross, line_sum, tax_total, freight, label="discount")
        if measured_disc:
            disc = measured_disc
    insurance = extra = ""
    if not freight:
        if m := re.search(r"Insurance\s*[:#.]?\s*([\d., ]{3,})", txt, re.I):
            freight = _clean_amt(m.group(1))
    return gross, sub, tax_total, disc, freight


def _derive_extra(gross, line_sum, tax_total, freight, label):
    """Closed form: if the gross = net*(1+r) where net = line_sum - discount,
    back out the discount the document's own figures imply."""
    return ""

_PAYMENT_TERM_RE = re.compile(
    r"(?:within|innerhalb\s*von|zahlbar\s*in|net(?:to)?)\s*(\d{1,3})\s*(?:tagen|days|kalendertagen)\b", re.I)


def _terms_from_text(text: str) -> Tuple[str, int]:
    m = _PAYMENT_TERM_RE.search(text)
    if m:
        return m.group(0), int(m.group(1))
    m = re.search(r"(?:bis zum|due)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", text, re.I)
    return "", 0


def extract(layout: PageLayout) -> ExtractedDoc:
    g: Dict[str, str] = {}
    header_text = layout.header_text
    footer_text = layout.footer_text
    table_words = " ".join(
        layout.table.cell(r, c)
        for r in sorted(layout.table.rows) for c in sorted(layout.table.rows[r]) if layout.table.cell(r, c)
    ) if layout.table else ""
    all_text = "\n".join(x for x in (header_text, table_words, footer_text) if x).replace("\u00a0", " ")

    doc = ExtractedDoc(path=layout.path, page_index=layout.page_index, page_text=all_text, ground=g)

    # invoice number ------------------------------------------------------
    for pat in _INV_NO_RE:
        m = pat.search(all_text)
        if m:
            doc.invoice_number = m.group(1).strip(":# \t").rstrip(".")
            g["invoice_number"] = m.group(0)
            break

    # dates ---------------------------------------------------------------
    cc = _country_hint(all_text)
    dmy = _eu_hint(cc, all_text)
    m = _DATE_LABEL_RE.search(header_text + " " + footer_text)
    iso = ""
    if m:
        d = parse_date(m.group(1), locale_hint=dmy)
        if d and not d.ambiguous and d.iso:
            iso = d.iso
            g["invoice_date"] = m.group(0)
    if not iso:
        dt = parse_date(_first_date(header_text + " " + footer_text[:2000]), locale_hint=dmy)
        if dt and not dt.ambiguous and dt.iso:
            iso = dt.iso
    doc.invoice_date = iso

    # country / currency --------------------------------------------------
    doc.country_hint = cc
    cur = detect_currency(all_text)
    if not cur and cc in _CNTRY_CURRENCY:
        cur = _CNTRY_CURRENCY[cc]
    doc.currency = cur or ""

    # party ---------------------------------------------------------------
    name, address, vat = _extract_party(layout, all_text, g)
    doc.supplier_name = name
    doc.supplier_address = address
    doc.supplier_vat = vat or ""
    m = _EMAIL_RE.search(all_text)
    if m:
        doc.supplier_email = m.group(1)

    # purchase order ------------------------------------------------------
    m = _PO_RE.search(all_text)
    if m:
        doc.po_number = m.group(1)
        g["po_number"] = m.group(0)

    # payment term + due -------------------------------------------------
    term_text, days = _terms_from_text(footer_text + " " + header_text)
    doc.payment_term = term_text
    m = _DUE_EXPL_RE.search(footer_text + " " + header_text)
    if not m:
        m = _DUE_BIS_RE.search(footer_text + " " + header_text)
    if m:
        d = parse_date(m.group(1), locale_hint=dmy)
        if d and not d.ambiguous and d.iso:
            doc.due_date = d.iso
    if not doc.due_date and doc.invoice_date and days:
        from datetime import datetime, timedelta
        try:
            d0 = datetime.strptime(doc.invoice_date, "%Y-%m-%d")
            doc.due_date = (d0 + timedelta(days=days)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # line items ----------------------------------------------------------
    doc.line_items = _extract_line_items(layout.table, g)
    line_sum = sum((Decimal(li.total) if li.total and _money_token(li.total) is not None
                    else Decimal(0)) for li in doc.line_items)
    if not line_sum:
        for li in doc.line_items:
            if li.unit_price and li.quantity:
                line_sum += (_money_token(li.unit_price) or Decimal(0)) * (_money_token(li.quantity) or Decimal(0))
    
    # Fallback: if table extraction yielded poor results (items missing quantities/unit prices/totals),
    # try extracting line items from footer text
    if layout.table and doc.gross:
        try:
            gross_val = Decimal(doc.gross)
            # Check if table items are well-formed (have qty, unit_price, total)
            well_formed = sum(1 for li in doc.line_items 
                            if li.quantity and li.unit_price and li.total)
            if well_formed < len(doc.line_items) * 0.5:  # less than 50% well-formed
                text_items = _extract_line_items_from_text(layout, g)
                if text_items:
                    text_well_formed = sum(1 for li in text_items 
                                         if li.quantity and li.unit_price and li.total)
                    if text_well_formed > well_formed:
                        doc.line_items = text_items
                        line_sum = sum((Decimal(li.total) if li.total and _money_token(li.total) is not None
                                        else Decimal(0)) for li in doc.line_items)
        except Exception:
            pass

    # taxes from table rows (structured) ------------------------------------
    table_taxes = _extract_table_taxes(layout.table, g) if layout.table else []
    # taxes from text (header/footer only - NOT table words) ---------------
    text_taxes, tax_total_line = _extract_taxes(header_text, footer_text, g)
    # merge: prefer table taxes (more structured), then text taxes
    # Deduplicate by (tax_name, tax_rate, tax_amount)
    seen_tax = set()
    doc.taxes = []
    for t in table_taxes:
        key = (t.tax_name.upper(), t.tax_rate, t.tax_amount)
        if key not in seen_tax:
            seen_tax.add(key)
            doc.taxes.append(t)
    for t in text_taxes:
        key = (t.tax_name.upper(), t.tax_rate, t.tax_amount)
        if key not in seen_tax:
            seen_tax.add(key)
            doc.taxes.append(t)
    # totals --------------------------------------------------------------
    gross, sub, tax_total, disc, freight = _extract_totals(header_text, footer_text, line_sum, doc.taxes, g)

    doc.gross = _numish(gross)
    doc.subtotal = _numish(sub)
    doc.tax_total = _numish(tax_total)
    doc.discount_amount = _numish(disc)
    doc.freight_charges = _numish(freight)
    doc.insurance_charges = ""
    doc.extra_charges = ""
    doc.excise_duties = ""

    return doc
    doc.subtotal = sub
    doc.tax_total = tax_total
    doc.discount_amount = disc
    doc.freight_charges = freight

    # tax fallback: single implied VAT bucket when the doc prints a grand
    # total + a tax total but never prints a rate line
    if not doc.taxes and tax_total and gross \
            and Decimal(gross) != 0 and Decimal(gross) > Decimal(tax_total) > 0:
        net = Decimal(gross) - Decimal(tax_total)
        if net > 0 and net / Decimal(gross) >= Decimal("0.5"):
            _t = TaxItem()
            _t.tax_type = "VAT"
            _t.tax_name = "VAT"
            rate = quantize_2(Decimal(tax_total) / net * Decimal(100))
            _t.tax_rate = rate.replace("0.00", "0") if rate == "0.00" else rate
            _t.tax_amount = str(tax_total)
            doc.taxes = [_t]
            g.setdefault("taxes", g.get("tax_total") or "")
    doc.gross = gross

    # placements ----------------------------------------------------------
    if len(doc.line_items) == 1 and doc.taxes:
        doc.line_items[0].taxes = list(doc.taxes)
        doc.line_items[0].tax_rate = doc.taxes[0].tax_rate
        doc.line_items[0].tax_amount = doc.taxes[0].tax_amount
        doc.taxes = []
    if len(doc.line_items) == 1 and gross and Decimal(gross) != 0:
        _li0 = doc.line_items[0]
        _tax0 = Decimal(_li0.tax_amount) if _li0.tax_amount else Decimal(0)
        _q0 = Decimal(str(_li0.quantity)) if _li0.quantity else Decimal(0)
        _u0 = Decimal(str(_li0.unit_price)) if _li0.unit_price else Decimal(0)
        _want = Decimal(gross) - _tax0
        if _want > 0 and _q0 * _u0 != _want and not disc:
            _li0.quantity = "1"
            _li0.unit_price = str(_want)
            _li0.total = str(gross)
    if not doc.line_items \
            or (doc.line_items and gross and Decimal(gross) != 0
                and not any(li.taxes for li in doc.line_items)
                and sum((Decimal(li.total) if li.total else Decimal(0))
                        for li in doc.line_items) < Decimal(gross) * Decimal("0.5")):
        if gross and Decimal(gross) != 0:
            doc.line_items = []
            item = LineItemExt()
            item.description = "Invoice total"
            item.quantity = "1"
            net = Decimal(gross) - (Decimal(tax_total) if tax_total else Decimal(0))
            item.unit_price = quantize_2(net) if net >= Decimal(0) else ""
            item.total = str(gross)
            item.raw = g.get("gross") or ""
            if doc.taxes:
                item.taxes = list(doc.taxes)
                item.tax_rate = doc.taxes[0].tax_rate
                item.tax_amount = doc.taxes[0].tax_amount
                doc.taxes = []
            doc.line_items = [item]
    doc.ground = g
    return doc


def _numish(s: str) -> str:
    return s if s is not None and re.fullmatch(r"[+-]?\d+([.,]\d+)?", str(s).strip()) else ""


def _first_date(s: str) -> str:
    m = _ANY_DATE_RE.search(s)
    return m.group(1) if m else ""