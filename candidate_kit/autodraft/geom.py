"""Geometry primitives: words, lines, bboxes, and page-scale awareness.

All coordinates are in the SAME space as the engine that produced them
(OCR quad points or pdfplumber/fitz points). We never assume an absolute
page size; every structural decision is ratio-based or relative.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    # Aliases for test compatibility
    width = property(lambda self: self.w)
    height = property(lambda self: self.h)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)

    def overlap_y(self, other: "Box", tol: float = 0.0) -> float:
        return max(0.0, min(self.y1, other.y1) - max(self.y0, other.y0) + tol)

    def overlaps(self, other: "Box", tol: float = 0.0) -> bool:
        """Check if boxes overlap (alias for intersects)."""
        return self.intersects(other, tol, tol)

    def contains(self, other: "Box", tol: float = 0.0) -> bool:
        """Check if this box contains another box."""
        return (
            self.x0 - tol <= other.x0
            and self.y0 - tol <= other.y0
            and self.x1 + tol >= other.x1
            and self.y1 + tol >= other.y1
        )

    def union_with(self, other: "Box") -> "Box":
        return Box(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def intersects(self, other: "Box", x_tol: float = 0.0, y_tol: float = 0.0) -> bool:
        return not (
            self.x1 + x_tol < other.x0
            or other.x1 + x_tol < self.x0
            or self.y1 + y_tol < other.y0
            or other.y1 + y_tol < self.y0
        )

    @classmethod
    def from_quad(cls, quad: Iterable[Iterable[float]]) -> "Box":
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        return cls(min(xs), min(ys), max(xs), max(ys))


@dataclass
class Word:
    box: Box
    text: str
    conf: float = 1.0

    @property
    def bbox(self) -> Box:
        return self.box


@dataclass
class Line:
    """A visual line: words that sit on the same baseline band."""

    words: List[Word] = field(default_factory=list)
    conf: float = 1.0

    def add(self, w: Word) -> None:
        self.words.append(w)

    @property
    def box(self) -> Box:
        if not self.words:
            return Box(0, 0, 0, 0)
        b = self.words[0].box
        for w in self.words[1:]:
            b = b.union_with(w.box)
        return b

    @property
    def text(self) -> str:
        words = sorted(self.words, key=lambda w: w.box.x0)
        return " ".join(w.text for w in words)

    @property
    def y_center(self) -> float:
        """Vertical center of the line."""
        if not self.words:
            return 0.0
        return sum(w.box.cy for w in self.words) / len(self.words)

    def tokens(self) -> List[Tuple[Box, str]]:
        return [(w.box, w.text) for w in sorted(self.words, key=lambda w: w.box.x0)]


def cluster_lines(words: Iterable[Word], gap_ratio: float = 0.35) -> List[Line]:
    """Cluster words into visual lines by y-band overlap.

    Two words join the same line if their vertical ranges overlap by a
    meaningful fraction of the smaller word's height.
    """
    wlist = sorted(words, key=lambda w: (w.box.y0, w.box.x0))
    lines: List[Line] = []
    for w in wlist:
        placed = False
        for ln in lines:
            lnbox = ln.box
            overlap = lnbox.overlap_y(w.box)
            min_h = min(max(lnbox.h, 1e-9), max(w.box.h, 1e-9))
            if overlap >= gap_ratio * min_h:
                ln.add(w)
                placed = True
                break
        if not placed:
            lines.append(Line(words=[w]))
    lines.sort(key=lambda ln: (ln.box.y0, ln.box.x0))
    return lines


def group_lines_by_bands(lines: Iterable[Line], gap_ratio: float = 0.6) -> List[List[Line]]:
    """Group already-clustered lines into text rows: lines whose y-bands
    heavily overlap (multi-line cell / wrapped paragraph) become one row."""
    ll = sorted(lines, key=lambda ln: (ln.box.y0, ln.box.x0))
    bands: List[List[Line]] = []
    for ln in ll:
        if bands:
            last = bands[-1]
            b = last[-1].box
            overlap = b.overlap_y(ln.box)
            min_h = min(max(b.h, 1e-9), max(ln.box.h, 1e-9))
            if overlap >= gap_ratio * min_h:
                last.append(ln)
                continue
        bands.append([ln])
    return bands


def reading_text(lines: Iterable[Line]) -> str:
    return "\n".join(ln.text for ln in sorted(lines, key=lambda ln: (ln.box.y0, ln.box.x0)))