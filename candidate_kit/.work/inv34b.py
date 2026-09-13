import sys
sys.path.insert(0,".")
import autodraft.pipeline as pl
from autodraft.structure import build_layout
for pg in (0,1,2):
    png = pl.WORK_DIR / ("INV-34_p%d.png" % (pg+1))
    if not png.exists():
        print("no png", pg); continue
    words = pl.ocr_words(str(png))
    layout = build_layout(str(png), pg, words)
    print("PAGE", pg)
    print(" HEADER:", (layout.header_text or "")[:220])
    print(" FOOTER:", (layout.footer_text or "")[:260])
    print(" PAGE :", (layout.page_text or "")[:220])
