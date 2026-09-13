import sys
sys.path.insert(0,".")
import autodraft.pipeline as pl
for name in ["DU-03","INV-06","INV-14","INV-15","INV-34"]:
    f = "documents/%s.pdf" % name
    r = pl.process_pdf(f)
    print("="*30, name)
    print("SUBTOT", {k:(v if not isinstance(v,list) else v[:1]) for k,v in r.items() if k not in ("line_items","payables","declined")})
