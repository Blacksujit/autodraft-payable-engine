import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.audit import run_audit
res = run_audit()
print("total results:", len(res))
issues = [r for r in res if r.get("issues")]
print("documents with issues:", len(issues))
for r in issues:
    print("###", r.get("file"))
    for i in r["issues"]:
        print("   ", i)
