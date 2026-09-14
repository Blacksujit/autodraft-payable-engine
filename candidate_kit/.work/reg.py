import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import run_folder
run_folder("documents", "output")
print("regenerated")
