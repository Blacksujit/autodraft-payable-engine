import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import pymupdf
d = pymupdf.open("documents/INV-06.pdf")
for i in range(len(d)):
    pix = d[i].get_pixmap(dpi=200)
    Path(os.path.join(os.getcwd(), f".work/inv06_p{i}.png")).write_bytes(pix.tobytes("png"))
print("rendered ok", os.listdir(".work")[:5])
