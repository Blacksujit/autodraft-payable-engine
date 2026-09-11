# AGENTS.md — engineering conventions for this repo

Working conventions for any agent (human or AI) editing this codebase.
The open→held-back distance is the metric; every convention below exists to
serve it.

## Non-negotiables

1. **Zero per-file special-casing.** No `if filename == "INV-03"` logic, ever —
   in code, config, or prompts. If a feature only works for the open set it is
   overfit and is rejected at code review.
2. **No invented numbers.** A value enters the record only if a page word (or a
   derivation from present words) produced it. "Balance-the-books" reasoning is
   a cue to re-read the document, never to patch.
3. **No guessed master codes.** Codes come from `resolve.py` scored matching,
   else honest `""`.
4. **Placement is part of correctness.** Header taxes stay header; line taxes
   stay line. Keep `line_items[]` decomposed (qty/unit/total/discount).
5. **Do not import or monkeypatch `erp.py`.** It is the sealed oracle. We wrap
   it in `oracle.py`; we never edit it.
6. **The oracle gates emission.** A payable ships only when
   `erp_book(payable).will_book_gross == printed_gross` (within 0.01) AND the
   grounding ledger is fully covered. Otherwise: re-examine once → or decline
   with the failing gate named.
7. **Numbers out are dot-decimal; dates out are ISO.** No locale parsing by the
   ERP. `normalize.py` owns this.

## Structure

```
autodraft/                 # the system (package)
  geom.py                  # Box/Word/Line + clustering (no deps)
  render.py                # PDF → PageSource (text-layer or PNG)
  ocr.py                   # RapidOCR → Word
  structure.py             # regions, columns, tables (ratio-based only)
  normalize.py             # currency/locale/date parsing → dot-decimal/ISO
  fields.py                # header fields + line-item cell roles
  classify.py              # INVOICE / CREDIT_MEMO / NOT_A_PAYABLE
  resolve.py               # master matching (rapidfuzz + corroboration)
  oracle.py                # sealed erp_book wrapper + refusal + grounding
  pipeline.py              # orchestrates one file
  backends/                # Ollama consult + optional premium vision
  __main__.py              # CLI: python -m autodraft <in> <out>
output/                    # generated *.json (the brief's artifacts)
docs/
  ARCHITECTURE.md          # design (read this first)
  ROADMAP.md               # phased plan with gates
DESIGN.md                  # submission doc (written last)
.work/                     # cached page renders / transcripts (gitignored)
```

## Conventions

- **Python 3.10+ stdlib where possible.** Two external wheels:
  `rapidocr_onnxruntime`, `rapidfuzz`. Add more only when a gate demands it.
- **`import pymupdf`**, not the deprecated `fitz`.
- **Coordinates are never absolute.** Geometry is ratio/relative; OCR scale
  varies between producers and pages.
- **Dependency injection for concurrency:** RapidOCR engine is process-global
  and reused; a `ThreadPool` runs *page* jobs, never within-page.
- **Log, don't guess.** Every refused gate logs the exact contradiction.

## Verification

- `python -m autodraft documents output` — full run, idempotent.
- Gates in `docs/ROADMAP.md` — each phase ends by re-running the full corpus.
- When a util gains tests, they live next to it as `autodraft/tests/`.