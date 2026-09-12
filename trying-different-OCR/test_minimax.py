import urllib.request
import json
import base64
import pypdf
import io
from PIL import Image

# Test minimax-m3:cloud with just text first
def ollama_chat(model, messages, timeout=120):
    url = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get('message', {}).get('content', '')
    except Exception as e:
        return f"ERROR: {e}"

# Test with text
print("Testing minimax-m3:cloud with text...")
result = ollama_chat("minimax-m3:cloud", [
    {"role": "user", "content": "What is 3+3? Answer with just the number."}
], timeout=30)
print(f"Result: {result}")
