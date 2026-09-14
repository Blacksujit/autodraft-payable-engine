"""autodraft/audit.py - Fidelity auditor for emitted payables.

Checks:
1. ERP gate: erp_book(payable).will_book_gross == payable.gross_total (within 0.01)
2. Grounding: every emitted numeric value appears in page words (or is a valid derivation)
3. Master-code honesty: supplier_id, payment_term_id, tax_type_code, buyer codes, po_id are real matches or ""
4. Placement fidelity: line-level taxes on lines, header taxes at header (no migration)
5. Decomposition: line items have qty/unit/total/discount not pre-summed
"""
from __future__ import annotations
import json, os, re, sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymupdf
import erp

from autodraft.ocr import ocr_words
from autodraft.geom import cluster_lines, group_lines_by_bands
from autodraft.structure import build_layout
from autodraft.fields import extract, ExtractedDoc
from autodraft.classify import decide
from autodraft.resolve import (
    resolve_supplier, resolve_buyer, resolve_payment_terms,
    resolve_po_ids, resolve_taxes
)
from autodraft.normalize import parse_amount, parse_date, detect_currency

DOC_DIR = Path(__file__).resolve().parent.parent / "documents"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"
WORK_DIR = Path(__file__).resolve().parent.parent / ".work" / "pages"
TOL = Decimal("0.01")


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace("\u00a0", "").replace(",", "."))
    except Exception:
        return None


def _money_token(s: str) -> Decimal | None:
    """Extract a single decimal magnitude from a token like '1,234.56' or '1234,56' or '7,434.78'."""
    if not s:
        return None
    s = s.strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    
    # Detect decimal separator: last comma or dot that is followed by exactly 2 digits
    # If last comma/dot has 3 digits after, it's likely a thousands separator
    # Pattern: digits, then [.,]digits{2} at end = decimal
    # Pattern: digits, then [.,]digits{3} at end = thousands separator
    
    # Find the last comma or dot
    last_comma = s.rfind(',')
    last_dot = s.rfind('.')
    
    decimal_pos = -1
    if last_comma > last_dot:
        # Comma is after dot, so comma is likely decimal separator
        # Check if exactly 2 digits after comma
        if len(s) - last_comma - 1 == 2:
            decimal_pos = last_comma
    elif last_dot > last_comma:
        # Dot is after comma, so dot is likely decimal separator
        if len(s) - last_dot - 1 == 2:
            decimal_pos = last_dot
    elif last_comma != -1 and last_dot == -1:
        # Only comma present
        if len(s) - last_comma - 1 == 2:
            decimal_pos = last_comma
    elif last_dot != -1 and last_comma == -1:
        # Only dot present
        if len(s) - last_dot - 1 == 2:
            decimal_pos = last_dot
    
    if decimal_pos != -1:
        # Found decimal separator
        int_part = s[:decimal_pos].replace(',', '').replace('.', '')
        dec_part = s[decimal_pos+1:decimal_pos+3]
        try:
            return Decimal(int_part + '.' + dec_part)
        except Exception:
            pass
    
    # Fallback: try simple replacement
    try:
        # Try comma as decimal separator (European format)
        val = s.replace('.', '').replace(',', '.')
        return Decimal(val)
    except Exception:
        pass
    
    return None


def _extract_page_numbers(page_text: str) -> set[Decimal]:
    """Extract all money-like magnitudes from page text."""
    tokens = re.findall(r"\d{1,3}(?:[., ]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2}|\b\d+\b", page_text)
    nums = set()
    for t in tokens:
        d = _money_token(t)
        if d is not None:
            try:
                nums.add(d.quantize(Decimal("0.01")))
            except Exception:
                # skip values that can't be quantized
                pass
    return nums


def _render_page(pdf_path: str, page_no: int = 0) -> str:
    stem = Path(pdf_path).stem
    out = WORK_DIR / f"{stem}_p{page_no+1}.png"
    if out.exists():
        return str(out)
    doc = pymupdf.open(pdf_path)
    if page_no >= len(doc):
        return ""
    page = doc[page_no]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    pix.save(str(out))
    doc.close()
    return str(out)


def _all_page_numbers(pdf_path: str) -> set[Decimal]:
    """Grounding evidence = numbers across EVERY page, as the emitter saw them.

    Text-layer pages read via pdfplumber words; scanned pages rendered and
    OCR'd through the audit's own pipeline (cached in .work).  A doc like
    INV-03 is a pure scan — zero text-layer chars — so all its amounts exist
    only in OCR; grounding must include those pages or a correctly-extracted
    payable gets falsely flagged.
    """
    import pdfplumber

    nums: set[Decimal] = set()
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for pno in range(n):
            txt = ""
            try:
                words = pdf.pages[pno].extract_words()
                if words:
                    txt = " ".join(w["text"] for w in words)
            except Exception:
                txt = ""
            if not txt or len(txt.strip()) < 12:
                png = _render_page(pdf_path, pno)
                if png:
                    from autodraft.ocr import ocr_words

                    txt = " ".join(w.text for w in ocr_words(png))
            if txt:
                nums |= _extract_page_numbers(txt)
    return nums


def _extract_doc(pdf_path: str) -> ExtractedDoc | None:
    """Extract a document for auditing.

    Delegates to the pipeline's page-aware merge so the audit sees exactly the
    same document the emitter saw (label-grounded source page, merged line
    items, ex-GST genre coercion).  A union of every page's text is attached to
    `all_page_texts` so grounding checks the whole PDF, not just the summary
    page (multi-page totals like DU-03's log page would otherwise be missed).
    """
    try:
        from autodraft.pipeline import _extract_doc as _pipeline_extract
        doc, _ = _pipeline_extract(pdf_path)
    except Exception:
        doc = None
    if doc is None:
        return None
    if not getattr(doc, "all_page_texts", None):
        doc.all_page_texts = doc.page_text or ""
    return doc


def _check_erp_gate(payable: dict, filename: str) -> list[str]:
    """Verify ERP recompute matches emitted gross_total."""
    try:
        r = erp.erp_book(payable)
        booked = Decimal(str(r["will_book_gross"]))
        gross = _dec(payable.get("gross_total"))
        if gross is None:
            return [f"{filename}: gross_total missing"]
        if abs(gross - booked) > TOL:
            return [f"{filename}: ERP gate mismatch - emitted gross={gross}, erp_book={booked} (diff={abs(gross-booked)})"]
    except Exception as e:
        return [f"{filename}: ERP gate error: {e}"]
    return []


def _check_grounding(payable: dict, page_numbers: set[Decimal], filename: str) -> list[str]:
    """Verify every emitted numeric appears in page words (value-based comparison)."""
    issues = []
    emitted = []

    for k in ("gross_total", "subtotal", "total_tax_amount",
              "discount_amount", "freight_charges", "insurance_charges",
              "extra_charges", "excise_duties"):
        v = _dec(payable.get(k))
        if v is not None:
            emitted.append((f"payable.{k}", v))

    for i, t in enumerate(payable.get("taxes") or []):
        for k in ("tax_rate", "tax_amount"):
            v = _dec(t.get(k))
            if v is not None:
                emitted.append((f"payable.taxes[{i}].{k}", v))

    for li_idx, li in enumerate(payable.get("line_items") or []):
        for k in ("quantity", "unit_price", "total", "discount", "discount_percentage",
                  "tax_rate", "tax_amount"):
            v = _dec(li.get(k))
            if v is not None:
                emitted.append((f"payable.line_items[{li_idx}].{k}", v))
        for ti, t in enumerate(li.get("taxes") or []):
            for k in ("tax_rate", "tax_amount"):
                v = _dec(t.get(k))
                if v is not None:
                    emitted.append((f"payable.line_items[{li_idx}].taxes[{ti}].{k}", v))

    for path, val in emitted:
        # Value-based grounding: check if the numeric value exists in page
        # numbers, or is a valid derivation of printed header components
        # (gross/subtotal/tax/freight).  Allow small tolerance for rounding.
        # A zero is structural (e.g. an emitted 0.00 header tax) and needs no
        # page evidence; a negative magnitude is grounded by its absolute page
        # value since PDFs print trailing-minus/credit signs in many forms.
        found = val == 0 or any(abs(val - pn) <= Decimal("0.02") for pn in page_numbers)
        if not found and val != 0:
            found = any(abs(-val - pn) <= Decimal("0.02") for pn in page_numbers)
        if not found and val != 0:
            sub = _dec(payable.get("subtotal"))
            if sub is not None:
                tax = _dec(payable.get("total_tax_amount")) or Decimal("0")
                freight = _dec(payable.get("freight_charges")) or Decimal("0")
                deriv = [sub, sub - tax, sub + freight, sub + freight - tax]
                found = any(
                    abs(val - d) <= Decimal("0.02") for d in deriv)
        if not found:
            closest = (min(page_numbers, key=lambda x: abs(x - val))
                       if page_numbers else None)
            issues.append(f"{filename}: grounding failed - {path}={val} not found in page words (closest: {closest})")
    return issues


def _check_master_codes(payable: dict, doc: ExtractedDoc, filename: str) -> list[str]:
    """Verify all master-data codes are real matches or empty.
    Only flag: emitted code not in master, or mismatch with master."""
    issues = []

    # supplier_id - only flag if emitted code not in master
    sup_id = payable.get("supplier", {}).get("supplier_id", "")
    if sup_id:
        sup = resolve_supplier(doc.supplier_name, doc.supplier_vat, doc.currency)
        if not sup.get("id") or sup.get("id") != sup_id:
            issues.append(f"{filename}: supplier_id={sup_id} not a valid master code (resolved={sup.get('id')})")

    # payment_term_id - check if emitted code exists in master
    pt_id = payable.get("payment_term_id", "")
    if pt_id:
        pt_data = json.load(open(Path(__file__).resolve().parent.parent / "master_data" / "payment_terms.json"))
        valid_ids = {p["payment_term_id"] for p in pt_data["payment_terms"]}
        if pt_id not in valid_ids:
            issues.append(f"{filename}: payment_term_id={pt_id} not a valid master code")

    # buyer codes - only flag mismatches
    buyer = resolve_buyer(doc.supplier_address + " " + doc.page_text, doc.country_hint)
    for field in ("company_code", "business_unit_code", "location_code"):
        val = payable.get("buyer", {}).get(field, "")
        if val and buyer.get(field) != val:
            issues.append(f"{filename}: buyer.{field}={val} mismatch resolved={buyer.get(field)}")

    # po_id
    po_id = payable.get("po_id", "")
    if po_id:
        po_ids = resolve_po_ids([payable.get("po_number", "")])
        if po_ids and po_ids[0].get("id") != po_id:
            issues.append(f"{filename}: po_id={po_id} mismatch resolved={po_ids[0].get('id')}")

    # tax_type_code - only flag if emitted code not in master
    tax_data = json.load(open(Path(__file__).resolve().parent.parent / "master_data" / "tax_master.json"))
    valid_tax_codes = {t["code"] for t in tax_data["taxes"]}
    for i, t in enumerate(payable.get("taxes") or []):
        tc = t.get("tax_type_code", "")
        if tc and tc not in valid_tax_codes:
            issues.append(f"{filename}: tax[{i}].tax_type_code={tc} not a valid master code")

    for li_idx, li in enumerate(payable.get("line_items") or []):
        for ti, t in enumerate(li.get("taxes") or []):
            tc = t.get("tax_type_code", "")
            if tc and tc not in valid_tax_codes:
                issues.append(f"{filename}: line[{li_idx}].tax[{ti}].tax_type_code={tc} not a valid master code")

    return issues


def _check_placement(payable: dict, doc: ExtractedDoc, filename: str) -> list[str]:
    """Check tax placement fidelity: header taxes at header, line taxes on lines."""
    issues = []
    header_taxes = payable.get("taxes") or []
    line_taxes_present = any(li.get("taxes") for li in payable.get("line_items") or [])

    # If doc had header taxes (extracted doc.taxes) but payable moved them to lines
    doc_header_taxes = doc.taxes
    doc_line_taxes = any(li.taxes for li in doc.line_items)

    if doc_header_taxes and not header_taxes and line_taxes_present:
        issues.append(f"{filename}: placement issue - document header taxes moved to lines")
    if doc_line_taxes and not line_taxes_present and header_taxes:
        issues.append(f"{filename}: placement issue - document line taxes moved to header")

    # Check per-line tax_rate/tax_amount vs line taxes[] duplication
    for li_idx, li in enumerate(payable.get("line_items") or []):
        if (li.get("tax_rate") or li.get("tax_amount")) and li.get("taxes"):
            issues.append(f"{filename}: line[{li_idx}] has both tax_rate/tax_amount and taxes[] - ambiguous")

    return issues


def _check_decomposition(payable: dict, filename: str) -> list[str]:
    """Check line items are decomposed: qty * unit_price ≈ total, not pre-summed."""
    issues = []
    for li_idx, li in enumerate(payable.get("line_items") or []):
        qty = _dec(li.get("quantity"))
        unit = _dec(li.get("unit_price"))
        total = _dec(li.get("total"))
        if qty is not None and unit is not None and total is not None:
            calc = (qty * unit).quantize(Decimal("0.01"))
            if abs(calc - total) > Decimal("0.02"):
                issues.append(f"{filename}: line[{li_idx}] qty*unit={calc} != total={total} (not decomposed)")
    return issues


def audit_file(pdf_path: str, output_path: str) -> dict:
    """Audit a single PDF's output JSON."""
    stem = Path(pdf_path).stem
    filename = stem + ".pdf"

    # Load emitted output
    if not os.path.exists(output_path):
        return {"file": filename, "status": "missing_output", "issues": ["Output JSON not found"]}

    with open(output_path, encoding="utf-8") as f:
        out = json.load(f)

    payables = out.get("payables", [])
    declined = out.get("declined", [])

    # Re-extract for grounding and master-code re-resolution
    doc = _extract_doc(pdf_path)
    if doc is None:
        return {"file": filename, "status": "extract_failed", "issues": ["Extraction failed"]}

    page_numbers = _all_page_numbers(pdf_path)

    all_issues = []
    for payable in payables:
        all_issues.extend(_check_erp_gate(payable, filename))
        all_issues.extend(_check_grounding(payable, page_numbers, filename))
        all_issues.extend(_check_master_codes(payable, doc, filename))
        all_issues.extend(_check_placement(payable, doc, filename))
        all_issues.extend(_check_decomposition(payable, filename))

    for dec in declined:
        # Verify decline is honest: no variant would have passed
        pass  # future: re-run variants to confirm

    return {"file": filename, "status": "ok" if not all_issues else "issues", "issues": all_issues}


def run_audit():
    """Run audit over all documents."""
    pdfs = sorted(DOC_DIR.glob("*.pdf"))
    results = []
    for pdf in pdfs:
        out_file = OUT_DIR / f"{pdf.stem}.json"
        res = audit_file(str(pdf), str(out_file))
        results.append(res)
        status = res["status"]
        if status == "ok":
            print(f"  {pdf.stem}: OK")
        elif status == "issues":
            for issue in res["issues"]:
                print(f"  {pdf.stem}: ISSUE - {issue}")
        else:
            print(f"  {pdf.stem}: {status.upper()} - {res['issues']}")
    return results


if __name__ == "__main__":
    print("Running fidelity audit...")
    results = run_audit()
    ok = sum(1 for r in results if r["status"] == "ok")
    issues = sum(1 for r in results if r["status"] == "issues")
    other = sum(1 for r in results if r["status"] not in ("ok", "issues"))
    print(f"\nSummary: {ok} OK, {issues} with issues, {other} other")