import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
from autodraft.ocr import ocr_words
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")
P._render_page("documents/INV-06.pdf", 1)
words = ocr_words(".work/pages/INV-06_p2.png")
for w in words:
    if w.box.y0 >= 700:
        print("%6.1f %6.1f  %r" % (w.box.x0, w.box.y0, w.text))
