import sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
import autodraft.fields as F
import autodraft.pipeline as P
ext, texts = P._extract_doc(str(Path("documents")/"INV-06.pdf"))
for pi,t in enumerate(texts):
    print(f"----- page {pi} ({len(t.splitlines())} lines)")
    for li,line in enumerate(t.splitlines()):
        items=[]
        for pat in F._STRONG_TOTAL_LABELS:
            for m in pat.finditer(line.lower()):
                it=F._window_read(line, m.end())
                if it: items.append((m.group(0), it))
        print(f"  L{li}: {line[:110]!r}")
        for lab,it in items[:6]:
            print(f"      STRONG[{lab}] -> {[(str(x[0]),bool(x[1]),x[2]) for x in it[:3]]}")
