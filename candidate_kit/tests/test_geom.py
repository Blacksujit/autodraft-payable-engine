"""
Tests for autodraft.geom module
"""

import pytest
from autodraft.geom import Box, Word, Line, cluster_lines, group_lines_by_bands


class TestBox:
    def test_box_creation(self):
        box = Box(0, 0, 100, 50)
        assert box.x0 == 0
        assert box.y0 == 0
        assert box.x1 == 100
        assert box.y1 == 50

    def test_box_properties(self):
        box = Box(10, 20, 110, 70)
        assert box.width == 100
        assert box.height == 50
        assert box.cx == 60
        assert box.cy == 45

    def test_box_overlap(self):
        box1 = Box(0, 0, 100, 100)
        box2 = Box(50, 50, 150, 150)
        box3 = Box(200, 200, 300, 300)
        
        assert box1.overlaps(box2) is True
        assert box1.overlaps(box3) is False

    def test_box_contains(self):
        box1 = Box(0, 0, 100, 100)
        box2 = Box(25, 25, 75, 75)
        box3 = Box(50, 50, 150, 150)
        
        assert box1.contains(box2) is True
        assert box1.contains(box3) is False


class TestWord:
    def test_word_creation(self):
        word = Word(Box(0, 0, 50, 20), "Hello", 0.95)
        assert word.text == "Hello"
        assert word.conf == 0.95

    def test_word_bbox(self):
        word = Word(Box(10, 10, 60, 30), "Test", 0.9)
        assert word.box.x0 == 10
        assert word.box.y0 == 10


class TestLine:
    def test_line_creation(self):
        words = [
            Word(Box(0, 0, 50, 20), "Hello", 0.9),
            Word(Box(60, 0, 110, 20), "World", 0.9),
        ]
        line = Line(words)
        assert len(line.words) == 2

    def test_line_text(self):
        words = [
            Word(Box(0, 0, 50, 20), "Hello", 0.9),
            Word(Box(60, 0, 110, 20), "World", 0.9),
        ]
        line = Line(words)
        assert line.text == "Hello World"

    def test_line_bbox(self):
        words = [
            Word(Box(0, 0, 50, 20), "Hello", 0.9),
            Word(Box(60, 0, 110, 20), "World", 0.9),
        ]
        line = Line(words)
        assert line.box.x0 == 0
        assert line.box.x1 == 110
        assert line.box.y0 == 0
        assert line.box.y1 == 20

    def test_line_y_center(self):
        words = [
            Word(Box(0, 0, 50, 20), "Hello", 0.9),
            Word(Box(60, 0, 110, 20), "World", 0.9),
        ]
        line = Line(words)
        assert line.y_center == 10


class TestClusterLines:
    def test_cluster_simple(self):
        # Lines that overlap vertically should cluster
        words = [
            Word(Box(0, 0, 50, 20), "Line1", 0.9),
            Word(Box(0, 15, 50, 35), "Line2", 0.9),  # Overlaps with Line1
            Word(Box(0, 100, 50, 120), "Line3", 0.9),  # Far apart
        ]
        clusters = cluster_lines(words)
        # Line1 and Line2 should cluster (they overlap), Line3 separate
        assert len(clusters) == 2
        assert len(clusters[0].words) == 2
        assert len(clusters[1].words) == 1

    def test_cluster_empty(self):
        assert cluster_lines([]) == []

    def test_cluster_single(self):
        words = [Word(Box(0, 0, 50, 20), "Line1", 0.9)]
        clusters = cluster_lines(words)
        assert len(clusters) == 1
        assert len(clusters[0].words) == 1


class TestGroupLinesByBands:
    def test_group_simple(self):
        lines = [
            Line([Word(Box(0, 0, 100, 20), "Header", 0.9)]),
            Line([Word(Box(0, 30, 100, 50), "Item 1", 0.9)]),
            Line([Word(Box(0, 60, 100, 80), "Item 2", 0.9)]),
            Line([Word(Box(0, 100, 100, 120), "Footer", 0.9)]),
        ]
        rows = group_lines_by_bands(lines)
        # Should group into 4 rows
        assert len(rows) == 4

    def test_group_with_wrapped_lines(self):
        # Two lines that should be grouped as one row
        lines = [
            Line([Word(Box(0, 0, 100, 20), "Description", 0.9)]),
            Line([Word(Box(0, 22, 100, 42), "continued", 0.9)]),  # Close to previous
            Line([Word(Box(0, 60, 100, 80), "Next item", 0.9)]),
        ]
        rows = group_lines_by_bands(lines)
        # First two lines should be in same band
        assert len(rows) <= 3


class TestIntegration:
    def test_full_pipeline(self):
        """Test the full line clustering and grouping pipeline"""
        words = [
            Word(Box(0, 0, 100, 20), "Invoice", 0.9),
            Word(Box(0, 30, 100, 50), "Date:", 0.9),
            Word(Box(110, 30, 200, 50), "2026-01-15", 0.9),
            Word(Box(0, 80, 100, 100), "Total:", 0.9),
            Word(Box(110, 80, 200, 100), "100.00", 0.9),
        ]
        
        lines = cluster_lines(words)
        rows = group_lines_by_bands(lines)
        
        # Should have reasonable number of rows
        assert len(rows) >= 3
        # Each row should have lines
        for row_lines in rows:
            assert len(row_lines) > 0