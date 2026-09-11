import pdfplumber
import os
import io
import base64
from PIL import Image

doc_dir = 'D:/candidate_kit/candidate_kit/documents'

with pdfplumber.open(os.path.join(doc_dir, 'INV-01.pdf')) as pdf:
    page = pdf.pages[0]
    # Try to get the page as image
    img = page.to_image(resolution=150)
    print(type(img))
    # Save it
    img.save('D:/candidate_kit/inv01_test.png')
    print('Saved')
    
    # Convert to base64 for API
    buf = io.BytesIO()
    img.original.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f'Base64 length: {len(b64)}')
