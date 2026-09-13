import sys, glob, re
sys.path.insert(0,".")
from autodraft.pipeline import _extract_doc, _render_page
for f in sorted(glob.glob("documents/*.pdf")):
    try:
        txt = _render_page(f, 0)
    except Exception as e:
        print(f, "render err", repr(e)); continue
    if "675" in txt or "700" in txt or "667" in txt:
        hits = [ln for ln in txt.splitlines() if re.search(r"675|700|667", ln)]
        print(f, "::", [h.strip()[:90] for h in hits[:8]])
