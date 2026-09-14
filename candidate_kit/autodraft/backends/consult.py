"""consult.py - the Ollama evidence re-phraser seam.

Contract (per Phase 4 / G4):
  * Called only for LOW-CONFIDENCE documents (the deterministic extractor
    already declined or returned a no-gross result).
  * The LLM output is a SHORT NARRATIVE that paraphrases which amount the page
    prints as owed and where it sits. It never supplies a number the core did
    not already see, and the pipeline never books from it.
  * Fail-open: if Ollama is down or the response is unusable we return None and
    the caller emits the deterministic decline unchanged.

No response from this module is ever treated as authoritative data.
"""
from __future__ import annotations

import os

from . import ollama

TEXT_MODEL = "llama3.2"
VISION_MODEL = "moondream"

_ENABLED = os.environ.get("AUTODRAFT_CONSULT", "0").lower() in ("1", "true", "yes", "on")


def enabled() -> bool:
    return _ENABLED


def _bounded_window(text: str, needle: str, radius: int = 700) -> str:
    """Small deterministic slice of the page text around a keyword."""
    idx = text.lower().find(needle.lower() if needle else "")
    if idx < 0:
        return text[: radius * 2]
    start = max(0, idx - radius)
    return text[start : min(len(text), idx + radius)]


_EVIDENCE_SYSTEM = (
    "You are a document examiner. A deterministic parser failed on an invoice page. "
    "You are given a fragment of the page text around the probable total. "
    "Restate, in at most 2 short sentences, WHICH amount the supplier states as the "
    "sum owed, exactly as printed, and where it appears (grand total line, item row, "
    "tax line). Do NOT compute, reformat, or invent amounts. If you cannot find a "
    "printed 'owed' amount, say exactly: NO_OWED_AMOUNT."
)


def _clean_reply(text: str | None, limit: int = 200) -> str | None:
    if not text:
        return None
    reply = " ".join(text.split())
    reply = reply.replace("NO_OWED_AMOUNT", "no printed 'owed' amount visible")
    if len(reply) > limit:
        reply = reply[:limit].rsplit(" ", 1)[0] + "…"
    return reply or None


def evidence(model: str = TEXT_MODEL) -> str | None:
    """Sanity marker: cheap way for tooling to prove the seam is wired."""
    return ollama.text(model, "Reply with exactly: EVIDENCE_OK", timeout=6)


def reread_fragment(page_text: str, near: str, model: str = TEXT_MODEL) -> str | None:
    """Re-phrase the evidence near `near` (e.g. printed gross, last footer line)."""
    if not _ENABLED:
        return None
    frag = _bounded_window(page_text, near)
    prompt = ("Page fragment:\n'''\n" + frag + "\n'''\n\nWhat amount is owed and where is it printed?")
    return _clean_reply(ollama.text(model, prompt, system=_EVIDENCE_SYSTEM, timeout=12))


def describe(page_text: str, png_bytes: bytes, model: str = VISION_MODEL) -> str | None:
    """Vision re-phrase for pathological scans: describe the table/total region."""
    if not _ENABLED:
        return None
    prompt = (
        "Describe ONLY the invoice total region: which line is the grand total, "
        "what amount is printed, and is it labelled with a word like Total/Sum/Betrag. "
        "Do not compute or read other fields."
    )
    frag = page_text[:1200]
    return _clean_reply(ollama.image(model, prompt + "\n\nOCR fragment near total: " + frag[:400], png_bytes, timeout=25), 240)