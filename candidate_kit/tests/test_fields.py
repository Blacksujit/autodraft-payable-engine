"""
Tests for autodraft.fields module
"""

import pytest
from decimal import Decimal
from autodraft.fields import (
    ExtractedDoc, LineItemExt, TaxItem, extract, 
    _extract_line_items, _extract_taxes, _extract_table_taxes,
    _is_summary_row, _is_tax_label, _is_pure_tax_label,
    _item_type, _split_qty_uom, _money_token,
    _label_amount, _label_ground, _extract_totals,
    _INV_NO_RE, _DATE_LABEL_RE, _DUE_EXPL_RE,
    _BAL_LABELS, _GROSS_LABELS, _SUB_LABELS, _TAX_TOTAL_LABELS,
    _DISC_LABELS, _FREIGHT_LABELS, _SUMMARY_LABELS, _TAX_LABELS
)
from autodraft.structure import build_layout, Table
from autodraft.geom import Word, Line, Box


class TestExtractedDoc:
    def test_creation(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        assert doc.path == "test.pdf"
        assert doc.page_index == 0
        assert doc.page_text == "Test"

    def test_default_values(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        assert doc.invoice_number == ""
        assert doc.invoice_date == ""
        assert doc.currency == ""
        assert doc.line_items == []


class TestLineItemExt:
    def test_creation(self):
        item = LineItemExt(description="Test", quantity="1", unit_price="100", total="100")
        assert item.description == "Test"
        assert item.quantity == "1"

    def test_empty(self):
        item = LineItemExt()
        assert item.description == ""
        assert item.quantity == ""


class TestTaxItem:
    def test_creation(self):
        tax = TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20.00")
        assert tax.tax_name == "VAT"
        assert tax.tax_rate == "20"


class TestRegexes:
    def test_inv_no_re(self):
        text = "Invoice Number: 12345"
        for pattern in _INV_NO_RE:
            match = pattern.search(text)
            if match:
                assert match.group(1) == "12345"
                break

    def test_date_label_re(self):
        text = "Invoice Date: 15.01.2026"
        match = _DATE_LABEL_RE.search(text)
        assert match is not None
        assert match.group(1) == "15.01.2026"

    def test_due_expl_re(self):
        text = "DueDate:31May2025"
        match = _DUE_EXPL_RE.search(text)
        assert match is not None
        assert match.group(1) == "31May2025"

    def test_bal_labels(self):
        labels = ["Total Due", "Amount Due", "Balance Due", "Zu zahlen", "Arvekokku"]
        for label in labels:
            match = any(pattern.search(label) for pattern in _BAL_LABELS)
            assert match is True, f"Failed for label: {label}"

    def test_gross_labels(self):
        labels = ["Total", "Grand Total", "Invoice Total", "Arvekokku"]
        for label in labels:
            match = any(pattern.search(label) for pattern in _GROSS_LABELS)
            assert match is True, f"Failed for label: {label}"

    def test_tax_labels(self):
        labels = ["VAT", "GST", "MwSt", "USt", "IVA", "BTW", "Käibemaks"]
        for label in labels:
            match = any(pattern.search(label) for pattern in _TAX_LABELS)
            assert match is True, f"Failed for label: {label}"


class TestItemType:
    def test_service(self):
        assert _item_type("Projektmanagement") == "SERVICE"
        assert _item_type("Consulting services") == "SERVICE"
        assert _item_type("Cleaning service") == "SERVICE"

    def test_goods(self):
        assert _item_type("Hardware") == "GOODS"
        assert _item_type("CDJ-3000") == "GOODS"
        assert _item_type("Speaker") == "GOODS"

    def test_default(self):
        assert _item_type("Unknown item") == "GOODS"


class TestSplitQtyUom:
    def test_split_qty_uom(self):
        qty, uom = _split_qty_uom("10 Hr")
        assert qty == Decimal("10")
        assert uom == "Hr"

    def test_split_no_uom(self):
        qty, uom = _split_qty_uom("10")
        assert qty == Decimal("10")
        assert uom == ""  # No UOM provided

    def test_split_invalid(self):
        qty, uom = _split_qty_uom("abc")
        assert qty is None
        assert uom == "abc"


class TestMoneyToken:
    def test_european_format(self):
        result = _money_token("1.234,56")
        assert result == Decimal("1234.56")

    def test_us_format(self):
        result = _money_token("1,234.56")
        assert result == Decimal("1234.56")

    def test_simple(self):
        result = _money_token("100.50")
        assert result == Decimal("100.50")

    def test_integer(self):
        result = _money_token("100")
        assert result == Decimal("100")


class TestLabelAmount:
    def test_basic(self):
        text = "Total Due: 100.00"
        labels = _BAL_LABELS
        result = _label_amount(text, labels)
        assert result == "100.00"

    def test_no_match(self):
        text = "No total here"
        labels = [pytest.importorskip("re").compile(r"Total:")]
        result = _label_amount(text, labels)
        assert result == ""


class TestExtractTotals:
    def test_extract_basic(self):
        header = ""
        footer = "Subtotal 100.00 VAT 20.00 Total 120.00"
        taxes = []
        g = {}
        
        from autodraft.fields import _extract_totals
        gross, sub, tax_total, disc, freight = _extract_totals(
            header, footer, Decimal("100"), taxes, g
        )
        
        assert gross == "120.00"
        assert sub == "100.00"
        assert tax_total == "20.00"


class TestExtractLineItems:
    def test_extract_from_table(self):
        # Create a mock table
        columns = [
            type('Col', (), {'index': 0, 'x0': 0, 'x1': 100})(),
            type('Col', (), {'index': 1, 'x0': 100, 'x1': 200})(),
            type('Col', (), {'index': 2, 'x0': 200, 'x1': 300})(),
        ]
        
        table = Table(0, 100, columns=columns)
        table.rows = {
            0: {0: [(None, "Description")], 1: [(None, "Qty")], 2: [(None, "Total")]},
            1: {0: [(None, "Item 1")], 1: [(None, "10")], 2: [(None, "100")]},
            2: {0: [(None, "Item 2")], 1: [(None, "5")], 2: [(None, "50")]},
        }
        table.header_row = 0
        table.money_cols = [1, 2]
        table.DESCR = 0
        
        g = {}
        items = _extract_line_items(table, g)
        
        assert len(items) == 2
        assert items[0].description == "Item 1"
        assert items[0].quantity == "10"
        assert items[0].total == "100"


class TestIsSummaryRow:
    def test_summary_keywords(self):
        assert _is_summary_row("Total", "", "", "100") is True
        assert _is_summary_row("Subtotal", "", "", "50") is True
        assert _is_summary_row("VAT", "", "", "20") is True
        assert _is_summary_row("Summe", "", "", "100") is True

    def test_not_summary(self):
        assert _is_summary_row("Item 1", "10", "10", "100") is False
        assert _is_summary_row("Product A", "1", "100", "100") is False


class TestIsTaxLabel:
    def test_tax_labels(self):
        assert _is_tax_label("VAT 20%") is True
        assert _is_tax_label("GST") is True
        assert _is_tax_label("MwSt 19%") is True
        assert _is_tax_label("IVA 22%") is True

    def test_not_tax(self):
        assert _is_tax_label("Item 1") is False
        assert _is_tax_label("Total") is False


class TestExtractTableTaxes:
    def test_extract_tax_rows(self):
        columns = [
            type('Col', (), {'index': 0, 'x0': 0, 'x1': 100})(),
            type('Col', (), {'index': 1, 'x0': 100, 'x1': 200})(),
            type('Col', (), {'index': 2, 'x0': 200, 'x1': 300})(),
        ]
        
        table = Table(0, 100, columns=columns)
        table.rows = {
            0: {0: [(None, "Description")], 1: [(None, "Qty")], 2: [(None, "Total")]},
            1: {0: [(None, "VAT 20%")], 1: [(None, "")], 2: [(None, "20.00")]},
            2: {0: [(None, "Subtotal")], 1: [(None, "")], 2: [(None, "100.00")]},
        }
        table.header_row = 0
        table.money_cols = [1, 2]
        table.DESCR = 0
        
        g = {}
        taxes = _extract_table_taxes(table, g)
        
        assert len(taxes) >= 1
        assert taxes[0].tax_name == "VAT 20%"
        assert taxes[0].tax_amount == "20.00"


class TestExtractTaxes:
    def test_extract_from_text(self):
        header = ""
        footer = "VAT 20%: 20.00 Subtotal 100.00 Total 120.00"
        g = {}
        
        taxes, total = _extract_taxes(header, footer, g)
        
        assert len(taxes) >= 1
        assert taxes[0].tax_name == "VAT"
        assert taxes[0].tax_rate == "20"
        assert taxes[0].tax_amount == "20.00"