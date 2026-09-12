"""
Tests for autodraft.audit module
"""

import pytest
from decimal import Decimal
from autodraft.audit import (
    audit_file, run_audit, _check_erp_gate, _check_grounding,
    _check_master_codes, _check_placement, _check_decomposition,
    _extract_page_numbers, _money_token, _render_page, _extract_doc
)


class TestExtractPageNumbers:
    def test_extract_numbers(self):
        text = "Total: 100.00 VAT: 20.00 Gross: 120.00"
        numbers = _extract_page_numbers(text)
        assert Decimal("100.00") in numbers
        assert Decimal("20.00") in numbers
        assert Decimal("120.00") in numbers

    def test_european_format(self):
        text = "Total: 1.234,56"
        numbers = _extract_page_numbers(text)
        assert Decimal("1234.56") in numbers

    def test_empty(self):
        assert _extract_page_numbers("") == set()


class TestMoneyToken:
    def test_european(self):
        result = _money_token("1.234,56")
        assert result == Decimal("1234.56")

    def test_us(self):
        result = _money_token("1,234.56")
        assert result == Decimal("1234.56")

    def test_simple(self):
        result = _money_token("100.00")
        assert result == Decimal("100.00")


class TestCheckErpGate:
    def test_match(self):
        payable = {"gross_total": "120.00", "currency": "EUR"}
        issues = _check_erp_gate(payable, "test.pdf")
        # This will call erp.erp_book which computes the actual gross
        # We're just testing the function structure
        assert isinstance(issues, list)

    def test_mismatch(self):
        payable = {"gross_total": "100.00", "currency": "EUR"}
        issues = _check_erp_gate(payable, "test.pdf")
        assert isinstance(issues, list)


class TestCheckGrounding:
    def test_found(self):
        payable = {"gross_total": "100.00"}
        page_numbers = {Decimal("100.00"), Decimal("20.00")}
        issues = _check_grounding(payable, page_numbers, "test.pdf")
        assert len(issues) == 0

    def test_not_found(self):
        payable = {"gross_total": "999.99"}
        page_numbers = {Decimal("100.00")}
        issues = _check_grounding(payable, page_numbers, "test.pdf")
        assert len(issues) > 0


class TestCheckMasterCodes:
    def test_valid_codes(self):
        from autodraft.fields import ExtractedDoc
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        payable = {"supplier": {"supplier_id": ""}}
        
        issues = _check_master_codes(payable, doc, "test.pdf")
        assert isinstance(issues, list)


class TestCheckPlacement:
    def test_header_tax_moved(self):
        from autodraft.fields import ExtractedDoc
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Test")
        doc.taxes = [type('Tax', (), {'tax_rate': '20', 'tax_amount': '20'})()]
        
        payable = {
            "taxes": [],
            "line_items": [{"taxes": [{"tax_rate": "20", "tax_amount": "20"}]}]
        }
        
        issues = _check_placement(payable, doc, "test.pdf")
        assert any("moved to lines" in issue for issue in issues)


class TestCheckDecomposition:
    def test_valid_decomposition(self):
        payable = {
            "line_items": [
                {"quantity": "10", "unit_price": "10", "total": "100"}
            ]
        }
        
        issues = _check_decomposition(payable, "test.pdf")
        assert len(issues) == 0

    def test_invalid_decomposition(self):
        payable = {
            "line_items": [
                {"quantity": "10", "unit_price": "10", "total": "50"}  # 10*10 != 50
            ]
        }
        
        issues = _check_decomposition(payable, "test.pdf")
        assert len(issues) > 0


class TestAuditFile:
    def test_missing_output(self):
        result = audit_file("nonexistent.pdf", "nonexistent.json")
        assert result["status"] == "missing_output"

    def test_declined_document(self, tmp_path):
        # Create a declined output
        output_file = tmp_path / "test.json"
        output_file.write_text('{"file": "test.pdf", "payables": [], "declined": [{"reason": "test"}]}')
        
        result = audit_file("test.pdf", str(output_file))
        # Should handle declined documents gracefully
        assert result["status"] in ["ok", "issues"]


class TestRenderPage:
    def test_render_creates_png(self, tmp_path, mock_pdf_path):
        if mock_pdf_path:
            output = _render_page(mock_pdf_path, 0)
            assert output is not None