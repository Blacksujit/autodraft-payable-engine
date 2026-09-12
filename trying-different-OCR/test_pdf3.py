import pypdf
import os
import io
import base64
from PIL import Image

doc_dir = 'D:/candidate_kit/candidate_kit/documents'

reader = pypdf.PdfReader(os.path.join(doc_dir, 'INV-01.pdf'))
print(f'Pages: {len(reader.pages)}')

page = reader.pages[0]
resources = page.get('/Resources', {})
print('Resource keys:', list(resources.keys()) if resources else 'none')

# Try to get images via pypdf
try:
    images = list(reader.pages[0].images)
    print(f'Images found: {len(images)}')
    if images:
        img = images[0]
        print(f'Image name: {img.name}')
        print(f'Image data type: {type(img.data)}')
        # Save it
        pil_img = Image.open(io.BytesIO(img.data))
        pil_img.save('D:/candidate_kit/inv01_extracted.png')
        print(f'Saved: {pil_img.size}')
        
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        print(f'Base64 length: {len(b64)}')
except Exception as e:
    print(f'Error: {e}')
