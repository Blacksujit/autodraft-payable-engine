import sys, glob, re
sys.path.insert(0,".")
import autodraft.pipeline as pl
from autodraft.structure import build_layout
for f in sorted(glob.glob("documents/*.pdf")):
    name = f.split("\\")[-1][:-4]
    png = pl.WORK_DIR / (name + "_p1.png")
    if not png.exists():
        continue
    words = pl.ocr_words(str(png))
    layout = build_layout(str(png), 0, words)
    txt = (layout.header_text or "") + " " + (layout.footer_text or "")
    m = re.findall(r"Sub[\s\-]*Total\w*|Subtotal", txt, re.I)
    if m:
        matches = [x.strip() for x in re.findall(r"[^\n]*Sub[\s\-]*Total[^\n]*", txt, re.I)]
        print(name, "->", [mm[:70] for mm in matches][:4])
