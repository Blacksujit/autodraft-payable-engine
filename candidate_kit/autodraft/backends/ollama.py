"""ollama.py - minimal local-Ollama client (text + vision).

The consult layer is used ONLY as an evidence re-phraser. Its output is a
short narrative that may sharpen a decline reason or point the deterministic
core at a re-read; its numbers NEVER enter the record. Every call is bounded by
a timeout and fails open (returns None) so the deterministic pipeline is never
blocked or made non-deterministic by the LLM.

Environment:
  OLLAMA_HOST  (default http://127.0.0.1:11434)
"""
from __future__ import annotations

import base64
import os
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:11434"
GEN_TIMEOUT = float(os.environ.get("AUTODRAFT_OLLAMA_TIMEOUT", "12"))


def _host() -> str:
    return os.environ.get("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def _post(path: str, payload: dict, timeout: float) -> dict:
    import json as _json

    data = _json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(_host() + path, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _chat(payload: dict, timeout: float = GEN_TIMEOUT):
    """POST /api/chat, streaming off. Returns the full JSON or None."""
    try:
        return _post("/api/chat", payload, timeout)
    except Exception:
        return None


def ping() -> bool:
    """True when a local Ollama server answers."""
    try:
        body = urllib.request.urlopen(_host() + "/api/tags", timeout=2).read()
        return b"models" in body
    except Exception:
        return False


def list_models():
    """[names] available locally, or []."""
    try:
        import json as _json

        body = urllib.request.urlopen(_host() + "/api/tags", timeout=2).read()
        return [m.get("name", "") for m in _json.loads(body).get("models", [])]
    except Exception:
        return []


def text(model: str, prompt: str, system: str = "", timeout: float = GEN_TIMEOUT) -> str | None:
    """Plain chat completion. Returns the assistant text or None."""
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    resp = _chat({"model": model, "messages": msgs, "stream": False}, timeout)
    if not resp:
        return None
    return resp.get("message", {}).get("content", "").strip() or None


def image(model: str, prompt: str, image_bytes: bytes, timeout: float = GEN_TIMEOUT) -> str | None:
    """Vision chat: attach one image (moondream / llava-style models)."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    msgs = [{"role": "user", "content": prompt, "images": [b64]}]
    resp = _chat({"model": model, "messages": msgs, "stream": False}, timeout)
    if not resp:
        return None
    return resp.get("message", {}).get("content", "").strip() or None