import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.ocr import ocr_words
w = ocr_words(r".work/pages/INV-06_p1.png")
print(type(w[0]), dir(w[0])[:24])
o=w[0]
for a in ("text","x","y","w","h","left","top","width","height"):
    if hasattr(o,a): print(a, getattr(o,a))
print("count", len(w))
