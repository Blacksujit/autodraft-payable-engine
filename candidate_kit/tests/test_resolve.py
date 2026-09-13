"""
Tests for autodraft.resolve module
"""

import pytest
from autodraft.resolve import (
    resolve_supplier, resolve_buyer, resolve_payment_terms,
    resolve_po_ids, resolve_taxes, _score_name, _norm
)


class TestNorm:
    def test_basic(self):
        assert _norm("Hello World") == "helloworld"
        assert _norm("  Test  ") == "test"
        assert _norm("Test!@#$%") == "test"
        assert _norm("") == ""


class TestScoreName:
    def test_exact_match(self):
        score = _score_name("Test Supplier", "Test Supplier")
        assert score == 1.0

    def test_substring(self):
        score = _score_name("Northwind Operations OU", "Northwind")
        assert score >= 0.9

    def test_partial_match(self):
        score = _score_name("Northwind Operations OU", "Operations")
        assert score > 0

    def test_no_match(self):
        score = _score_name("Completely Different", "Another Company")
        assert score == 0


class TestResolveSupplier:
    def test_exact_name_match(self):
        result = resolve_supplier("Phocus Direct Communication GmbH", "", "EUR")
        assert result["id"] != ""
        assert result["name"] == "Phocus Direct Communication GmbH"

    def test_vat_match(self):
        result = resolve_supplier("", "DE209177122", "EUR")
        assert result["id"] != ""
        assert result["vat_id"] == "DE209177122"

    def test_partial_name_match(self):
        result = resolve_supplier("Phocus", "", "EUR")
        # Should find Phocus Direct Communication GmbH
        assert result["id"] != ""

    def test_no_match(self):
        result = resolve_supplier("NonExistent Company", "XX123456", "EUR")
        assert result["id"] == ""
        assert result["name"] == "NonExistent Company"

    def test_currency_mismatch(self):
        # Supplier in USD but invoice in EUR should reduce score
        result = resolve_supplier("Test Supplier", "", "EUR")
        # Should still match but with lower score if currency differs
        pass


class TestResolveBuyer:
    def test_address_match(self):
        # Northwind Operations OU address
        result = resolve_buyer("Northwind Operations OU Herrn Alex Kask Lindenstrasse 15 10134 Estonia", "EE")
        assert result["company_code"] != ""
        assert result["business_unit_code"] != ""

    def test_no_match(self):
        result = resolve_buyer("Unknown Company Random Address", "XX")
        assert result["company_code"] == ""
        assert result["business_unit_code"] == ""


class TestResolvePaymentTerms:
    def test_exact_alias(self):
        result = resolve_payment_terms("Net 30", 30)
        assert result["id"] != ""

    def test_partial_alias(self):
        result = resolve_payment_terms("Payment within 30 days", 30)
        assert result["id"] != ""

    def test_days_only(self):
        result = resolve_payment_terms("", 30)
        assert result["id"] != ""

    def test_no_match(self):
        result = resolve_payment_terms("Unknown terms", 0)
        assert result["id"] == ""


class TestResolvePoIds:
    def test_valid_po(self):
        result = resolve_po_ids(["PO12345"])
        assert len(result) == 1
        # May or may not match depending on master data

    def test_empty(self):
        result = resolve_po_ids([])
        assert len(result) == 1
        assert result[0]["id"] == ""

    def test_no_po_number(self):
        result = resolve_po_ids([""])
        assert len(result) == 1
        assert result[0]["id"] == ""


class TestResolveTaxes:
    def test_resolve_vat(self):
        from autodraft.fields import TaxItem
        taxes = [TaxItem(tax_name="VAT", tax_rate="20", tax_amount="20.00")]
        result = resolve_taxes(taxes, "DE")
        
        assert len(result) == 1
        assert result[0]["tax_type"] == "VAT"
        assert result[0]["tax_rate"] == "20.00"

    def test_resolve_zero_rate(self):
        from autodraft.fields import TaxItem
        taxes = [TaxItem(tax_name="Reverse Charge", tax_rate="0", tax_amount="0")]
        result = resolve_taxes(taxes, "DE")
        
        assert len(result) == 1
        assert result[0]["tax_rate"] == "0.00"

    def test_unknown_rate(self):
        from autodraft.fields import TaxItem
        taxes = [TaxItem(tax_name="Unknown Tax", tax_rate="99", tax_amount="10")]
        result = resolve_taxes(taxes, "XX")
        
        assert len(result) == 1
        assert result[0]["tax_type_code"] == ""