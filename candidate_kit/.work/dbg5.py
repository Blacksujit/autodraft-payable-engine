import sys, os
sys.path.insert(0, r"D:\candidate_kit\candidate_kit")
os.chdir(r"D:\candidate_kit\candidate_kit")
import autodraft.pipeline as P
P.WORK_DIR = P.Path(r"D:\candidate_kit\candidate_kit\.work")
for f in ["INV-11","INV-13","INV-14","INV-16"]:
    r = P.process_pdf("documents/%s.pdf"%f, ".work")
    d = r.get("declined",[{}])[0]
    print("==== %s" % f)
    print("  gross_mismatch:", d.get("reason","")[:200])
    print()
