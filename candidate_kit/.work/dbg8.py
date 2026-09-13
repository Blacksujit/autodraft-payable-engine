import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
from autodraft.ocr import ocr_words
from autodraft.structure import build_layout
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")

for f in ["INV-11"]:
    ndoc = P.pymupdf.open("documents/%s.pdf"%f)
    npg = len(ndoc)
    ndoc.close()
    print("==== %s (%d pages)" % (f, npg))
    for pg in range(npg):
        P._render_page("documents/%s.pdf"%f, pg)
        words = ocr_words(P.WORK_DIR / ("%s_p%d.png"%(f,pg+1)))
        lay = build_layout(str(P.WORK_DIR / ("%s_p%d.png"%(f,pg+1))), pg, words)
        print("-- page %d: %d lines, %d items in table" % (pg+1, len(lay.get("lines",[])), len(lay.get("table",[]))))
        for r in lay.get("table", []):
            print("   row:", r)