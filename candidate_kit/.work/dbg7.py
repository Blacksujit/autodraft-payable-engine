import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
from autodraft.ocr import ocr_words
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")

for f in ["INV-11","INV-16"]:
    ndoc = P.pymupdf.open("documents/%s.pdf"%f)
    npg = len(ndoc)
    ndoc.close()
    print("==== %s (%d pages)" % (f, npg))
    for pg in range(npg):
        P._render_page("documents/%s.pdf"%f, pg)
        words = ocr_words(P.WORK_DIR / ("%s_p%d.png"%(f,pg+1)))
        lines = {}
        for w in words:
            key = round(w.box.y0, 0)
            lines.setdefault(key, []).append(w)
        print("-- page %d: %d lines" % (pg+1, len(lines)))
        for k in sorted(lines):
            ws = sorted(lines[k], key=lambda w: w.box.x0)
            print("   %5.0f: %s" % (k, " | ".join(w.text for w in ws)))