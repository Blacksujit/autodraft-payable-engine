import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.ocr import ocr_words
for i in range(2):
    words = ocr_words(f".work/inv06_p{i}.png")
    print("==== page", i, "words", len(words), "====")
    print("\n".join(w[1] for w in words))
