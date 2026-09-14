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
print("layout type:", type(layout))
t = getattr(layout, "table", None)
print("table:", t)
for attr in ("tables","blocks","bands"):
    if hasattr(layout, attr):
        print(attr, len(getattr(layout, attr)))
