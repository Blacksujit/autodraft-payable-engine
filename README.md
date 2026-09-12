# Autodraft Payable Engine

Autodraft is a grounded, deterministic document-understanding pipeline for converting supplier PDFs into ERP-bookable payable records. It is engineered for real financial workflows, where correctness is defined not by superficial extraction quality but by whether the generated payable matches the ERP's own recomputation logic and whether non-payables are rejected honestly.

The system exists to solve a practical and difficult problem: reading supplier invoice PDFs, reconstructing their true structure, and emitting payables only when the page supports them under strict validation.

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

Supplier invoices are not just text fragments. They encode financial meaning in layout, row structure, tax placement, totals, dates, addresses, and item hierarchy.

The challenge is not merely extracting words; it is reconstructing the obligations hidden in the document and validating them under the ERP contract.

The project therefore builds on three non-negotiable ideas:

1. Grounded extraction
   No value is emitted unless it is either visible on the page or derived by a mathematically explicit, document-supported transformation.

2. Structural fidelity
   A total line may appear correct while the tax placement is wrong. ERP validity depends on structure, not just arithmetic.

3. Honest decline
   If a document is not a payable, or if the evidence is insufficient, it should be placed in `declined[]` with a cause, not forced into `payables[]`.

---

## Quick Start

```bash
# One command: input directory → output directory
python -m autodraft documents output
```

This command:

- reads every `documents/*.pdf`
- renders or OCRs pages as required
- extracts structured invoice fields and line items
- classifies each document as invoice, credit memo, or non-payable
- resolves available master data
- validates against a sealed ERP oracle
- writes one JSON file per input PDF to `output/`

The output shape is:

```json
{
  "file": "INV-01.pdf",
  "payables": [],
  "declined": []
}
```

A payable record contains invoice and payment metadata, line items, taxes, and ERP-ready fields. A declined document contains the reason the document is not a payable.

---

## Requirements

- Python 3.10+
- `rapidocr_onnxruntime`, `rapidfuzz`, `pymupdf`
- project-root `erp.py` sealed ERP oracle

```bash
pip install rapidocr_onnxruntime rapidfuzz pymupdf
```

---

## Architecture

```text
documents/*.pdf
      │
      ▼
┌───────────────────────────────────────────────┐
│  Render + OCR acquisition                     │
│  text layer if available; rendered pages +    │
│  OCR otherwise                                │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Geometry reconstruction                     │
│  words → lines → rows → columns → tables     │
│  header/footer and table-region separation    │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Normalization + field extraction             │
│  dates, currencies, numbers, line items,      │
│  taxes, totals                                │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Document classification                     │
│  INVOICE / CREDIT_MEMO / NOT_A_PAYABLE       │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Master resolution                           │
│  suppliers, buyer orgs, tax, payment terms, │
│  PO references                                │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Oracle gate                                 │
│  compare ERP gross to printed gross          │
│  enforce tax-placement validity              │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  Output JSON                                 │
│  payables[] / declined[]                     │
└───────────────────────────────────────────────┘
```

This is not a naive extraction pipeline. It is a layered, validation-driven architecture:

- source acquisition is separated from document understanding
- geometry is reconstructed before field binding
- semantic classification occurs before final emission
- ERP validation is the final gate, not an afterthought

---

## Design principles in practice

### 1. Deterministic engineering core

The core processing is designed to be deterministic and explainable. It relies on:

- page geometry
- page-relative coordinates and ratios
- label recognition and field association
- explicit normalization rules

This keeps the pipeline robust across different PDFs and minimizes dependence on brittle per-file logic.

### 2. Grounding ledger

Every emitted field is traceable to document evidence. The system keeps a provenance ledger that tracks where a value came from, which page it came from, and how it was derived.

This is crucial in a finance workflow: an answer is more valuable when it can be explained and audited.

### 3. Conservative refusal behavior

The project is intentionally willing to say "no".

If a document is ambiguous, unsupported, or structurally inconsistent, the correct action is not to fabricate a payable. The correct action is to decline it with a specific reason and let the downstream workflow decide how to handle it.

---

## Key technical behavior

### Render and OCR flow

The pipeline supports both embedded text and scanned documents:

- if a PDF contains extractable text, use it
- if not, render pages and run OCR
- all downstream stages use a common word-and-box representation

This makes the system robust across mixed corpora without introducing source-specific logic downstream.

### Locale-aware numeric normalization

Invoice numbers vary in formatting and locale. The project handles mixed numeric patterns such as:

- `1.234,56`
- `1,234.56`
- `1234.56`
- `73,00`
- `438.00`

These are normalized into a canonical decimal form before being used in a payable record.

### Tax correctness and placement

The project does not treat tax as a purely arithmetic afterthought. It recognizes that different documents place taxes at different structural points:

- line-level tax
- header tax
- total-only tax
- credit memo tax migration

The ERP gate validates the final placement. A field may numerically look correct but still fail if the structure is inconsistent with the document.

---

## Oracle gate

The ERP recompute is a sealed black box (`erp.erp_book`). A payable emits only when:

```python
abs(erp_book(payable).will_book_gross - printed_gross) <= 0.01
```

This is the critical correctness rule. It ensures the output record is not merely plausible to a reader; it is valid from the perspective of the actual booking engine.

The oracle tries canonical tax placements in priority order:

1. `keep` — extracted placement as-is
2. `no_header_mods` — remove ambiguous header charges
3. `solo_total` / `solo_gross` — single-line fallback
4. `header_taxes` — credit memo line taxes moved to header
5. `header_amount` / `header_rate` / `line_rate` — canonical tax migrations

The first placement that passes is accepted. If no placement passes, the document is declined with a named gate failure rather than being forced through.

---

## Classification and output semantics

Each input is classified as one of the following:

- `INVOICE`
- `CREDIT_MEMO`
- `NOT_A_PAYABLE`

A credit memo remains a payable record, but with credit-style semantics. A non-payable doc goes to `declined[]` with reason metadata instead of being emitted as a payable.

Examples of non-payables:

- quotes
- delivery notes
- customs forms
- statements
- utility reimbursement documents
- boilerplate and supporting attachments

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
    "line_items": [
      { "description": "Projektmanagement", "quantity": "4", "unit_price": "73.00", "total": "292.00" }
    ],
    "taxes": [{ "tax_type": "VAT", "tax_name": "Reverse Charge", "tax_rate": "0", "tax_amount": "0" }]
  }],
  "declined": []
}
```

---

## Refusal rules

The project is deliberately engineered to reject wrong answers rather than guess them.

### 1. No invented values
Any field value must be grounded in the document or derived from data explicitly present.

### 2. No invented codes
Master data matching is scored and corroborated. Weak or ambiguous matches remain empty rather than guessed.

### 3. No creative corrections
The system does not silently rewrite invoice structure to make numbers fit. If the document does not support the correction, it declines.

This is a strong design choice and one of the major differentiators of the project.

---

## Operating model

The intended workflow is:

1. place PDFs in `documents/`
2. run `python -m autodraft documents output`
3. inspect resulting `output/*.json`
4. review any documents in `declined[]` for reasons and failed gates
5. keep the pipeline conservative and traceable

This is a real engineering pattern: the system emphasizes correctness, auditability, and operational honesty over volume of extracted output.

---

## Repository references

- `ARCHITECTURE.md` — detailed engineering and design rationale
- `ROADMAP.md` — phased verification and release gates
- `AUTODRAFT_SCHEMA.md` — payable JSON schema contract
- `DESIGN.md` — design brief and held-back-document reasoning

---

## Summary

Autodraft is not a generic PDF parser. It is a grounded financial-document extraction engine designed to convert supplier invoices into valid ERP-bookable payables while refusing unsupported or non-payable documents.

Its core value is the combination of:

- deterministic page reconstruction
- source-agnostic extraction
- locale-aware normalization
- tax-structure correctness
- master-data resolution
- strict ERP oracle validation
- evidence-based refusal behavior

The project is engineered to behave like a professional payable automation system, not a demo that overfits to a small happy path.
