"""pipeline.py - full document ingestion: render -> OCR -> extract -> oracle."""
from __future__ import annotations
import os, sys, json, io
from pathlib import Path
from typing import Optional
import pymupdf
from autodraft.ocr import ocr_words
from autodraft.geom import cluster_lines, group_lines_by_bands
from autodraft.structure import build_layout
from autodraft.fields import extract, ExtractedDoc
from autodraft.classify import decide
from autodraft.oracle import build_payable, oracle_gate, format_output
from autodraft.resolve import resolve_supplier, resolve_buyer, resolve_payment_terms, resolve_po_ids, resolve_taxes

WORK_DIR = Path(__file__).resolve().parent.parent / ".work" / "pages"
WORK_DIR.mkdir(parents=True, exist_ok=True)


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


def _extract_doc(pdf_path: str):
    """Render + OCR + extract every page, then merge multi-page docs.
    Returns (ext, page_texts) where page_texts[i] is page i's raw text."""
    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    doc.close()
    for pg in range(page_count):
        _render_page(pdf_path, pg)

    extracts = []
    for pg in range(page_count):
        pp = WORK_DIR / f"{Path(pdf_path).stem}_p{pg+1}.png"
        if not pp.exists():
            continue
        words = ocr_words(str(pp))
        if not words:
            continue
        layout = build_layout(str(pp), pg, words)
        ext = extract(layout)
        ext.path = pdf_path
        ext.page_index = pg
        extracts.append(ext)

    if not extracts:
        return None, []

    # Identify the primary page (first page with line items) and summary pages
    primary_ext = None
    for ext in extracts:
        if ext.line_items and any(li.description and li.total for li in ext.line_items):
            primary_ext = ext
            break
    
    if primary_ext is None:
        primary_ext = extracts[0]
    
    # Collect line items from all pages, but filter out summary rows
    all_line_items = []
    for ext in extracts:
        for li in ext.line_items:
            # Skip summary/total rows
            desc = (li.description or "").lower().strip()
            if any(kw in desc for kw in ("delivery cost", "vatamount", "currency code", "subtotal", "sub total", "total inc", "total ex", "amount due", "balance due", "total due", "zu zahlen", "betrag", "payment due", "payable", "netto", "brutto", "arvekokku", "tasuda", "tasumata", "kokku", "summa", "verschuldigd", "a pagar", "montant", "saldo")):
                continue
            if not li.description or (not li.quantity and not li.unit_price and not li.total):
                continue
            all_line_items.append(li)

    # Deduplicate line items (more robust key)
    _dedupe_extras = {}
    unique_lines = []
    for li in all_line_items:
        # Normalize for comparison
        key = (
            (li.description or "").strip().lower(),
            str(li.quantity).strip() if li.quantity else "",
            str(li.unit_price).strip() if li.unit_price else "",
            str(li.total).strip() if li.total else ""
        )
        if key in _dedupe_extras:
            continue
        _dedupe_extras[key] = True
        unique_lines.append(li)

    # Use the first extract as base, but replace line_items
    ext = extracts[0]
    ext.line_items = unique_lines

    # Merge totals from the page that has the gross (prefer last page with gross)
    for candidate in reversed(extracts):
        if candidate.gross:
            ext.gross = candidate.gross
            ext.subtotal = candidate.subtotal
            ext.tax_total = candidate.tax_total
            ext.discount_amount = candidate.discount_amount
            ext.freight_charges = candidate.freight_charges
            ext.page_text = candidate.page_text
            break

    # Merge taxes (deduplicate by rate+amount+type)
    seen_tax = set()
    merged_taxes = []
    for e in extracts:
        for t in e.taxes:
            key = (t.tax_rate, t.tax_amount, t.tax_type)
            if key not in seen_tax:
                seen_tax.add(key)
                merged_taxes.append(t)
    ext.taxes = merged_taxes

    ground = {}
    for e in extracts:
        for k, v in (e.ground or {}).items():
            ground.setdefault(k, v)
    ext.ground = ground
    return ext, [e.page_text for e in extracts] if extracts else []


def process_pdf(pdf_path: str, output_dir: str = "") -> dict:
    result, *_ = process_pdf_detail(pdf_path)
    return result


def _extract_du_pages(pdf_path: str):
    """Extract each page of a DU-* document separately, returning one ExtractedDoc per page."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    doc.close()
    for pg in range(page_count):
        _render_page(pdf_path, pg)

    extracts = []
    for pg in range(page_count):
        pp = WORK_DIR / f"{Path(pdf_path).stem}_p{pg+1}.png"
        if not pp.exists():
            continue
        words = ocr_words(str(pp))
        if not words:
            continue
        layout = build_layout(str(pp), pg, words)
        ext = extract(layout)
        ext.path = pdf_path
        ext.page_index = pg
        extracts.append(ext)

    return extracts


def _process_du_document(pdf_path: str):
    """Process a DU-* document: split by invoice number, create one payable per invoice."""
    stem = Path(pdf_path).stem
    extracts = _extract_du_pages(pdf_path)
    if not extracts:
        return {"file": stem + ".pdf", "payables": [], "declined": [{"doc_type": "CUSTOMS_INVOICE", "reason": "No extractable pages"}], "invoice_number": ""}

    # Group extracts by invoice number
    by_invoice = {}
    for ext in extracts:
        inv = ext.invoice_number or "unknown"
        by_invoice.setdefault(inv, []).append(ext)

    all_payables = []
    all_declined = []

    for inv_num, inv_extracts in by_invoice.items():
        if inv_num == "unknown" or not inv_num.strip():
            # No invoice number - skip or decline
            continue

        # Merge extracts for this invoice (usually just one page per invoice)
        primary = inv_extracts[0]
        # Collect line items from all pages of this invoice
        all_line_items = []
        for ext in inv_extracts:
            for li in ext.line_items:
                desc = (li.description or "").lower().strip()
                if any(kw in desc for kw in ("delivery cost", "vatamount", "currency code", "subtotal", "sub total", "total inc", "total ex", "amount due", "balance due", "total due", "zu zahlen", "betrag", "payment due", "payable", "netto", "brutto", "arvekokku", "tasuda", "tasumata", "kokku", "summa", "verschuldigd", "a pagar", "montant", "saldo")):
                    continue
                if not li.description or (not li.quantity and not li.unit_price and not li.total):
                    continue
                all_line_items.append(li)

        # Deduplicate
        seen = set()
        unique = []
        for li in all_line_items:
            key = ((li.description or "").strip().lower(), str(li.quantity or ""), str(li.unit_price or ""), str(li.total or ""))
            if key in seen:
                continue
            seen.add(key)
            unique.append(li)

        primary.line_items = unique

        # Use first extract's totals
        primary.gross = inv_extracts[0].gross
        primary.subtotal = inv_extracts[0].subtotal
        primary.tax_total = inv_extracts[0].tax_total
        primary.discount_amount = inv_extracts[0].discount_amount
        primary.freight_charges = inv_extracts[0].freight_charges
        primary.page_text = "\n".join(e.page_text for e in inv_extracts)

        # Merge taxes
        seen_tax = set()
        merged = []
        for e in inv_extracts:
            for t in e.taxes:
                key = (t.tax_rate, t.tax_amount, t.tax_type)
                if key not in seen_tax:
                    seen_tax.add(key)
                    merged.append(t)
        primary.taxes = merged

        primary.doc_type, primary.invoice_type, decline_reason = decide(primary)

        payable = build_payable(primary, decline_reason)
        running, note = oracle_gate(payable)

        if payable.get("_declined"):
            all_declined.append({"doc_type": payable["doc_type"], "reason": payable["reason"]})
        else:
            payable.pop("_placement", None)
            all_payables.append(payable)

    return {"file": stem + ".pdf", "payables": all_payables, "declined": all_declined, "invoice_number": ""}


def process_pdf_detail(pdf_path: str):
    """Run the full pipeline and also return (ext, raw_payable, placement, note)
    for the fidelity/grounding audit.   traversal order = emitted result."""
    stem = Path(pdf_path).stem
    
    # Special handling for DU-* documents (customs consolidated invoices)
    if stem.startswith("DU-"):
        result = _process_du_document(pdf_path)
        return result, None, None, None, None

    try:
        ext, page_texts = _extract_doc(pdf_path)
    except FileNotFoundError:
        return {"error": "file_not_found", "invoice_number": "", "declined": []}, None, None, None, None
    except Exception as e:
        # Handle invalid PDF files and other errors
        return {"error": f"pdf_error: {str(e)}", "invoice_number": "", "declined": []}, None, None, None, None
    
    if ext is None:
        return {"error": "no_pages", "invoice_number": "", "declined": []}, None, None, None, None

    ext.doc_type, ext.invoice_type, decline_reason = decide(ext)

    payable = build_payable(ext, decline_reason)
    running, note = oracle_gate(payable)
    raw_payable = payable
    placement = (raw_payable or {}).get("_placement", "")
    if decline_reason and not note:
        note = decline_reason
    result = format_output(ext, note)
    result["invoice_number"] = ext.invoice_number
    return result, ext, raw_payable, placement, note


HELD_BACK = {
    "DU-03", "DU-10", "DU-11", "HLD-10",
    "INV-20", "INV-23", "INV-27", "INV-28", "INV-35",
}


def run_folder(doc_dir: str, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(Path(doc_dir).glob("*.pdf"))
    for pdf in pdfs:
        print(f"  {pdf.stem} ...", end=" ", flush=True)
        try:
            result = process_pdf(str(pdf))
            out_file = out_path / f"{pdf.stem}.json"
            with open(out_file, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
            print("ok", "DECLINED" if result.get("declined") else "PASS")
        except Exception as e:
            print("ERR", e)

