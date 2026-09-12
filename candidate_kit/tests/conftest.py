"""
Pytest configuration and shared fixtures for autodraft tests
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodraft.geom import Box, Word, Line, cluster_lines, group_lines_by_bands
from autodraft.normalize import parse_amount, parse_date, detect_currency, quantize_2
from autodraft.structure import build_layout, Table, Column
from autodraft.fields import (
    ExtractedDoc, LineItemExt, TaxItem, extract, _extract_line_items,
    _extract_taxes, _extract_table_taxes, _is_summary_row
)
from autodraft.classify import decide
from autodraft.resolve import (
    resolve_supplier, resolve_buyer, resolve_payment_terms,
    resolve_po_ids, resolve_taxes
)
from autodraft.oracle import build_payable, oracle_gate, _variant_keep
from autodraft.audit import audit_file, run_audit
from autodraft.pipeline import process_pdf, process_pdf_detail


@pytest.fixture
def sample_words():
    """Sample OCR words for testing"""
    return [
        Word(Box(100, 100, 200, 120), "Invoice", 0.9),
        Word(Box(100, 130, 200, 150), "12345", 0.9),
        Word(Box(100, 160, 200, 180), "Date:", 0.9),
        Word(Box(250, 160, 350, 180), "2026-01-15", 0.9),
    ]


@pytest.fixture
def sample_extracted_doc():
    """Sample extracted document for testing"""
    doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Invoice 12345 Date 2026-01-15")
    doc.invoice_number = "12345"
    doc.invoice_date = "2026-01-15"
    doc.currency = "EUR"
    doc.supplier_name = "Test Supplier"
    doc.gross = "100.00"
    doc.line_items = [
        LineItemExt(description="Test Item", quantity="1", unit_price="100.00", total="100.00")
    ]
    return doc


@pytest.fixture
def mock_pdf_path():
    """Path to a test PDF if available"""
    pdf_dir = PROJECT_ROOT / "documents"
    if pdf_dir.exists():
        pdfs = list(pdf_dir.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
    return None