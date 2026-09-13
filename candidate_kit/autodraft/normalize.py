"""Currency / number / date normalisation with strict ambiguity rules.

The ERP does no locale parsing: numbers out are dot-decimal, dates out are ISO.
Locale is decided per-number (separator patterns), with currency and document
context as corroboration. When a value cannot be disambiguated, we return None
rather than guess — rule 1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Set, Tuple

# ── currency ─────────────────────────────────────────────────────────────────

# Symbols use \u escapes so the source file stays pure ASCII on every platform.
_CURRENCY_TABLE = [
    # (symbol_or_code, iso3)
    ("\u20ac", "EUR"), ("EUR", "EUR"), ("eur", "EUR"),
    ("$", "USD"), ("USD", "USD"), ("US$", "USD"),
    ("\u00a3", "GBP"), ("GBP", "GBP"), ("gbp", "GBP"),
    ("R", "ZAR"), ("ZAR", "ZAR"), ("zar", "ZAR"),
    ("GH\u20b5", "GHS"), ("GH\u00a2", "GHS"), ("GHS", "GHS"),
    ("KSh", "KES"), ("KES", "KES"),
    ("RM", "MYR"), ("MYR", "MYR"), ("myr", "MYR"),
    ("\u00a5", "JPY"), ("JPY", "JPY"),
    ("\u20b9", "INR"), ("INR", "INR"),
]

# note: ordering matters; longest symbol first
_CURRENCY_RE = re.compile(
    r"(US\$|GH\u20b5|GH\u00a2|KSh|KES|MYR|ZAR|GHS|GBP|EUR|USD|INR|JPY|RM|"
    r"\u20ac|\$|\u00a3|\u00a5|\u20b9|R)",
    re.IGNORECASE,
)

_STRONG_SYM = None  # placeholder (kept intentionally unused)


def detect_currency(text: str) -> Optional[str]:
    """Return the strongest ISO-3 currency signal in the text.

    Signal priority (strongest first):
      * ISO code words (EUR, USD, GHS, ...)
      * unambiguous symbols / symbol-digraphs (US$, GH\u20b5, KSh, RM, ...)
      * lone single-char symbols (EUR \u20ac, USD $, GBP \u00a3), except ZAR "R"
        which is only accepted when glued to a digit (else "Rechnung" wins).
    """
    iso_m = re.findall(
        r"\b(?:EUR|USD|GBP|ZAR|GHS|KES|MYR|JPY|INR)\b", text, flags=re.IGNORECASE
    )
    if iso_m:
        return iso_m[0].upper()
    strong = re.findall(
        r"(?:US\$|GH\u20b5|GH\u00a2|KSh|KES|MYR|RM|EUR|\u20ac|\$|\u00a3|\u00a5|\u20b9)",
        text,
    )
    if strong:
        lowest = strong[0]
        for s in strong:
            if len(s) > len(lowest):
                lowest = s
        for s, code in _CURRENCY_TABLE:
            if s == lowest:
                return code
    if re.search(r"R\s?\d", text):
        return "ZAR"
    return None


# ── number parsing ───────────────────────────────────────────────────────────

_NUM_RE = re.compile(
    r"[+-]?\s*"
    r"(?:\d{1,3}(?:[\.,]\d{3})+|\d+)"
    r"(?:[\.,]\d+)?"
)


@dataclass
class Amount:
    value: Decimal
    text: str
    ambiguous: bool = False


def parse_amount(token: str) -> Optional[Amount]:
    """Parse a single printed number into a Decimal (dot-decimal).

    Decides the locale from the separator pattern:
      * 1.234,56  -> thousands '.', decimal ','
      * 1,234.56  -> thousands ',', decimal '.'
      * 1234.56   -> dot decimal (2 trailing digits)
      * 70.000    -> thousands dot (3 trailing digits) => 70000
      * 1234      -> integer
    Returns None when not parseable, or when ambiguous (e.g. 1.2345).
    """
    if token is None:
        return None
    if isinstance(token, (int, float, Decimal)):
        token = str(token)
    s = str(token).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    
    # Strip leading currency symbols and other non-numeric prefix
    # Keep only leading sign (+/-) and digits/separators
    s = re.sub(r'^[^+\-\d]*', '', s)
    if not s:
        return None
    
    # Check for negative sign
    neg = s.lstrip().startswith("-")
    if neg:
        s = s.lstrip()[1:]  # Remove the minus sign
    
    # Find the numeric part using regex
    m = re.search(r'[-+]?\d[\d.,]*', s)
    if not m:
        return None
    s = m.group(0).strip()
    
    digits = [c for c in s if c.isdigit()]
    if not digits:
        return None

    # isolate the numeric core
    body = s.replace(",", "|").replace(".", "|").split("|")
    # body contains segments of digits
    segs = [b for b in body if b.strip() != ""]
    if len(segs) == 1:
        try:
            v = Decimal(segs[0])
        except InvalidOperation:
            return None
        return Amount(-v if neg else v, token)
    # multiple segments => separators at play
    last = segs[-1]
    if len(last) == 2:
        # last sep is a decimal separator (2 decimals)
        if len(segs) == 2 and len(segs[0]) in (1, 2, 3):
            # e.g. 73,00 or 292,00 or 1.234,56 -> decimal comma; thousands dot ok
            # decide which separator is decimal: the one adjacent to last segment
            dec_sep = s.rfind(",") if s.rfind(",") > s.rfind(".") else s.rfind(".")
            if dec_sep < 0:
                return None
            int_part = s[:dec_sep].replace(",", "").replace(".", "")
            try:
                v = Decimal(int_part) + Decimal(last) / Decimal(100)
            except InvalidOperation:
                return None
            return Amount(-v if neg else v, token)
        # multiple group seps then a 2-digit last: European-ish or US-ish
        # e.g. 1.234.567,89 -> keep
        # decide: score by alignment of the 'other' separator
        # we try Europe-first: last sep is decimal
        dec_sep = s.rfind(",") if s.rfind(",") > s.rfind(".") else s.rfind(".")
        int_part = s[:dec_sep].replace(",", "").replace(".", "")
        frac_part = Decimal(last) if last.isdigit() and len(last) == 2 else Decimal(0)
        try:
            v = Decimal(int_part) + frac_part / Decimal(100)
        except InvalidOperation:
            return None
        return Amount(-v if neg else v, token, ambiguous=(s.rfind(",") == -1))
    elif len(last) == 3 and len(segs) > 1:
        # last sep is a thousands separator: 70.000, 1.234.567
        int_str = "".join(segs)
        try:
            v = Decimal(int_str)
        except InvalidOperation:
            return None
        return Amount(-v if neg else v, token)
    elif len(last) == 3 and len(segs) == 2 and len(segs[0]) in (1, 2):
        # "7.340" -> ambiguous: could be decimal (7.34c? no) -> group: 7340
        # only in currencies with 3 decimals (BHD etc.) => treat as thousands
        try:
            v = Decimal("".join(segs))
        except InvalidOperation:
            return None
        return Amount(-v if neg else v, token, ambiguous=True)
    else:
        # 4+ digit last segment is almost certainly a code/figure, skip
        return None


def parse_amount_any(token: str) -> Optional[Amount]:
    return parse_amount(token)


# ── dates ────────────────────────────────────────────────────────────────────

_DATE_RE = re.compile(
    r"\b(\d{1,4})[\-\./](\d{1,2})[\-\./](\d{1,4})\b"
)

# Additional pattern for formats like "30Apr2025", "31May2025", "15January2026"
_DATE_ALPHA_RE = re.compile(
    r"\b(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)(\d{2,4})\b", re.I
)

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class DateResolved:
    iso: str  # YYYY-MM-DD
    text: str
    ambiguous: bool = False


def parse_date(token: str, locale_hint: str = "", context: str = "") -> Optional[DateResolved]:
    """Parse a printed date to ISO. Resolves the day/month order from the
    token itself and, when still ambiguous, from label semantics passed in
    `context` (e.g. a label word like 'invoice date' means the US mm/dd is
    plausible only for US suppliers) — never guessed without a signal."""
    
    # Try alpha month format first (e.g., "30Apr2025", "31May2025")
    m_alpha = _DATE_ALPHA_RE.search(token.strip())
    if m_alpha:
        day = int(m_alpha.group(1))
        month_str = m_alpha.group(2).lower()[:3]
        year_str = m_alpha.group(3)
        month = _MONTH_MAP.get(month_str)
        if month:
            year = int(year_str)
            if year < 100:
                year = 2000 + year if (2000 + year) <= 2050 else 1900 + year
            try:
                iso = f"{year:04d}-{month:02d}-{day:02d}"
                return DateResolved(iso, token)
            except ValueError:
                pass
    
    m = _DATE_RE.search(token.strip())
    if m is None:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)

    if len(a) == 4:
        # YYYY-...
        try:
            iso = f"{int(a):04d}-{int(b):02d}-{int(c):02d}"
            return DateResolved(iso, token)
        except ValueError:
            return None
    if len(c) == 4:
        # DD/MM/YYYY or MM/DD/YYYY
        first, second = int(a), int(b)
        if first > 12:
            iso = f"{int(c):04d}-{second:02d}-{first:02d}"
            return DateResolved(iso, token)  # DD.MM
        if second > 12:
            iso = f"{int(c):04d}-{first:02d}-{second:02d}"
            return DateResolved(iso, token)  # MM.DD
        if first == second:
            iso = f"{int(c):04d}-{first:02d}-{first:02d}"
            return DateResolved(iso, token)  # identical order, never ambiguous
        hint = locale_hint.strip().lower()
        if hint in ("dmy", "dd/mm", "de", "eu", "euro"):
            iso = f"{int(c):04d}-{second:02d}-{first:02d}"
            return DateResolved(iso, token)  # day-first under EU hint
        if hint in ("mdy", "us", "en", "usa"):
            iso = f"{int(c):04d}-{first:02d}-{second:02d}"
            return DateResolved(iso, token)
        # both <=12 -> ambiguous; use hint
        ctx = context.lower()
        if "month" in ctx or ("dd/mm" in ctx):
            iso = f"{int(c):04d}-{first:02d}-{second:02d}"
            return DateResolved(iso, token, ambiguous=first > 6 and second <= 6)
        # default: if the document is EU-style (dot-decimal governs?) we can't
        # know days; report ambiguous.
        return DateResolved("", token, ambiguous=True)
    if len(a) in (1, 2) and len(c) in (1, 2):
        # DD.MM.YY
        first, second = int(a), int(b)
        yr = int(c)
        year = 2000 + yr if (2000 + yr) <= 2050 else 1900 + yr
        if first > 12:
            return DateResolved(f"{year:04d}-{second:02d}-{first:02d}", token)
        if first == second:
            return DateResolved(f"{year:04d}-{first:02d}-{first:02d}", token)
        if locale_hint.strip().lower() in ("dmy", "de", "eu", "euro"):
            return DateResolved(f"{year:04d}-{second:02d}-{first:02d}", token)
        return DateResolved("", token, ambiguous=True)
    return None


# ── helpers for resolving full rows ──────────────────────────────────────────

def quantize_2(v: Decimal) -> Decimal:
    """2-decimal rounding as the ERP would; use quantize with ROUND_HALF_UP."""
    from decimal import ROUND_HALF_UP

    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)