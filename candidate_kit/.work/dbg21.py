import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.ocr import ocr_words
w = ocr_words(r".work/pages/INV-06_p1.png")
ys = sorted(set(round(y) for _,_,y,*_ in w))
for y in sorted(set(round(x[2]) for x in w)):
    line = " ".join(x[0] for x in sorted([ww for ww in w if abs(ww[2]-y)<=2], key=lambda z:z[0]))
    if line.strip(): print(f"{y}: {line}")
