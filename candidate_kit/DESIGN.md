# Autodraft System Design

## Overview

The Autodraft system processes supplier PDF invoices into structured autodraft JSON records that a downstream ERP can book. It uses a pipeline of PDF rendering → OCR → layout analysis → field extraction → master-data resolution → ERP-gated emission.

---

## 1. What did you eventually understand about these documents that you did not understand on day one?

**The gross is not the total.** On day one I treated "gross" as just the biggest number on the page. The real insight: every document has a *printed gross word* (the amount the supplier says is owed) and the ERP recomputes from the *components* we emit (line totals, header taxes, charges). A payable passes only when the ERP's recompute from our emitted components lands within 0.01 of that printed gross. The gross is a *constraint*, not a target.

**Placement is structural, not cosmetic.** A tax the document puts at the header (one rate for the whole invoice) must stay at the header in the autodraft; a tax printed on a line belongs on that line. Migrating a header tax to lines (or vice versa) changes the ERP's tax base and breaks the gate — even when the gross still foots. The variant system (keep / header-amount / header-rate / line-rate / header-taxes / solo-*) is not a fallback ladder; it is a disciplined search for the *one* placement that matches the document's own structure.

**The master data is intentionally sparse.** The sample masters (14 suppliers, 10 payment terms, 34 taxes, 2 POs) cover only a fraction of the documents. Empty codes (`""`) are the correct honest answer when no match exists — not a failure. The system resolves against masters where possible and leaves blanks otherwise.

---

## 2. When your system meets a document unlike any it has seen, what does it actually do — and why does that generalise instead of guessing?

When a new document arrives, the pipeline runs the same fixed stages:

1. **Render & OCR** — 2× PNG → RapidOCR words (cached in `.work/`)
2. **Layout** — geometric clustering (ratio-based, no absolute coords) → columns/tables
3. **Extract** — regex/label-based totals, line-item decomposition (qty/unit/total), tax rows, dates, currency
4. **Classify** — INVOICE / CREDIT_MEMO / NOT_A_PAYABLE (regex on page text, multilingual)
5. **Resolve** — fuzzy match supplier/buyer/terms/taxes/PO against masters (score ≥ 0.45)
6. **Oracle gate** — try canonical tax placements in priority order; first that makes `erp_book(payable).will_book_gross ≈ printed_gross` (within 0.01) wins; emit that payable with `_placement` recorded. If none passes, decline with named gate.

**Why this generalises:** No per-document branches, no invented numbers, no special-casing. The variant ladder covers the *canonical* ways taxes appear on invoices (header vs line, amount vs rate). A document outside the open set either matches one of those patterns (passes) or honestly declines (no placement foots). The held-back set tests whether the same canonical patterns cover the unseen cases — not whether I memorised the open set.

**Measured (open corpus, final): 16 of 42 ≈ 38 % book; every other row declines with a named reason; zero errors, zero invented numbers.** The held-back set (11 never-seen docs, see `heldback/REPORT.md`) added one real improvement before it ever ran: auditing the generator exposed that `iva` and `impuesto` were sitting in the **customs** cue regex — but those are ordinary VAT words on Italian/Spanish invoices. Removing them re-classified two held-back invoices to INVOICE and, on the open set, **newly booked INV-34** (15 → 16, no bookings lost). That is generalisation in action: a fix driven by adversarial cases, validated on the original corpus.

The honest gap the held-back set still demonstrates: line-item carving does not (yet) engage for clean-but-foreign text-layer tables, so 8/8 genuinely-reconcilable synthetic invoices decline as `gross_mismatch` while all four deliberately-refusable cases (quote, customs, and one provably-unsolvable page) decline correctly. That gap is the same root cause as the open set's 26 declines — and it is the documented job of Phase 4 (below) to point at it.

Audit coverage is now measured per-page: every PDF page renders and is OCR'd through the same evidence path the emitter used, so a fully-scanned doc like INV-03 is grounded against its raster, not just its text layer. The integration suite's audit gate (ERP recompute + value grounding) is green across all 42 docs, and the credit-note capability DU-10 genuinely needs is registered as a known `xfail` gap instead of being silently asserted.

---

## 3. Was there a document you concluded could not be solved the way the others were? If so, which, and how did you know?

**DU-03 (customs declaration).** It is a consolidated customs statement between third parties (Blueharbor Logistics → various). The "buyer" field resolves to a non-Bolt entity that cannot be matched against `chart_of_books`. The document asserts no payable obligation to the tenant. Classifying it as `not_a_payable` with reason `customs_statement` is the only honest outcome — no variant of tax placement can manufacture a valid tenant payable from a third-party customs form. Recognising this and refusing to fake a payable is worth more than any code that pretends otherwise.

**A second, provably-unsolvable case (synthetic, `HELD-UNSOLVABLE`).** A single page with a routing memo, a phone number, a barcode reference and zero monetary amounts. No page can support a payable: there is no gross to check, no line to emit, no supplier that owes the tenant money. The system declines with a reason and emits **no payable and no fabricated number** — the same discipline, not a special case.

---

## 4. Local-LLM evidence seam (optional, off by default)

`autodraft/backends/` is a fail-open, narrative-only layer over a local Ollama.
It exists for one reason: on a document the deterministic core will not book, a
decline reason can be re-phrased into actionable evidence ("the printed gross is
on the last footer line") without a human opening the PDF.

* The LLM is consulted **only** on documents already declined by the deterministic
  core. It never fills a number the core did not see, never flips a decline to a
  book, and its words are appended as `[consult: …]` to the reason — marked as
  non-authoritative.
* Every call is bounded by a timeout and **fails open**: if Ollama is down, the
  reply is unusable, or `AUTODRAFT_CONSULT` is unset (default), the pipeline
  behaves exactly as without the layer — byte-for-byte deterministic from a
  clean state.
* Vision models (`moondream`) are wired for pathological scans but only ever
  describe the total region; the numbers they mention are illustrative of the
  evidence, never booked.

---

## Key Implementation Details

| Stage | Module | Key Invariant |
|-------|--------|---------------|
| OCR | `ocr.py` | RapidOCR ONNX, cached words per page |
| Geometry | `geom.py` | Ratio-based clustering, no absolute coords |
| Layout | `structure.py` | Column detection, table reconstruction |
| Extraction | `fields.py` | Label-based totals, qty/unit/total decomposition |
| Classification | `classify.py` | Multilingual regex (INVOICE/CREDIT/NOT_A_PAYABLE) |
| Resolution | `resolve.py` | Scored fuzzy match (≥0.45) against masters |
| Oracle | `oracle.py` | 7 placement variants, ERP gate, honest decline |
| Pipeline | `pipeline.py` | Multi-page merge, dedupe, per-file JSON |

**CLI:** `python -m autodraft documents output` — one command over `documents/` → `output/`

**ERP Contract:** `erp.erp_book(payable) → {"will_book_gross": float, "currency": str}` — sealed, never patched.