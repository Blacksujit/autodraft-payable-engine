import sys, os
sys.path.insert(0, os.getcwd())
txt = open(".work/inv6_pagetext.txt",encoding="utf-8").read()
print("LEN", len(txt))
print(txt[:3800])
