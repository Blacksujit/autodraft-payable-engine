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
print("PageLayout attrs:", [a for a in dir(layout) if not a.startswith("_")])
try:
    print("footer_text:", repr(layout.footer_text)[:800])
except Exception as e:
    print("no footer_text", e)
try:
    print("header_text:", repr(layout.header_text)[:400])
except Exception as e:
    print("no header_text", e)
