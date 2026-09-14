import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.audit import run_audit
res = run_audit()
lines = []
for r in res:
    for i in (r.get("issues") or []):
        lines.append(r.get("file") + " :: " + i)
open(".work/audit_report.txt","w",encoding="utf-8").write("\n".join(lines))
print("written", len(lines))
