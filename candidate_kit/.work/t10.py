import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
res, ext, raw, placement, note = process_pdf_detail("documents/INV-10.pdf")
print("=== PAGE TEXT ===")
print(ext.page_text)
