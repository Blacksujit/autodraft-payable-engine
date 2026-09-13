import sys, glob, re
sys.path.insert(0,".")
import autodraft.pipeline as pl
from autodraft.structure import build_layout
seen = 0
for f in sorted(glob.glob("documents/*.pdf")):
    styl = re.sub(r"\d+[A-Za-z]?$", "", f.split("\\")[-1][:-4])
    doc = pl._extract_doc(f)
    ext = doc[0]
    if ext is None: continue
    txts = ext.page_text or ""
    for e2 in [ext.page_text] if False else []:
        pass
    allt = (ext.page_text or "")
    if re.search(r"\bgst\b", allt, re.I) or re.search(r"ex\s*gst", allt, re.I):
        seen += 1
        hits = [l.strip()[:80] for l in allt.splitlines() if re.search(r"gst", l, re.I)]
        print(f, "gross=", ext.gross, "sub=", ext.subtotal, "tax_total=", ext.tax_total, "| GST hits:", hits[:5])
print("total docs w/ gst words:", seen)
