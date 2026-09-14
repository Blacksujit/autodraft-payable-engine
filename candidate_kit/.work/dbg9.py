import pymupdf
d=pymupdf.open("documents/INV-06.pdf")
print("pages:",len(d))
for i,p in enumerate(d):
    t=p.get_text() or ""
    t=" ".join(t.split())
    print(f"--- pdf page {i} len={len(t)}: {t[:130]!r}")
d.close()
