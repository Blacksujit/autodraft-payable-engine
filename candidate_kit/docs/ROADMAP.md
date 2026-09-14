# Roadmap

Phased plan with hard verification gates. A gate fails ⇒ solve the underlying
cause (which is the point) before moving on — never paper over to keep the
schedule. Each phase ends by re-running the *entire* corpus so regressions are
caught the day they are introduced.

Working principle from the brief, taken literally:

> "The distance between open and held-back performance is the headline metric."
> Every feature must be built so it works on a document we have not seen. No
> per-file special cases, ever. They are forbidden even when they are tempting.

Legend: **D** = deterministic core · **L** = local LLM consult · **G** = gate

---

## Phase 0 — Toolchain & corpus baseline (done, re-checked at every step)

- [x] Verify Python 3.14.6, CPU-only, 8.2 GB RAM, 12 cores.
- [x] `pip install rapidocr_onnxruntime rapidfuzz` (the two new wheels; the
      rest of the stack is preinstalled).
- [x] Confirm `pymupdf` (use `import pymupdf`, not `fitz`), `pdfplumber`,
      Ollama (`moondream`, `llava:7b`, `llama3.2`, `nomic-embed-text`).
- [x] Corpus survey: 42 PDFs / 111 pages; 6 text-layer (English); 36 image scans.
- [x] Probe OCR quality for both scanned (INV-01) and low-fi (HLD-01, DU-02)
      pages; RapidOCR returns `[quad, text, conf]`, ~6–10 s/page, coordinates
      ~3× page scale ⇒ downstream geometry is 100% ratio-based.
- [x] Read the sealed oracle (`erp.py`) and reverse its exact arithmetic.
- [x] Survey all masters (14 suppliers incl. PT; 34 taxes; 10 payment terms with
      aliases; org tree; 2 POs).

**G0** — Renders + OCR of all 111 pages complete on the unmodified corpus;
elapsed time recorded. Artifacts: page transcripts cache under `.work/`.

---

## Phase 1 — Reconstruction core (D)

Geometry → structure → normalize → fields. No LLM anywhere in this phase; the
deterministic core must already carry *most* of the value.

1. `geom.py` — `Box`, `Word`, `Line`, `cluster_lines`, `group_lines_by_bands`.
2. `render.py` — `iter_pages`: text-layer words via pdfplumber, else PNG at
   200 DPI for OCR (cached).
3. `ocr.py` — lazy `RapidOCR` engine → `Word` list.
4. `structure.py` — line/row clustering, column-band detection, table-region
   carving, header/footer/table tagging.
5. `normalize.py` — currency detection, per-number locale parse, dot-decimal
   emission, date parsing with ambiguity rules.
6. `fields.py` — multilingual header field extraction; line-item cell → role
   mapping (description / qty / unit / total / tax) by ≥2 agreeing signals.

**G1** — On the 7 text-layer docs, extraction reaches the known-good structure
(identical to what `sample_autodraft.json` demonstrates for the same file family):
correct invoice#, dates, supplier, unit/qty/total, taxes with *placement*.

---

## Phase 2 — Oracle harness + assembly (D)

7. `oracle.py` — wraps sealed `erp_book`; compare-to-printed-gross; refusal
   rules; grounding ledger; report format.
8. `classify.py` — doc-type triage (INVOICE / CREDIT_MEMO / NOT_A_PAYABLE)
   from structure signals, multilingual credit cues, absent-total detection.
9. `resolve.py` — master matching scored (rapidfuzz + corroboration).

**G2** — First booking: `erp_book(payable) == printed gross` on ≥ half the corpus,
auto-detected types and codes resolve honestly (code or `""`).

---

## Phase 3 — Multi-payable + credit + declined semantics (D)

10. Multi-payable files (the `DU-*` customs consolidated invoice) → one payable
    per invoice; per-page totals vs the single true payable total triaged.
11. CREDIT_MEMO path end-to-end (same schema, positive magnitudes, ERP sign).
12. NOT_A_PAYABLE path: quotes/statements/supporting pages → `declined[]` with
    precise reasons.

**G3** — No document is force-booked; every output row is either oracle-matching
or declined *with the failing gate named*.

---

## Phase 4 — Local-LLM consult layer (L)

13. Ollama backend protocol + `llama3.2` text consult for doc-type and
    field-binding on low-confidence pages only.
14. Vision escalation: `moondream` → `llava:7b` for pathological scans, used
    as *evidence re-phraser* only (core re-extracts; LLM numbers never enter
    the record).

**G4** — Pages that previously failed G3 now either book (verified) or decline
*faster* with a sharper reason; total added correctness measured, not assumed.

---

## Phase 5 — Generalisation & held-back posture (D+L)

15. Adversarial sweep: hand-build 10 synthetic "never-seen" docs (new languages,
    unusual column orders, mixed separators, multi-invoice, credit cues,
    ambiguous dates, absent PO, unknown supplier) and require the *same*
    machinery — no special cases — to handle each honestly.
16. The one *provably unsolvable* doc (brief's promise): confirm no page could
    support the answer, and document in `DESIGN.md` the refusal.

**G5** — Synthetic-set distance ≤ small; refusal reasons are diagnostic.

---

## Phase 6 — Release packaging + DESIGN.md

17. `output/*.json` for all 42 files, re-runnable in one command.
18. `DESIGN.md` (≤3 pages) answering the brief's three questions honestly.
19. README (system run instructions) + final verification sweep.

**G6** — `python -m autodraft documents output` is reproducible from a clean
state; graduated format: passing per-doc report in hand.

---

## Tracked risks (revisit at each gate)

- **Mixed number locales within one doc** (seen already) — handled in
  `normalize.py` per-number; watch for the inverse (`1,234.56`).
- **Multi-payable files** — the ORCAd multi-`payables[]` contract is exercised
  first on `DU-*`.
- **Vision-model latency** on 12-core CPU — moondream is ~1.7 GB; llava 7B
  slow; escalation is bounded to pages that *need* it.
- **Transformers/torchvision drift** — torchvision is broken (0.2.0); we do
  **not** depend on transformers-vision at all. Text-only transformers unused
  too: Ollama covers the LLM layer with zero pip friction.
- **`winsdk` unavailable on py3.14** — Windows built-in OCR is not used;
  RapidOCR is the single OCR path (simpler, and identical behaviour on the
  held-back set).

---

## Launch-day status (measured, not assumed)

| Gate | Intent | Status verified today |
|------|--------|----------------------|
| G0 | all-page renders + OCR | Done; page cache under `.work/` (gitignored) |
| G1 | text-layer extraction known-good | Done for the English families that book; line-item carving still misses foreign/localized header tables (see G2) |
| G2 | `erp_book(payable) == printed gross` on ≥ half the corpus | **38 % honest current value** — 16 of 42 book; every other file declines with a named gate; 0 errors, 0 invented numbers. 26 declines share one root cause (line-item reconstruction), which the held-back set isolates and Phase 4 points at |
| G3 | no force-booking | Holds: every row is oracle-matching (`payables[]`) or `declined[]` with the failing gate named |
| G4 | local-LLM seam, low-confidence only, fail-open | Shipped & proven: `autodraft/backends/` (Ollama + consult), `AUTODRAFT_CONSULT=1` re-phrases decline evidence as `[consult: …]`; default run stays byte-deterministic |
| G5 | synthetic “never-seen” set, same machinery | Done: `heldback/build_synthetic.py` → 11 docs, all run through identical machinery; report at `heldback/REPORT.md`. Distances measured: 8/8 bookable GAP (line-item root cause), 3/3 refusables HIT incl. the provably-unsolvable doc. The sweep already paid one real, general fix (customs cue `\biva\b`/`\bimpuesto\b` removal → INV-34 newly books, 15→16, nothing lost) |
| G6 | one-command reproducible from clean state | Holds: `python -m autodraft documents output`; `.work/` cache is content-hashed so a second run is fast and byte-identical (consult off); `output/` and `heldback/output/` are gitignored and regenerable |

Launch-day verification commands:

```
python -m autodraft documents output                 # open corpus
python heldback/build_synthetic.py                    # regenerate held-back PDFs
python -m autodraft heldback/documents heldback/output
$env:AUTODRAFT_CONSULT=1; python -m autodraft heldback/documents heldback/output   # Phase 4 seam (optional)
```

Unverified-honestly: G2's ≥ half target is **not** met; the 38 % number is the
measured distance the next iteration must shrink, and the held-back set is the
fixed yardstick for that.