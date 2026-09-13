import os, sys, io
sys.path.insert(0, os.getcwd())
from pathlib import Path
from autodraft.audit import run_audit
from autodraft.pipeline import run_folder
out = Path(".work/reout"); out.mkdir(parents=True, exist_ok=True)
run_folder("documents", str(out))
results = run_audit()
buf = io.StringIO()
for r in results:
    st = r.get("status")
    iss = r.get("issues") or []
    flag = ""
    if iss:
        flag = "  <<<"
    print(f"{r.get('file','?'):12s} {str(st):10s} issues={len(iss)}{flag}", file=buf)
    for it in iss:
        print(f"        - {it}", file=buf)
Path(".work/audit_report.txt").write_text(buf.getvalue(), encoding="utf-8")
print(buf.getvalue())
