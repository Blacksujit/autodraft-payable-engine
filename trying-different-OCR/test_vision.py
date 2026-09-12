import urllib.request
import json
import base64
import pypdf
import io
from PIL import Image

def get_pdf_image_b64(pdf_path, page_num=0, max_dim=1024):
    """Extract page as JPEG base64 from a PDF."""
    reader = pypdf.PdfReader(pdf_path)
    page = reader.pages[page_num]
    
    images = list(page.images)
    if images:
        img_data = images[0].data
        try:
            pil_img = Image.open(io.BytesIO(img_data))
            # Convert to RGB (JPEG requires RGB)
            if pil_img.mode not in ('RGB', 'L'):
                pil_img = pil_img.convert('RGB')
            # Resize
            w, h = pil_img.size
            if max(w, h) > max_dim:
                ratio = max_dim / max(w, h)
                pil_img = pil_img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG', quality=85)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            print(f"Error converting image: {e}")
            return None
    return None

def ollama_vision_chat(model, image_b64, prompt, timeout=120):
    """Query Ollama with image + text."""
    url = "http://127.0.0.1:11434/api/chat"
    messages = [{
        "role": "user",
        "content": prompt,
        "images": [image_b64]
    }]
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get('message', {}).get('content', '')
    except Exception as e:
        return f"ERROR: {e}"

# Test with INV-01.pdf
print("Testing moondream with INV-01.pdf...")
b64 = get_pdf_image_b64('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
if b64:
    print(f"Image extracted ({len(b64)} chars)")
    prompt = "What does this document show? Is it an invoice? If so, what is the invoice number, date, supplier name, and total amount?"
    result = ollama_vision_chat("moondream:latest", b64, prompt)
    print("Result:", result[:500])
else:
    print("Could not extract image")
