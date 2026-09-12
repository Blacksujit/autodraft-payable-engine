import urllib.request, json, base64, pypdf, io
from PIL import Image

r = pypdf.PdfReader('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
imgs = list(r.pages[0].images)
pil = Image.open(io.BytesIO(imgs[0].data)).convert('RGB')
w, h = pil.size
print(f"Full image: {w}x{h}")

# Use full image at good quality
buf = io.BytesIO()
pil.save(buf, format='JPEG', quality=95)
b64 = base64.b64encode(buf.getvalue()).decode()
print(f"B64 len: {len(b64)}")

url = 'http://127.0.0.1:11434/api/chat'
questions = [
    "What text is written at the top of this document?",
    "Can you read the total amount in this document?",
    "What language is this document written in?",
    "Describe this document in detail including all text you can read."
]
for q in questions:
    payload = {
        'model': 'moondream:latest',
        'messages': [{'role': 'user', 'content': q, 'images': [b64]}],
        'stream': False,
        'options': {'num_predict': 300}
    }
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        ans = result.get('message', {}).get('content', '')
        print(f"\nQ: {q}")
        print(f"A: {ans[:300]}")
