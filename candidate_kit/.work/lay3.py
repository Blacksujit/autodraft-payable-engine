import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _render_page
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
from autodraft.pipeline import WORK_DIR
from pathlib import Path
pdf = "documents/INV-10.pdf"
_render_page(pdf, 0)
pp = WORK_DIR / f"{Path(pdf).stem}_p{1}.png"
words = ocr_words(str(pp))
layout = build_layout(str(pp), 0, words)
for ln in layout.footer_lines:
    print(type(ln).__name__, repr(getattr(ln, "text", None)), getattr(ln, "y0", None), getattr(ln, "y1", None))
    bs = getattr(ln, "boxes", None)
    if bs:
        for b in bs[:12]:
            print("   box:", round(b.x0,1), round(b.y0,1), round(b.x1,1), repr(getattr(b,'text','')))
