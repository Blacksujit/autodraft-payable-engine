import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import _extract_doc
ext, texts = _extract_doc(str(Path("documents/INV-06.pdf")))
for i, t in enumerate(texts):
    print("="*30, "page", i, "len", len(t))
    print(t[:4000])
