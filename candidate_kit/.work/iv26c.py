import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _render_page, WORK_DIR
from autodraft.ocr import ocr_words
from autodraft.geom import cluster_lines, group_lines_by_bands
from autodraft.structure import build_layout
from autodraft.fields import extract
pdf="documents/INV-26.pdf"
_render_page(pdf, 0)
pp = WORK_DIR / "INV-26_p1.png"
words = ocr_words(str(pp))
layout = build_layout(str(pp), 0, words)
ext = extract(layout)
print(layout.page_text[:4000].replace("\n"," | "))
