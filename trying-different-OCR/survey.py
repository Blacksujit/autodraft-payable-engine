import pypdf, os, sys
doc_dir = 'D:/candidate_kit/candidate_kit/documents'
for fname in sorted(os.listdir(doc_dir)):
    if not fname.endswith('.pdf'): continue
    try:
        r = pypdf.PdfReader(os.path.join(doc_dir, fname))
        text = ''.join(p.extract_text() or '' for p in r.pages)
        pages = len(r.pages)
        imgs = sum(len(list(p.images)) for p in r.pages)
        mode = 'TEXT' if len(text.strip()) > 100 else 'IMAGE'
        print(f'{mode} {fname}: {pages}p, {imgs}img, {len(text)}chars')
    except Exception as e:
        print(f'ERROR {fname}: {e}')
