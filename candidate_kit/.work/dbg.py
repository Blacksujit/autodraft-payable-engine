import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
import autodraft.fields as F
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")
S = __import__("autodraft.structure", fromlist=["x"])
for pg in [0,1]:
    P._render_page("documents/INV-06.pdf", pg)
    words = ocr_words(".work/pages/INV-06_p%d.png" % (pg+1))
    layout = build_layout(".work/pages/INV-06_p%d.png" % (pg+1), pg, words)
    ext = F.extract(layout)
    print("p%d gross=%r ground=%r" % (pg+1, ext.gross, ext.ground.get("gross")))
    print("    items:", len(ext.line_items))
