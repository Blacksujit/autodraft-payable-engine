import sys, os, re
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.pipeline as P
import autodraft.fields as F
doc, texts = P._extract_doc(str(Path("documents")/"DU-03.pdf"))
print("crude gross/source:", doc.gross, doc.source_page, "gr:", repr(doc.ground))
exs=[doc.extracts] if hasattr(doc,"extracts") else None
print("has extracts attr:", hasattr(doc,"extracts"), "tex keys sample:", list(texts)[:3])
# find per-page money words for the source page
from decimal import Decimal
for tid, t in texts.items():
    if t:
        mon = sorted({m for m in re.findall(r"\d[\d.,]*", t) if ',' in m or '.' in m}, key=lambda s: -len(s))[:8]
        print(f"  [page {tid}? part={tid}] money-like: {mon}")
