# Autodraft — Supplier Invoice to ERP Payable

Turns supplier PDF invoices into structured autodraft JSON records that an ERP can book.

## Quick Start

```bash
# One command: input directory → output directory
python -m autodraft documents output
```

- Reads every `documents/*.pdf`
- Writes `output/<stem>.json` per file (one JSON per PDF)
- Each JSON: `{ "file": "...", "payables": [...], "declined": [...] }`
- Payables conform to `AUTODRAFT_SCHEMA.md`; declined items explain why not a payable

## Requirements

- Python 3.10+
- `rapidocr_onnxruntime`, `rapidfuzz`, `pymupdf`
- `erp.py` (sealed ERP oracle) in project root

```bash
pip install rapidocr_onnxruntime rapidfuzz pymupdf
```

## Architecture

```
documents/*.pdf
      │
      ▼
┌─────────────────────────────────────────┐
│  Pipeline (autodraft/pipeline.py)       │
│  1. Render PDF → PNG (pymupdf, 2×)     │
│  2. OCR → words (RapidOCR ONNX)        │
│  3. Layout → columns/tables (ratio)    │
│  4. Extract → fields, lines, taxes     │
│  5. Classify → INVOICE / CREDIT / NO   │
│  6. Resolve → master codes (suppliers,  │
│     terms, taxes, buyer, POs)          │
│  7. Oracle gate → ERP-gated emission   │
└─────────────────────────────────────────┘
      │
      ▼
output/*.json  (one per PDF)
```

## Oracle Gate

The ERP recompute is a sealed black box (`erp.erp_book`). A payable emits only when:

```
abs(erp_book(payable).will_book_gross - printed_gross) ≤ 0.01
```

The oracle tries canonical tax placements in priority order:
1. `keep` — extracted placement as-is
2. `no_header_mods` — drop ambiguous header charges
3. `solo_total` / `solo_gross` — single-line fallback
4. `header_taxes` — credit memo line taxes → header
5. `header_amount` / `header_rate` / `line_rate` — canonical tax migrations

First passing placement wins; else honest decline with named gate.

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
    "buyer": { "company_code": "BOLTGROUP", ... },
    "payment_term_id": "Net_10",
    "gross_total": "438.00",
    "line_items": [
      { "description": "Projektmanagement", "quantity": "4", "unit_price": "73.00", "total": "292.00", ... }
    ],
    "taxes": [{ "tax_type": "VAT", "tax_name": "Reverse Charge", "tax_rate": "0", "tax_amount": "0" }]
  }],
  "declined": []
}
```

## Non-Payables

Documents with no payable obligation (quotes, delivery notes, customs forms, utility reimbursements) appear in `declined[]` with a reason — never in `payables[]`.

## Design

See `DESIGN.md` for the three-question design document.