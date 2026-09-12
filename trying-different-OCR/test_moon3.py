import urllib.request, json, base64, pypdf, io
from PIL import Image

r = pypdf.PdfReader('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
imgs = list(r.pages[0].images)
pil = Image.open(io.BytesIO(imgs[0].data)).convert('RGB')
w, h = pil.size

# Resize to very small
pil_small = pil.resize((400, int(400*h/w)), Image.LANCZOS)
buf = io.BytesIO()
pil_small.save(buf, format='JPEG', quality=85)
b64 = base64.b64encode(buf.getvalue()).decode()
print(f"Small image: {pil_small.size}, b64: {len(b64)}")

url = 'http://127.0.0.1:11434/api/chat'
payload = {
    'model': 'moondream:latest',
    'messages': [{'role': 'user', 'content': 'What is this document?', 'images': [b64]}],
    'stream': False,
    'options': {'num_predict': 200}
}
req = urllib.request.Request(url, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
    print("Response:", result.get('message', {}).get('content', ''))
    print("Eval count:", result.get('eval_count'))
    print("Duration:", result.get('total_duration'))
