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
for row in sorted(t.rows):
    cells = t.rows[row]
    for col, items in sorted(cells.items()):
        parts = []
        for it in items:
            b = it[0] if isinstance(it, tuple) else it
            txt = it[1] if isinstance(it, tuple) and isinstance(it[1], str) else (getattr(b,'text',None) or '')
            if not txt:
                txt = repr(b)[:30]
            parts.append(str(txt))
        line = " ".join(parts)
        if line.strip():
            print(f"  row {row} col {col}: {line[:70]}")
