import pymupdf, os
import sys; sys.path.insert(0, os.getcwd()); from autodraft.ocr import ocr_words
d=pymupdf.open("documents/INV-06.pdf")
for i,p in enumerate(d):
    out=f".work/inv6_page{i}.png"
    p.get_pixmap(matrix=pymupdf.Matrix(2,2), alpha=False).save(out)
    w=ocr_words(out)
    words=" ".join(x.text for x in w[:40])
    print(f"page {i}: {words!r}")
d.close()
