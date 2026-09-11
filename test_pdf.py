import pdfplumber
import os

doc_dir = 'D:/candidate_kit/candidate_kit/documents'

with pdfplumber.open(os.path.join(doc_dir, 'INV-01.pdf')) as pdf:
    print(f'Pages: {len(pdf.pages)}')
    page = pdf.pages[0]
    text = page.extract_text()
    tlen = len(text) if text else 0
    print(f'Text length: {tlen}')
    if text:
        print(repr(text[:200]))
    else:
        print('EMPTY')
    imgs = page.images
    print(f'Images on page: {len(imgs)}')
    if imgs:
        print('First image keys:', list(imgs[0].keys()))
