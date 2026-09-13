import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.pipeline import _extract_doc
names = sys.argv[1:] or ["DU-03"]
for name in names:
    p = Path("documents")/(name+".pdf")
    print("="*72); print("##", name)
    try:
        ext, texts = _extract_doc(str(p))
    except Exception as e:
        print("ERR", e); continue
    for i, t in enumerate(texts):
        print(f"--- page {i} ---")
        print(t)
