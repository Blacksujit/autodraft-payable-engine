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

    ext = extracts[0]
    for subsequent in extracts[1:]:
        ext.line_items.extend(subsequent.line_items)

    _dedupe_extras = {}
    unique_lines = []
    for li in ext.line_items:
        key = (li.description, str(li.quantity), str(li.unit_price), str(li.total))
        if key in _dedupe_extras:
            continue
        _dedupe_extras[key] = True
        unique_lines.append(li)
    ext.line_items = unique_lines

    for candidate in reversed(extracts):
        if candidate.gross:
            ext.gross = candidate.gross
            ext.subtotal = candidate.subtotal
            ext.tax_total = candidate.tax_total
            ext.discount_amount = candidate.discount_amount
            ext.freight_charges = candidate.freight_charges
            ext.page_text = candidate.page_text
            break

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


def process_pdf_detail(pdf_path: str):
    """Run the full pipeline and also return (ext, raw_payable, placement, note)
    for the fidelity/grounding audit.   traversal order = emitted result."""
    stem = Path(pdf_path).stem
    ext, page_texts = _extract_doc(pdf_path)
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

