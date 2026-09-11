import os, pypdf, io, warnings
from PIL import Image
warnings.filterwarnings('ignore')

doc_dir = 'D:/candidate_kit/candidate_kit/documents'
img_dir = 'D:/candidate_kit/candidate_kit/images'
os.makedirs(img_dir, exist_ok=True)

for fname in sorted(os.listdir(doc_dir)):
    if not fname.endswith('.pdf'): continue
    base = fname.replace('.pdf', '')
    pdf_path = os.path.join(doc_dir, fname)
    try:
        r = pypdf.PdfReader(pdf_path)
        for page_num, page in enumerate(r.pages):
            img_list = list(page.images)
            if img_list:
                pil = Image.open(io.BytesIO(img_list[0].data)).convert('RGB')
                out_path = os.path.join(img_dir, f'{base}_p{page_num}.jpg')
                if not os.path.exists(out_path):
                    pil.save(out_path, format='JPEG', quality=90)
                    print(f'Saved: {out_path} {pil.size}')
                else:
                    print(f'Skip (exists): {out_path}')
    except Exception as e:
        print(f'Error {fname}: {e}')

# List what we have
imgs = sorted(os.listdir(img_dir))
print(f'\nTotal images saved: {len(imgs)}')
for img in imgs[:5]:
    print(f'  {img}')
