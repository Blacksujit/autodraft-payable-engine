"""Render PDFs to page images and harvest embedded text layers.

Strategy per page:
  * If the page has a rich text layer (embedded, extractable), use pdfplumber
    words -> Word objects directly (they carry precise boxes).
  * Otherwise render the page to a PNG (DPI ~200) for OCR.
We keep the pull of 'which pages need OCR' explicit so the pipeline can
decide cheaply.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

DEFAULT_DPI = 200


@dataclass
class PageSource:
    """One extracted page: its words (text-layer or OCR), path, and index."""

    path: str  # PDF path
    page_index: int  # 0-based
    words: List  # list of Word (from .geom)
    ocr: bool
    render_path: Optional[str] = None
    text: str = ""


def _pdfplumber_words(path: str, page_index: int) -> List:
    import pdfplumber

    words = []
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_index]
        for w in page.extract_words(x_tolerance=1.5, keep_blank_chars=False, use_text_flow=False):
            from autodraft.geom import Box, Word

            words.append(Word(Box(w["x0"], w["top"], w["x1"], w["bottom"]), w["text"], 1.0))
    return words


def page_has_text(path: str, page_index: int, min_chars: int = 12) -> bool:
    try:
        import fitz

        with fitz.open(path) as doc:
            return len(doc[page_index].get_text().strip()) >= min_chars
    except Exception:
        return False


def render_page(path: str, page_index: int, out_png: str, dpi: int = DEFAULT_DPI) -> str:
    import fitz

    with fitz.open(path) as doc:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        pix.save(out_png)
    return out_png


def iter_pages(path: str, ocr_engine=None, workdir: str = ".work") -> List[PageSource]:
    """Split a PDF into PageSource objects. Pages with a text layer are read
    directly; the rest are rendered to PNG and queued for OCR by the caller."""
    import fitz

    pages = []
    with fitz.open(path) as doc:
        n = len(doc)
        for i in range(n):
            txt = doc[i].get_text().strip()
            src = PageSource(path=path, page_index=i, words=[], ocr=False, text=txt)
            if len(txt) >= 12:
                src.words = _pdfplumber_words(path, i)
            else:
                src.ocr = True
                os.makedirs(workdir, exist_ok=True)
                png = os.path.join(workdir, f"{os.path.basename(path)}_{i}.png")
                render_page(path, i, png)
                src.render_path = png
            pages.append(src)
    return pages