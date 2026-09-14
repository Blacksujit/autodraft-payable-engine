# Autodraft Payable Engine

Autodraft is a grounded, deterministic document-understanding pipeline for converting supplier PDFs into ERP-bookable payable records. It is engineered for real financial workflows, where correctness is defined not by superficial extraction quality but by whether the generated payable matches the ERP's own recomputation logic and whether non-payables are rejected honestly.

The system exists to solve a practical and difficult problem: reading supplier invoice PDFs, reconstructing their true structure, and emitting payables only when the page supports them under strict validation.

---

## Table of Contents

- [Mission](#mission)
- [Why this project matters](#why-this-project-matters)
- [Quick Start](#quick-start)
- [Live demo / review mode](#live-demo--review-mode)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Key technical behavior](#key-technical-behavior)
- [Oracle gate](#oracle-gate)
- [Classification and output semantics](#classification-and-output-semantics)
- [Output Example](#output-example)
- [Refusal rules](#refusal-rules)
- [Operating model](#operating-model)
- [References](#references)
- [Summary](#summary)

---

## Mission

The project turns supplier documents into machine-structured payable records that can be booked by an ERP, while explicitly rejecting documents that are not payables.

It is built around the principle that a payable is valid only when:

- the extracted values are grounded in the document
- tax structure and placement remain faithful to the original invoice
- the recomputed ERP gross matches the printed gross within tolerance
- the document is classified correctly as invoice, credit memo, or non-payable

This makes the project fundamentally different from simple OCR or PDF scraping pipelines. It is an engineering system with explicit verification gates and a refusal policy.

---

## Why this project matters

Supplier invoices are financial records, not generic PDFs. The system extracts only records that can be validated against the ERP's own rules.

It focuses on three things:

1. Grounded extraction — every value must be supported by the document.
2. Structural correctness — tax and totals must match the invoice layout, not just the numbers.
3. Honest refusal — if the document is not a payable, it is declined instead of guessed.

---

## Quick Start

```bash
# Input directory -> output directory
python -m autodraft documents output
```

The pipeline:

- reads PDFs from `documents/`
- extracts structured fields from text or rendered pages
- classifies each file as `INVOICE`, `CREDIT_MEMO`, or `NOT_A_PAYABLE`
- resolves master data when available
- validates the result using the ERP oracle
- writes one JSON result per input document in `output/`

Example output:

```json
{
  "file": "INV-01.pdf",
  "payables": [],
  "declined": []
}
```

---

## Live demo / review mode

The batch path is great for production, but for verifying the pipeline there is
an interactive review CLI. It runs the **same** pipeline and the **same** ERP
gate on every document — including the held-back corpus the machine has never
been tuned against — so an evaluator can reproduce the honesty claim in real
time.

```bash
python -m autodraft demo                # interactive menu over open + held-back corpus
python -m autodraft demo --doc INV-01   # one-document report: fields, taxes, ERP gate, audit
python -m autodraft demo --all          # verdict table for every PDF (PASS / DECLINED / ERROR)
python -m autodraft demo --json out     # also write the emitted JSON records
```

A per-document report shows the emitted payable (totals, taxes, line items),
which tax-placement variant was applied, the ERP recompute against the printed
gross (`GATE PASS` / `GATE FAIL`), and a fidelity audit confirming every
emitted number is grounded on the page. Held-back documents are tagged `[H]`
and their expected ground-truth gross is shown when known, so a mismatch is
never hidden.

---

## Architecture

```text
documents/*.pdf
      │
      ▼
┌───────────────────────────────────────────────┐
│  Render / OCR acquisition                     │
│  text layer if available; otherwise render    │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Geometry reconstruction                      │
│  words → lines → rows → columns               │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Normalization + field extraction             │
│  dates, numbers, taxes, totals, line items    │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Classification                               │
│  INVOICE / CREDIT_MEMO / NOT_A_PAYABLE        │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  ERP validation gate                          │
│  recompute gross and tax placement            │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Output JSON                                  │
│  payables[] / declined[]                      │
└───────────────────────────────────────────────┘
```

The design is simple: understand the document, classify it, validate it, then emit only what the ERP can safely book.

---

## Requirements

- Python 3.10+
- `rapidocr_onnxruntime`, `rapidfuzz`, `pymupdf`
- project-root `erp.py` sealed ERP oracle

```bash
pip install rapidocr_onnxruntime rapidfuzz pymupdf
```

---

## Key technical behavior

- Render OCR if the PDF does not have usable text.
- Normalize mixed number formats like `1.234,56`, `1,234.56`, and `73,00`.
- Preserve document structure when matching taxes and totals.
- Reject unsupported or ambiguous files rather than forcing a result.

---

## Oracle gate

The ERP recomputation is the final gate. A payable is emitted only if:

```python
abs(erp_book(payable).will_book_gross - printed_gross) <= 0.01
```

If the document does not pass this check, it is declined with a clear reason instead of being silently altered.

---

## Classification and output semantics

Each input is classified as one of:

- `INVOICE`
- `CREDIT_MEMO`
- `NOT_A_PAYABLE`

Examples of non-payables:

- quotes
- delivery notes
- customs forms
- statements
- utility reimbursement documents
- boilerplate / supporting attachments

A credit memo remains a payable record with credit semantics. A non-payable goes into `declined[]` rather than `payables[]`.

---

## Output Example

```json
{
  "file": "INV-01.pdf",
  "payables": [{
    "invoice_number": "852566",
    "invoice_date": "2025-01-15",
    "due_date": "2025-01-25",
    "invoice_type": "INVOICE",
    "currency": "EUR",
    "supplier": {
      "name": "NorthwindOperationsOU",
      "supplier_id": "",
      "address": "...",
      "vat_id": "EE398766194"
    },
    "buyer": { "company_code": "BOLTGROUP" },
    "payment_term_id": "Net_10",
    "gross_total": "438.00",
    "line_items": [{
      "description": "Projektmanagement",
      "quantity": "4",
      "unit_price": "73.00",
      "total": "292.00"
    }],
    "taxes": [{
      "tax_type": "VAT",
      "tax_name": "Reverse Charge",
      "tax_rate": "0",
      "tax_amount": "0"
    }]
  }],
  "declined": []
}
```

---

## Refusal rules

The system is intentionally conservative.

- No invented values
- No invented codes
- No silent structural corrections
- If evidence is weak or the document is not a payable, decline it

This is a core requirement for financial automation, where wrong output is more dangerous than no output.

---

## Operating model

1. Place PDFs in `documents/`
2. Run `python -m autodraft documents output`
3. Review generated `output/*.json`
4. Check any entries in `declined[]`
5. Keep the pipeline conservative and auditable

For ad-hoc verification of a single document or the full held-back corpus, use
`python -m autodraft demo` (see [Live demo / review mode](#live-demo--review-mode)).

---

## References

Repository references:

- `ARCHITECTURE.md` — pipeline and engineering design
- `ROADMAP.md` — verification and release gates
- `AUTODRAFT_SCHEMA.md` — payable output schema
- `DESIGN.md` — design rationale and held-back-document reasoning
- `erp.py` — sealed ERP oracle used for validation

Related financial/document automation context:

- invoice extraction and table reconstruction from supplier PDFs
- ERP gross validation and tax placement checks
- document classification for invoice, credit memo, and non-payable detection

---

## Summary

Autodraft is a practical payable-validation pipeline for supplier documents. It does not try to extract every PDF into a plausible result. It extracts only documents that can be grounded, structured, and validated under ERP rules.

The purpose is straightforward: produce valid payable records or explicit declines, not invented ones.
