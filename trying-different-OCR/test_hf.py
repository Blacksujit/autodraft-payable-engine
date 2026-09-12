import pypdf
import os
import io
import base64
import json
import urllib.request
import urllib.error
from PIL import Image

HF_TOKEN = os.environ.get('HF_TOKEN', '')

def extract_page_image_b64(pdf_path, page_num=0, max_size=1600):
    """Extract page image from PDF as base64 PNG."""
    reader = pypdf.PdfReader(pdf_path)
    page = reader.pages[page_num]
    
    # Try embedded images first
    images = list(page.images)
    if images:
        img_data = images[0].data
        pil_img = Image.open(io.BytesIO(img_data))
    else:
        # No images - try text
        return None, page.extract_text() or ''
    
    # Resize if too large
    w, h = pil_img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        pil_img = pil_img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    
    buf = io.BytesIO()
    pil_img.save(buf, format='JPEG', quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64, ''

def query_hf_vision(image_b64, prompt, model="Qwen/Qwen2-VL-7B-Instruct"):
    """Query HuggingFace Inference API with image + text."""
    url = f"https://api-inference.huggingface.co/models/{model}"
    
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {
            "image": image_b64,
            "text": prompt
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}: {body[:500]}"}

# Test
b64, text = extract_page_image_b64('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
if b64:
    print(f"Image extracted, base64 length: {len(b64)}")
    prompt = "This is a supplier invoice. Extract the invoice number, invoice date, due date, supplier name, total amount, and line items."
    print("Querying HF API...")
    result = query_hf_vision(b64, prompt)
    print(json.dumps(result, indent=2)[:1000])
else:
    print(f"Text only: {text[:200]}")
