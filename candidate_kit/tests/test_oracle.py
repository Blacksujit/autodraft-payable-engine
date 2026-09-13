"""
Tests for autodraft.oracle module
"""

import pytest
from decimal import Decimal
import erp
from autodraft.oracle import (
    build_payable, oracle_gate, _variant_keep, _variant_header_amount,
    _variant_header_rate, _variant_line_rate, _matches, _booked,
    _fill_totals, _tax_dict, _li_dict
)
from autodraft.fields import ExtractedDoc, TaxItem, LineItemExt


class TestTaxDict:
    def test_from_taxitem(self):
        tax = TaxItem(tax_type="VAT", tax_name="VAT 20%", tax_rate="20", tax_amount="20.00")
        result = _tax_dict(tax)
        assert result["tax_type"] == "VAT"
        assert result["tax_name"] == "VAT 20%"
        assert result["tax_rate"] == "20.00"
        assert result["tax_amount"] == "20.00"

    def test_from_dict(self):
        tax = {"tax_type": "VAT", "tax_name": "VAT", "tax_rate": "20", "tax_amount": "20"}
        result = _tax_dict(tax)
        assert result["tax_rate"] == "20.00"


class TestLiDict:
    def test_with_line_taxes(self):
        li = LineItemExt(description="Item", quantity="1", unit_price="100", total="100")
        li.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = _li_dict(li, li.taxes)
        
        # The result includes tax_type_code which may be empty
        assert len(result["taxes"]) == 1
        tax = result["taxes"][0]
        assert tax["tax_type"] == "VAT"
        assert tax["tax_name"] == "VAT"
        assert tax["tax_rate"] == "20.00"  # Now formatted to 2 decimal places
        assert tax["tax_amount"] == "20.00"

    def test_without_line_taxes(self):
        li = LineItemExt(description="Item", quantity="1", unit_price="100", total="100", tax_rate="20", tax_amount="20")
        
        result = _li_dict(li, [])
        assert result["tax_rate"] == "20"
        assert result["tax_amount"] == "20"
        assert result["taxes"] == []


class TestVariantKeep:
    def test_keeps_original(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.invoice_number = "12345"
        doc.gross = "120.00"
        doc.subtotal = "100.00"
        doc.tax_total = "20.00"
        doc.line_items = [
            LineItemExt(description="Item", quantity="1", unit_price="100", total="100")
        ]
        doc.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = _variant_keep(doc)
        
        assert result["gross_total"] == "120.00"
        assert result["subtotal"] == "100.00"
        assert result["total_tax_amount"] == "20.00"
        assert len(result["line_items"]) == 1


class TestVariantHeaderAmount:
    def test_moves_taxes_to_header(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.gross = "120.00"
        doc.line_items = [
            LineItemExt(description="Item", quantity="1", unit_price="100", total="100")
        ]
        doc.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = _variant_header_amount(doc)
        
        assert len(result["taxes"]) == 1
        assert len(result["line_items"][0]["taxes"]) == 0


class TestVariantHeaderRate:
    def test_removes_tax_amount(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.gross = "120.00"
        doc.line_items = [
            LineItemExt(description="Item", quantity="1", unit_price="100", total="100")
        ]
        doc.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = _variant_header_rate(doc)
        
        assert result["taxes"][0]["tax_rate"] == "20.00"
        assert result["taxes"][0]["tax_amount"] == ""


class TestVariantLineRate:
    def test_applies_to_all_lines(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.gross = "120.00"
        doc.line_items = [
            LineItemExt(description="Item 1", quantity="1", unit_price="50", total="50"),
            LineItemExt(description="Item 2", quantity="1", unit_price="50", total="50"),
        ]
        doc.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = _variant_line_rate(doc)
        
        assert len(result["line_items"]) == 2
        assert len(result["line_items"][0]["taxes"]) == 1
        assert len(result["line_items"][1]["taxes"]) == 1


class TestMatches:
    def test_exact_match(self):
        payable = {
            "gross_total": "120.00",
            "line_items": [{"quantity": "1", "unit_price": "100", "total": "100"}],
            "taxes": [{"tax_rate": "20", "tax_amount": "20"}],
        }
        target = Decimal("120.00")
        assert _matches(payable, target) is True

    def test_within_tolerance(self):
        payable = {
            "gross_total": "120.005",
            "line_items": [{"quantity": "1", "unit_price": "100", "total": "100"}],
            "taxes": [{"tax_rate": "20", "tax_amount": "20"}],
        }
        target = Decimal("120.00")
        assert _matches(payable, target) is True  # Within 0.01

    def test_outside_tolerance(self):
        # Payable computes to 120.20 (outside 0.01 tolerance of 120.00)
        payable = {
            "gross_total": "120.20",
            "line_items": [{"quantity": "1", "unit_price": "100.20", "total": "100.20"}],
            "taxes": [],
        }
        target = Decimal("120.00")
        assert _matches(payable, target) is False


class TestBooked:
    def test_valid_payable(self):
        payable = {
            "line_items": [{"quantity": "1", "unit_price": "100", "total": "100"}],
            "taxes": [],
        }
        result = _booked(payable)
        assert result == Decimal("100.00")

    def test_with_tax(self):
        payable = {
            "line_items": [{"quantity": "1", "unit_price": "100", "total": "100"}],
            "taxes": [{"tax_rate": "20", "tax_amount": "20"}],
        }
        result = _booked(payable)
        assert result == Decimal("120.00")


class TestFillTotals:
    def test_calculates_correctly(self):
        payable = {
            "line_items": [{"total": "100", "taxes": []}],
            "taxes": [{"tax_rate": "20", "tax_amount": "20"}],
            "discount_amount": "",
            "freight_charges": "",
            "insurance_charges": "",
            "extra_charges": "",
            "excise_duties": "",
        }
        
        _fill_totals(payable)
        
        assert payable["subtotal"] == "100.00"
        assert payable["total_tax_amount"] == "20.00"
        assert payable["gross_total"] == "120.00"


class TestBuildPayable:
    def test_creates_payable(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.invoice_number = "12345"
        doc.invoice_date = "2026-01-15"
        doc.due_date = "2026-02-15"
        doc.currency = "EUR"
        doc.supplier_name = "Test Supplier"
        doc.supplier_vat = "DE123456789"
        doc.gross = "120.00"
        doc.subtotal = "100.00"
        doc.tax_total = "20.00"
        doc.line_items = [
            LineItemExt(description="Item", quantity="1", unit_price="100", total="100")
        ]
        doc.taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20")]
        
        result = build_payable(doc, "")
        
        assert result["invoice_number"] == "12345"
        assert result["currency"] == "EUR"
        assert result["gross_total"] == "120.00"
        assert "_placement" in result

    def test_credit_memo(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.invoice_type = "CREDIT_MEMO"
        doc.gross = "-100.00"
        doc.line_items = [
            LineItemExt(description="Return", quantity="1", unit_price="100", total="100")
        ]
        
        result = build_payable(doc, "")
        
        # Credit memos use positive magnitudes
        assert result["gross_total"] == "100.00"
        assert result["invoice_type"] == "CREDIT_MEMO"


class TestOracleGate:
    def test_passes_valid(self):
        payable = {
            "invoice_number": "12345",
            "gross_total": "120.00",
            "line_items": [{"quantity": "1", "unit_price": "100", "total": "100"}],
            "taxes": [{"tax_rate": "20", "tax_amount": "20"}],
        }
        
        result, reason = oracle_gate(payable)
        assert reason == ""
        assert result == payable

    def test_fails_invalid(self):
        payable = {"_declined": True, "reason": "test"}
        
        result, reason = oracle_gate(payable)
        assert reason == "test"
        assert result == payable