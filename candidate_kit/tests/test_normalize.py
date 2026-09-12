"""
Tests for autodraft.normalize module
"""

import pytest
from decimal import Decimal
from autodraft.normalize import (
    parse_amount, parse_date, detect_currency, quantize_2,
    Amount, DateResolved
)


class TestParseAmount:
    def test_european_format(self):
        """Test European number format (1.234,56)"""
        result = parse_amount("1.234,56")
        assert result is not None
        assert result.value == Decimal("1234.56")
        assert result.ambiguous is False

    def test_us_format(self):
        """Test US number format (1,234.56)"""
        result = parse_amount("1,234.56")
        assert result is not None
        assert result.value == Decimal("1234.56")
        assert result.ambiguous is False

    def test_simple_decimal(self):
        """Test simple decimal (1234.56)"""
        result = parse_amount("1234.56")
        assert result is not None
        assert result.value == Decimal("1234.56")

    def test_integer(self):
        """Test integer (1234)"""
        result = parse_amount("1234")
        assert result is not None
        assert result.value == Decimal("1234")

    def test_negative(self):
        """Test negative numbers"""
        result = parse_amount("-1234.56")
        assert result is not None
        assert result.value == Decimal("-1234.56")

    def test_with_currency_symbol(self):
        """Test with currency symbols"""
        result = parse_amount("$1,234.56")
        assert result is not None
        assert result.value == Decimal("1234.56")

        result = parse_amount("€1.234,56")
        assert result is not None
        assert result.value == Decimal("1234.56")

    def test_thousands_only(self):
        """Test thousands separator only (1.234)"""
        result = parse_amount("1.234")
        assert result is not None
        assert result.value == Decimal("1234")

    def test_ambiguous_case(self):
        """Test ambiguous case (1.234) - could be 1.234 or 1234"""
        result = parse_amount("1.234")
        # Should detect as thousands separator
        assert result is not None

    def test_invalid(self):
        """Test invalid input"""
        assert parse_amount("abc") is None
        assert parse_amount("") is None
        assert parse_amount(None) is None

    def test_percentage(self):
        """Test percentage values"""
        result = parse_amount("15%")
        assert result is not None
        assert result.value == Decimal("15")


class TestParseDate:
    def test_iso_format(self):
        """Test ISO format YYYY-MM-DD"""
        result = parse_date("2026-01-15")
        assert result is not None
        assert result.iso == "2026-01-15"
        assert result.ambiguous is False

    def test_european_format(self):
        """Test European format DD.MM.YYYY"""
        result = parse_date("15.01.2026")
        assert result is not None
        assert result.iso == "2026-01-15"

    def test_us_format(self):
        """Test US format MM/DD/YYYY"""
        result = parse_date("01/15/2026")
        assert result is not None
        assert result.iso == "2026-01-15"

    def test_ambiguous_date(self):
        """Test ambiguous date (01/02/2026)"""
        result = parse_date("01/02/2026")
        # Should be ambiguous
        assert result is not None
        assert result.ambiguous is True

    def test_alpha_month(self):
        """Test alpha month format (15Jan2026)"""
        result = parse_date("15Jan2026")
        assert result is not None
        assert result.iso == "2026-01-15"

    def test_alpha_month_long(self):
        """Test alpha month format (15January2026)"""
        result = parse_date("15January2026")
        assert result is not None
        assert result.iso == "2026-01-15"

    def test_with_locale_hint(self):
        """Test with locale hint"""
        result = parse_date("01/02/2026", locale_hint="dmy")
        assert result is not None
        assert result.iso == "2026-02-01"
        assert result.ambiguous is False

        result = parse_date("01/02/2026", locale_hint="mdy")
        assert result is not None
        assert result.iso == "2026-01-02"
        assert result.ambiguous is False


class TestDetectCurrency:
    def test_euro_symbol(self):
        assert detect_currency("€100") == "EUR"
        assert detect_currency("100 €") == "EUR"
        assert detect_currency("EUR 100") == "EUR"

    def test_dollar(self):
        assert detect_currency("$100") == "USD"
        assert detect_currency("USD 100") == "USD"

    def test_pound(self):
        assert detect_currency("£100") == "GBP"
        assert detect_currency("GBP 100") == "GBP"

    def test_zAR(self):
        assert detect_currency("R 100") == "ZAR"
        assert detect_currency("ZAR 100") == "ZAR"

    def test_no_currency(self):
        assert detect_currency("100") is None


class TestQuantize2:
    def test_round_half_up(self):
        assert quantize_2(Decimal("1.005")) == Decimal("1.01")
        assert quantize_2(Decimal("1.004")) == Decimal("1.00")
        assert quantize_2(Decimal("1.006")) == Decimal("1.01")

    def test_already_quantized(self):
        assert quantize_2(Decimal("1.00")) == Decimal("1.00")
        assert quantize_2(Decimal("1.23")) == Decimal("1.23")

    def test_integer(self):
        assert quantize_2(Decimal("100")) == Decimal("100.00")