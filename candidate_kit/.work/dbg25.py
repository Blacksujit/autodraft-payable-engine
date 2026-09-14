import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.ocr import ocr_words
w = ocr_words(r".work/pages/INV-06_p2.png")
def pos(o): return getattr(o, "left", getattr(o,"x",0)), getattr(o, "top", getattr(o,"y",0))
ys = sorted(set(round(pos(o)[1]) for o in w))
for y in ys:
    line = " ".join(o.text for o in sorted([z for z in w if abs(pos(z)[1]-y)<=2], key=lambda z: pos(z)[0]))
    if line.strip(): print(f"{y}: {line}")
