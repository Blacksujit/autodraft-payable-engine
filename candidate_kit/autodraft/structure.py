"""Structure: regions, columns, tables. Purely geometric, ratio-based.

Owns the page's spatial organisation:
  * words -> lines -> text rows (see geom)
  * header / footer rows vs a table region
  * column-band detection inside the table (so we can map cells->roles)

The table detector uses geometric invariants only:
  * clean numeric tokens are digits + separators (optionally a currency
    symbol) — dates, VAT ids, glued labels never qualify;
  * money bands = column bands holding a token with a decimal separator;
  * description = the *region* strictly left of the leftmost column band,
    and a valid data row's description word must sit within tolerance of the
    most common leftmost x0 across money-bearing rows — so right-anchored
    totals / tax labels (which sit in the columns region) and stray margin
    labels are never taken as descriptions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from autodraft.geom import Box, Line, Word, cluster_lines, group_lines_by_bands
from autodraft.normalize import parse_amount

_INTLIKE_RE = re.compile(r"^\d{1,9}(?:[\.,]\d{0,2})?(?:[\sx×X*]+\S.*)?$")

# Summary/total row labels (multilingual) - used to filter out footer summaries from table detection
_SUMMARY_LABELS = [
    re.compile(r"\b(kokku|vahesumma|summa|subtotal|sub-total|total|gesamt|balance|amount\s*(due|payable)|arvekokku|tasuda|tasumata|summa|k\w*maksuga|verschuldigd|zu\s*zahlen|betrag\s*zu\s*zahlen|a\s*pagar|montant\s*(?:à\s*payer|du)|saldo\s*a|summe|sum\b)\b", re.I),
]

_TAX_LABELS = [
    re.compile(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax|kaibemaks|moms)\b", re.I),
]


def _strip_currency(tok: str) -> str:
    out = []
    for ch in tok:
        if ch.isdigit() or ch in ".,-+":
            out.append(ch)
    return "".join(out)


def _is_summary_label(desc: str) -> bool:
    """Check if description is a summary/total label."""
    if not desc:
        return False
    low = desc.lower().strip()
    return any(pat.search(low) for pat in _SUMMARY_LABELS)


def _is_tax_label(desc: str) -> bool:
    """Check if description is a tax label."""
    if not desc:
        return False
    low = desc.lower().strip()
    return any(pat.search(low) for pat in _TAX_LABELS)


def _strip_currency(tok: str) -> str:
    out = []
    for ch in tok:
        if ch.isdigit() or ch in ".,-+":
            out.append(ch)
    return "".join(out)


def clean_numeric(tok: str) -> bool:
    t = tok.strip()
    if not t:
        return False
    s = _strip_currency(t)
    if not any(c.isdigit() for c in s):
        return False
    if any(ch.isalpha() for ch in tok):
        return False
    # Check for multiple decimal separators
    dot_count = s.count('.')
    comma_count = s.count(',')
    if dot_count > 1 or comma_count > 1:
        return False
    if dot_count == 1 and comma_count == 1:
        # Both present - ambiguous, but could be valid
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        if abs(last_dot - last_comma) <= 1:
            return False  # Too close together
    return True


def amount_value(tok: str):
    a = parse_amount(tok)
    return None if a is None else a.value


def _has_decimal(tok: str) -> bool:
    return any(c in _strip_currency(tok) for c in ".,")


def intlike_number(word: Word):
    """Parse a quantity-ish token: pure integer or integer+unit (e.g. '4 Std.')."""
    t = " ".join(word.text.split())
    if _INTLIKE_RE.match(t):
        a = parse_amount(t[:8])  # the leading number
        if a is None:
            return None
        return a.value
    return None


def _numeric_word(word: Word):
    if clean_numeric(word.text):
        v = amount_value(word.text)
        if v is not None:
            return v
    return intlike_number(word)


@dataclass
class Column:
    index: int
    center: float
    x0: float
    x1: float
    rows: Dict[int, List[Tuple[Box, str]]] = field(default_factory=dict)


@dataclass
class Table:
    y0: float
    y1: float
    columns: List[Column] = field(default_factory=list)
    # rows: global row index -> {column index -> [(Box, text)]}
    rows: Dict[int, Dict[int, List[Tuple[Box, str]]]] = field(default_factory=dict)
    DESCR = -1  # virtual column for the description region
    header_row: Optional[int] = None
    money_cols: List[int] = field(default_factory=list)
    desc_edge: float = 0.0

    def col(self, i: int) -> Optional[Column]:
        for c in self.columns:
            if c.index == i:
                return c
        return None

    def cell(self, row: int, col: int) -> str:
        toks = self.rows.get(row, {}).get(col, [])
        if not toks:
            return ""
        toks = sorted(toks, key=lambda tb: tb[0].x0)
        seen, out = set(), []
        for bx, t in toks:
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
        return " ".join(out)


@dataclass
class PageLayout:
    path: str
    page_index: int
    header_lines: List[Line] = field(default_factory=list)
    footer_lines: List[Line] = field(default_factory=list)
    body_lines: List[Line] = field(default_factory=list)
    table: Optional[Table] = None

    @property
    def header_text(self) -> str:
        return " ".join(ln.text for ln in self.header_lines)

    @property
    def footer_text(self) -> str:
        return " ".join(ln.text for ln in self.footer_lines)

    @property
    def page_text(self) -> str:
        chunks = [self.header_text]
        if self.table is not None:
            for r in sorted(self.table.rows):
                for c in sorted(self.table.rows[r]):
                    t = self.table.cell(r, c)
                    if t:
                        chunks.append(t)
        chunks.append(self.footer_text)
        return "\n".join(chunks)


def _cluster_centers(centers: List[float], tol: float) -> List[List[float]]:
    clusters: List[List[float]] = []
    for c in sorted(centers):
        if clusters and abs(clusters[-1][-1] - c) <= tol:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    return clusters


# ── main entry ───────────────────────────────────────────────────────────────

def build_layout(path: str, page_index: int, words: List[Word]) -> PageLayout:
    lines = cluster_lines(words)
    rows = group_lines_by_bands(lines)
    layout = PageLayout(path=path, page_index=page_index)
    if not rows:
        return layout

    def row_has_money(row: List[Line]) -> bool:
        for ln in row:
            for w in ln.words:
                if clean_numeric(w.text) and amount_value(w.text) is not None and _has_decimal(w.text):
                    return True
        return False

    numeric_rows = [row_has_money(r) for r in rows]
    best_start = best_end = -1
    run_start = -1
    for i, is_num in enumerate(numeric_rows):
        if is_num:
            if run_start < 0:
                run_start = i
        else:
            if run_start >= 0 and (i - 1) - run_start + 1 > best_end - best_start:
                best_start, best_end = run_start, i - 1
            run_start = -1
    if run_start >= 0 and len(rows) - 1 - run_start + 1 > best_end - best_start:
        best_start, best_end = run_start, len(rows) - 1

    if best_start >= 0 and best_end - best_start >= 0:
        has_header = False
        with_header = best_start
        if best_start > 0:
            n_words = sum(len(ln.words) for ln in rows[best_start - 1])
            if n_words >= 3:
                with_header = best_start - 1
                has_header = True
        table, data_rows_used = _build_table(rows, with_header, best_end, has_header)
        if table is not None:
            layout.table = table
            layout.table.header_row = best_start if with_header == best_start else with_header
            layout.header_lines = [ln for r in rows[:with_header] for ln in r]
            layout.footer_lines = [ln for r in rows[data_rows_used + 1 :] for ln in r]
            return layout

    layout.header_lines = [ln for r in rows[:2] for ln in r]
    layout.footer_lines = [ln for r in rows[-2:] for ln in r]
    layout.body_lines = [ln for r in rows[2:-2] for ln in r] if len(rows) > 4 else list(rows)
    return layout


def _build_table(rows: List[List[Line]], start: int, end: int, has_header: bool = False):
    run = rows[start : end + 1]
    words = [w for r in run for ln in r for w in ln.words]
    if not words:
        return None, start - 1

    xmin = min(w.box.x0 for w in words)
    xmax = max(w.box.x1 for w in words)
    width = max(1e-9, xmax - xmin)
    tol = max(4.0, 0.03 * width)

    num_words = [w for w in words if _numeric_word(w) is not None]
    if not num_words:
        return None, start - 1

    # column bands from x0 of numeric words
    centers = [w.box.x0 for w in num_words]
    bands = _cluster_centers(centers, tol)
    columns = [
        Column(i, sum(b) / len(b), min(b) - tol / 2, max(b) + tol / 2, {})
        for i, b in enumerate(bands)
    ]
    money_cols = [
        c.index
        for c in columns
        if any(
            clean_numeric(w.text) and amount_value(w.text) is not None and _has_decimal(w.text)
            for w in num_words
            if abs(w.box.x0 - c.center) <= tol
        )
    ]
    if not columns:
        return None, start - 1

    leftmost_money_band = min(c.center for c in columns if c.index in money_cols)
    desc_x1 = leftmost_money_band - tol  # description region boundary

    def assign(w: Word) -> Tuple[Optional[int], bool]:
        """Return (column index, is_money_band). desc region -> DESCR."""
        if w.box.x0 < desc_x1:
            return Table.DESCR, False
        best, bd = None, None
        for c in columns:
            d = abs(w.box.x0 - c.center)
            if bd is None or d < bd:
                bd, best = d, c.index
        if best is not None and bd <= tol:
            return best, best in money_cols
        # fallback: short labels between bands (e.g. "Menge")
        best2, bd2 = None, None
        for c in columns:
            d = abs(w.box.cx - c.center)
            if bd2 is None or d < bd2:
                bd2, best2 = d, c.index
        if best2 is not None and bd2 <= 1.6 * tol:
            return best2, best2 in money_cols
        if w.box.x0 < xmin + tol:
            return Table.DESCR, False
        return None, False

    occupancy: Dict[int, Dict[int, List[Tuple[Box, str]]]] = {}
    for r_i, r in enumerate(run):
        key = start + r_i
        row_map: Dict[int, List[Tuple[Box, str]]] = {}
        for ln in r:
            for w in ln.words:
                col, is_money = assign(w)
                if col is not None:
                    row_map.setdefault(col, []).append((w.box, w.text))
        occupancy[key] = row_map

    # description edge = mode of leftmost word x0 among candidate data rows
    # (rows with a money-band word AND a description anchor), header row
    # excluded. Exclude pure integer words (likely item codes) and summary rows.
    leftmost = []
    for key, row_map in occupancy.items():
        if key == start:
            continue
        if not any(i >= 0 and i in money_cols for i in row_map):
            continue
        if not row_map.get(Table.DESCR):
            continue
        # Filter out summary/total rows from desc edge computation
        desc_texts = [tx for _, tx in row_map[Table.DESCR]]
        combined_desc = " ".join(desc_texts).strip()
        if _is_summary_label(combined_desc):
            continue  # Skip footer summary rows
        # Filter out pure integer tokens (likely item codes) and short codes from desc anchor
        # Use only words containing letters (actual description text)
        desc_xs = []
        for bx, tx in row_map[Table.DESCR]:
            stripped = tx.strip()
            if stripped.isdigit():
                continue
            # Skip short codes (2-3 chars, all letters like "YM", "KG", "PC")
            if len(stripped) <= 3 and stripped.isalpha():
                continue
            if any(c.isalpha() for c in stripped):
                desc_xs.append(bx.x0)
        if desc_xs:
            leftmost.append(min(desc_xs))
    if not leftmost:
        return None, start - 1
    # tolerance-aware mode: cluster candidates, take the densest cluster
    lc = _cluster_centers(sorted(leftmost), tol)
    lc.sort(key=len, reverse=True)
    desc_edge = sum(lc[0]) / len(lc[0])

    def is_data_row(key: int, row_map: Dict[int, List[Tuple[Box, str]]]) -> bool:
        if not row_map:
            return False
        if not any(i >= 0 and i in money_cols for i in row_map):
            return False
        for toks in row_map.get(Table.DESCR, []):
            bx, tx = toks
            if abs(bx.x0 - desc_edge) <= tol:
                return True
        return False

    table = Table(
        y0=run[0][0].box.y0,
        y1=run[-1][-1].box.y1,
        columns=columns,
        money_cols=money_cols,
        desc_edge=desc_edge,
    )
    max_data_row = start - 1
    for key in sorted(occupancy):
        if key == start and has_header:
            if occupancy[key]:
                table.rows[key] = occupancy[key]
            continue
        if is_data_row(key, occupancy[key]):
            table.rows[key] = occupancy[key]
            max_data_row = max(max_data_row, key)
    if not table.rows:
        return None, start - 1
    return table, max_data_row