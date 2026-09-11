"""resolve.py - master-data lookup with scored matching."""
from __future__ import annotations
import json, os, re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

M_DIR = Path(__file__).resolve().parent.parent / "master_data"

def _load(name):
    return json.load(open(M_DIR / name, encoding="utf-8"))

_sup_data = None
_cob_data = None
_pt_data = None
_tax_data = None
_po_data = None


def _sup():
    global _sup_data
    if _sup_data is None:
        _sup_data = _load("suppliers.json")["suppliers"]
    return _sup_data


def _cob():
    global _cob_data
    if _cob_data is None:
        _cob_data = _load("chart_of_books.json")["companies"]
    return _cob_data


def _pt():
    global _pt_data
    if _pt_data is None:
        _pt_data = _load("payment_terms.json")["payment_terms"]
    return _pt_data


def _tax():
    global _tax_data
    if _tax_data is None:
        _tax_data = _load("tax_master.json")["taxes"]
    return _tax_data


def _po():
    global _po_data
    if _po_data is None:
        _po_data = _load("po_master.json")["purchase_orders"]
    return _po_data


# ── normalisation helpers ────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _score_name(name: str, candidate: str) -> float:
    n = _norm(name)
    c = _norm(candidate)
    if not n or not c:
        return 0
    if n == c:
        return 1
    if c in n or n in c:
        return 0.9
    parts = c.split()
    hits = sum(p in n for p in parts)
    return hits / len(parts) * 0.85 if parts else 0


# ── public API ───────────────────────────────────────────────────────────────

def resolve_supplier(name: str = "", vat: str = "", currency: str = "") -> Dict[str, str]:
    best, best_s = None, 0
    for s in _sup():
        sc = _score_name(name, s["name"])
        if vat and s.get("vat_id") and _norm(vat) == _norm(s["vat_id"]):
            sc = max(sc, 0.98)
        if currency and s.get("country") and currency != _guess_cc(s["country"]):
            sc *= 0.6
        if sc > best_s:
            best, best_s = s, sc
    if best and best_s >= 0.45:
        return {"id": best["supplier_id"], "name": best["name"], "vat_id": best.get("vat_id", ""),
                "address": best.get("address", ""), "country": best.get("country", ""),
                "bank_account": best.get("bank_iban", ""), "email": best.get("email", "")}
    return {"id": "", "name": name or "", "vat_id": vat or "", "address": "", "country": "",
            "bank_account": "", "email": ""}


def _guess_cc(country_code):
    m = {"DE": "EUR", "EE": "EUR", "PT": "EUR", "ZA": "ZAR", "GH": "GHS",
         "MY": "MYR", "GB": "GBP", "KE": "KES", "NL": "EUR", "FR": "EUR",
         "SE": "SEK", "DK": "DKK", "PL": "PLN", "US": "USD", "CA": "CAD",
         "VN": "VND", "RO": "RON", "CH": "CHF", "TH": "THB", "SG": "SGD", "IN": "INR"}
    return m.get(country_code.upper()[:2], "")


# buyer = invoice_to address match from chart_of_books

def _strip(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()


def resolve_buyer(address_text: str = "", country_hint: str = "", tenant_id: str = "") -> Dict[str, str]:
    """Match address_text against chart_of_books locations' invoice_to_address."""
    addr_norm = _norm(address_text)
    best, best_s = None, 0
    for company in _cob():
        for bu in company.get("business_units", []):
            for loc in bu.get("locations", []):
                inv = loc.get("invoice_to_address", "")
                loc_norm = _norm(inv)
                if not inv or not addr_norm:
                    continue
                if loc_norm in addr_norm or addr_norm in loc_norm:
                    sc = 0.99
                else:
                    parts = _strip(inv)
                    hits = sum(any(p in addr_norm for p in _strip(seg)) for seg in inv.split(",") if seg.strip())
                    sc = hits / max(1, len(inv.split(",")))
                if sc > best_s:
                    best_s, best = sc, {
                        "company_code": company["company_code"],
                        "business_unit_code": bu["business_unit_code"],
                        "location_code": loc["location_code"],
                        "full_address": loc.get("invoice_to_address", ""),
                        "invoice_to_address": loc.get("invoice_to_address", ""),
                    }
    if best and best_s >= 0.55:
        return best
    return {"company_code": "", "business_unit_code": "", "location_code": "",
            "full_address": "", "invoice_to_address": ""}


def resolve_payment_terms(text: str = "", days: int = 0) -> Dict[str, str]:
    low = text.lower()
    best, best_s = None, 0
    for pt in _pt():
        for alias in pt.get("text_aliases", []):
            if alias.lower() in low:
                sc = len(alias)
                if days and pt.get("days") == days:
                    sc += 5
                if sc > best_s:
                    best_s, best = sc, pt
    if best:
        return {"id": best["payment_term_id"]}
    if days:
        for pt in _pt():
            if pt.get("days") == days:
                return {"id": pt["payment_term_id"]}
    return {"id": ""}


def resolve_po_ids(po_numbers: List[str]) -> List[Dict[str, str]]:
    out = []
    for num in po_numbers:
        if not num:
            continue
        n = _norm(num)
        found = None
        for p in _po():
            if _norm(p.get("po_id", "")) == n or _norm(p.get("po_number", "")) == n:
                found = p["po_id"]
                break
        out.append({"id": found or ""})
    return out or [{"id": ""}]


def resolve_taxes(tax_items: list, country_hint: str = "") -> List[Dict[str, str]]:
    out = []
    for t in tax_items:
        code = _match_tax_code(float(t.tax_rate or 0), country_hint, t.tax_type, t.tax_name)
        out.append({
            "tax_type": t.tax_type or "VAT",
            "tax_name": t.tax_name or "",
            "tax_rate": t.tax_rate or "",
            "tax_amount": t.tax_amount or "",
            "tax_type_code": code,
        })
    return out


def _match_tax_code(rate: float, country: str, tax_type: str, name: str) -> str:
    rate_int = int(round(rate * 10))
    low = (name or "").lower()
    best, best_s = None, 0
    for tx in _tax():
        if country and tx.get("country", "").upper() != country.upper():
            continue
        if int(float(tx.get("rate", 0)) * 10) == rate_int:
            s = 1
            if tax_type and tx.get("tax_type", "").lower() == tax_type.lower():
                s += 0.5
            if any(k in low for k in (tx.get("name", "").lower().split()[:2])):
                s += 0.3
            if s > best_s:
                best_s, best = s, tx["code"]
    return best or ""

