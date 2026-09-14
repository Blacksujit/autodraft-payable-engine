import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import _render_page, WORK_DIR
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
pdf="documents/INV-26.pdf"
_render_page(pdf, 0)
pp = WORK_DIR / "INV-26_p1.png"
layout = build_layout(str(pp), 0, ocr_words(str(pp)))
t = layout.table
print("columns:", [(c.index, round(c.center,1)) for c in t.columns], "money_cols:", t.money_cols)
for row in sorted(t.rows):
    cells = t.rows[row]
    for col, items in sorted(cells.items()):
        txt = " ".join(b.text for b,_ in items)
        if txt.strip():
            print(f"  row {row} col {col}: {txt[:60]}")
