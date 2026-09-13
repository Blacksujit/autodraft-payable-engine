"""
Tests for autodraft.structure module
"""

import pytest
from autodraft.structure import (
    build_layout, PageLayout, Table, Column, clean_numeric, 
    amount_value, _has_decimal, _numeric_word, _strip_currency,
    _cluster_centers
)
from autodraft.geom import Word, Line, Box, cluster_lines, group_lines_by_bands


class TestCleanNumeric:
    def test_clean_basic(self):
        assert clean_numeric("100") is True
        assert clean_numeric("100.50") is True
        assert clean_numeric("-50.25") is True

    def test_clean_with_currency(self):
        assert clean_numeric("$100") is True
        assert clean_numeric("€100,50") is True
        assert clean_numeric("£1,234.56") is True

    def test_clean_invalid(self):
        assert clean_numeric("abc") is False
        assert clean_numeric("") is False
        assert clean_numeric("100abc") is False
        assert clean_numeric("100.50.30") is False


class TestAmountValue:
    def test_parse_valid(self):
        assert amount_value("100") == 100.0
        assert amount_value("100.50") == 100.50
        assert amount_value("-50.25") == -50.25

    def test_parse_with_currency(self):
        from decimal import Decimal
        assert amount_value("\u20ac100") == Decimal("100")
        assert amount_value("\u20ac100,50") == Decimal("100.50")
        assert amount_value("\u00a31,234.56") == Decimal("1234.56")

    def test_parse_invalid(self):
        assert amount_value("abc") is None
        assert amount_value("") is None


class TestHasDecimal:
    def test_has_decimal(self):
        assert _has_decimal("100.50") is True
        assert _has_decimal("100,50") is True
        assert _has_decimal("100") is False


class TestNumericWord:
    def test_numeric(self):
        word = Word(Box(0, 0, 50, 20), "100.50", 0.9)
        result = _numeric_word(word)
        assert result == 100.5

    def test_non_numeric(self):
        word = Word(Box(0, 0, 50, 20), "abc", 0.9)
        result = _numeric_word(word)
        assert result is None


class TestStripCurrency:
    def test_strip_basic(self):
        assert _strip_currency("$100") == "100"
        assert _strip_currency("€100,50") == "100,50"
        assert _strip_currency("-$50") == "-50"


class TestClusterCenters:
    def test_cluster_simple(self):
        centers = [10.0, 12.0, 14.0, 100.0, 102.0]
        clusters = _cluster_centers(centers, 5.0)
        assert len(clusters) == 2
        assert len(clusters[0]) == 3
        assert len(clusters[1]) == 2

    def test_cluster_empty(self):
        assert _cluster_centers([], 5.0) == []

    def test_cluster_single(self):
        clusters = _cluster_centers([10.0], 5.0)
        assert len(clusters) == 1
        assert clusters[0] == [10.0]


class TestBuildLayout:
    def test_build_layout_simple(self):
        words = [
            Word(Box(0, 0, 100, 20), "Invoice", 0.9),
            Word(Box(0, 30, 100, 50), "Date:", 0.9),
            Word(Box(110, 30, 200, 50), "2026-01-15", 0.9),
            Word(Box(0, 80, 100, 100), "Total:", 0.9),
            Word(Box(110, 80, 200, 100), "100.00", 0.9),
        ]
        
        layout = build_layout("test.png", 0, words)
        
        assert isinstance(layout, PageLayout)
        assert layout.path == "test.png"
        assert layout.page_index == 0

    def test_header_footer_detection(self):
        words = [
            Word(Box(0, 0, 100, 20), "Invoice", 0.9),
            Word(Box(0, 30, 100, 50), "Date:", 0.9),
            Word(Box(110, 30, 200, 50), "2026-01-15", 0.9),
            Word(Box(0, 80, 100, 100), "Total:", 0.9),
            Word(Box(110, 80, 200, 100), "100.00", 0.9),
        ]
        
        layout = build_layout("test.png", 0, words)
        
        assert hasattr(layout, 'header_lines')
        assert hasattr(layout, 'footer_lines')
        assert hasattr(layout, 'body_lines')


class TestTable:
    def test_table_creation(self):
        columns = [
            Column(0, 50, 0, 100),
            Column(1, 150, 100, 200),
        ]
        table = Table(0, 100, columns=columns)
        
        assert table.y0 == 0
        assert table.y1 == 100
        assert len(table.columns) == 2

    def test_table_cell(self):
        columns = [
            Column(0, 50, 0, 100, {}),
            Column(1, 150, 100, 200, {}),
        ]
        table = Table(0, 100, columns=columns)
        table.rows = {
            0: {0: [(Box(0, 0, 100, 20), "Desc")], 1: [(Box(100, 0, 200, 20), "100")]}
        }
        
        cell = table.cell(0, 0)
        assert cell == "Desc"
        
        cell = table.cell(0, 1)
        assert cell == "100"


class TestIntegration:
    def test_build_layout_then_extract(self):
        """Test the full pipeline: words -> layout -> extract"""
        from autodraft.fields import extract
        
        words = [
            Word(Box(0, 0, 100, 20), "Invoice", 0.9),
            Word(Box(0, 30, 100, 50), "Date:", 0.9),
            Word(Box(110, 30, 200, 50), "2026-01-15", 0.9),
            Word(Box(0, 80, 100, 100), "Total:", 0.9),
            Word(Box(110, 80, 200, 100), "100.00", 0.9),
        ]
        
        layout = build_layout("test.png", 0, words)
        ext = extract(layout)
        
        assert ext is not None
        assert ext.path == "test.png"
        assert ext.page_index == 0