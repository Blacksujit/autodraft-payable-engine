import urllib.request
import json
import base64
import pypdf
import io
from PIL import Image

def get_pdf_images_b64(pdf_path, max_dim=1600):
    """Extract all page images from a PDF as base64 JPEG."""
    reader = pypdf.PdfReader(pdf_path)
    result = []
    for page_num, page in enumerate(reader.pages):
        images = list(page.images)
        if images:
            for img_obj in images:
                try:
                    pil_img = Image.open(io.BytesIO(img_obj.data))
                    # Convert to RGB for JPEG
                    if pil_img.mode not in ('RGB',):
                        pil_img = pil_img.convert('RGB')
                    # Resize if needed
                    w, h = pil_img.size
                    if max(w, h) > max_dim:
                        ratio = max_dim / max(w, h)
                        pil_img = pil_img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
                    buf = io.BytesIO()
                    pil_img.save(buf, format='JPEG', quality=90)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    result.append((page_num, b64, pil_img.size))
                    break  # Just first image per page
                except Exception as e:
                    print(f"Img error p{page_num}: {e}")
    return result

def ollama_vision_generate(model, image_b64, prompt, timeout=180):
    """Query Ollama generate endpoint with image + text."""
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get('response', '')
    except Exception as e:
        return f"ERROR: {e}"

# Test with INV-01.pdf
print("Testing moondream with INV-01.pdf...")
imgs = get_pdf_images_b64('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
if imgs:
    page_num, b64, size = imgs[0]
    print(f"Got image: page={page_num}, size={size}, b64_len={len(b64)}")
    prompt = "Describe this document. What type is it? What are the key numbers you can read?"
    print("Sending to moondream...")
    result = ollama_vision_generate("moondream:latest", b64, prompt, timeout=180)
    print("Result:", repr(result[:800]))
else:
    print("No images found in PDF")
