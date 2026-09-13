import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.ocr import ocr_words
for i in (1,2):
    if not os.path.exists(f".work/pages/INV-16_p{i}.png"):
        continue
    w = ocr_words(f".work/pages/INV-16_p{i}.png")
    print("==== page", i, "words", len(w), "====")
    print("\n".join(x.text for x in w))
