import pypdf, urllib.request, json, base64, io
from PIL import Image

def get_img_b64(pdf_path, page_num=0, max_dim=1400):
    r = pypdf.PdfReader(pdf_path)
    if page_num >= len(r.pages): return None
    imgs = list(r.pages[page_num].images)
    if not imgs: return None
    pil = Image.open(io.BytesIO(imgs[0].data)).convert('RGB')
    w, h = pil.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        pil = pil.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def ollama_chat(model, messages, timeout=180):
    url = 'http://127.0.0.1:11434/api/chat'
    payload = {'model': model, 'messages': messages, 'stream': False, 'options': {'temperature': 0}}
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read()).get('message', {}).get('content', '')

# Step 1: moondream reads the image
b64 = get_img_b64('D:/candidate_kit/candidate_kit/documents/INV-01.pdf')
print(f"Image size: {len(b64)} b64 chars")

print("\n=== MOONDREAM PASS ===")
ocr_prompt = """Read every piece of text visible in this image. 
List all numbers, dates, names, amounts you can read.
Include: header text, invoice/document number, dates, names, addresses, 
all table rows with their values, tax information, totals.
Read carefully - this may be a financial document."""

raw_text = ollama_chat("moondream:latest", [{"role": "user", "content": ocr_prompt, "images": [b64]}])
print(raw_text[:1000])
print("\n=== END MOONDREAM ===")

# Step 2: qwen2.5 structures it
print("\n=== QWEN PASS ===")
struct_prompt = f"""Based on the following OCR text from a document, extract structured data.
Return ONLY valid JSON with these fields:
{{"invoice_type": "INVOICE|CREDIT_MEMO|DELIVERY_NOTE|PURCHASE_ORDER|STATEMENT|OTHER",
"invoice_number": "",
"invoice_date": "YYYY-MM-DD or empty",
"due_date": "YYYY-MM-DD or empty",
"currency": "ISO code",
"gross_total": "number as string",
"subtotal": "",
"total_tax_amount": "",
"supplier_name": "",
"buyer_entity": "",
"payment_terms_text": "",
"po_number": "",
"line_items": [{{"description": "", "quantity": "", "unit_price": "", "total": ""}}],
"taxes": [{{"tax_name": "", "tax_rate": "", "tax_amount": "", "level": "header or line"}}]
}}

OCR text:
{raw_text}

JSON only, no explanation:"""

structured = ollama_chat("qwen2.5:1.5b", [{"role": "user", "content": struct_prompt}])
print(structured[:2000])
