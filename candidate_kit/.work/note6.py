import sys
sys.path.insert(0,".")
import autodraft.pipeline as pl
for name in ["DU-03","INV-06","INV-14","INV-15","INV-34"]:
    try:
        r, ext, raw, placement, note = pl.process_pdf_detail("documents/%s.pdf"%name)
        ps = r.get("payables")
        g = (ps[0].get("gross_total") if ps else None)
        print("%-7s PAYABLE=%s placement=%s notes=%s" % (name, g, placement, note))
    except Exception as e:
        print(name, "ERR", e)
