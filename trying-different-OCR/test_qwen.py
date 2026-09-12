import pypdf, urllib.request, json

r = pypdf.PdfReader('D:/candidate_kit/candidate_kit/documents/INV-36.pdf')
text = ''.join(p.extract_text() or '' for p in r.pages)

prompt = """Extract invoice data from this text. Return ONLY valid JSON with these exact fields:
{"invoice_type": "INVOICE or CREDIT_MEMO or DECLINED", "doc_type_if_declined": "", "invoice_number": "", "invoice_date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "currency": "", "gross_total": "", "subtotal": "", "total_tax_amount": "", "supplier_name": "", "supplier_vat_id": "", "buyer_entity": "", "payment_terms_text": "", "po_number": "", "line_items": [], "taxes": []}

Document text:
""" + text + "\n\nRespond with only valid JSON, no explanation."

url = 'http://127.0.0.1:11434/api/chat'
payload = {
    'model': 'qwen2.5:1.5b',
    'messages': [{'role': 'user', 'content': prompt}],
    'stream': False,
    'options': {'temperature': 0}
}
data = json.dumps(payload).encode()
req = urllib.request.Request(url, data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read())
    content = result.get('message', {}).get('content', '')
    print(content[:2000])
