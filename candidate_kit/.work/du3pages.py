import sys
sys.path.insert(0,".")
import autodraft.pipeline as pl
doc = "documents/DU-03.pdf"
pdf_extracts = pl._extract_doc(doc)
print(type(pdf_extracts), len(pdf_extracts) if hasattr(pdf_extracts,"__len__") else "?")
ext = pdf_extracts[0]
print("merged ext gross:", ext.gross, "sub:", ext.subtotal, "tax:", ext.tax_total, "ppl:", len(ext.line_items))
pe_txts = pdf_extracts[1]
print("page_texts count:", len(pe_txts))
for i,t in enumerate(pe_txts):
    print("P%d:"%i, t[:320].replace("\n"," | "))
