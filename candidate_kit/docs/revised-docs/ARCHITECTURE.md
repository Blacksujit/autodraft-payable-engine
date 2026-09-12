# The Bookable Payable — Architecture & Design Document

## 1. Problem Analysis: What This Is Really Asking

### The Surface Problem
Convert 42 supplier PDFs into structured JSON autodrafts that an ERP can book.

### The Deep Problem (The Shift)
The README deliberately hints at "a shift in how you picture what one of these documents actually is."

Here is the shift: **A document is not a record. A document is evidence. The autodraft is a faithful reconstruction of the financial intent behind that evidence — not a transcription of its pixels.**

The three reasons a faithful copy can still fail to book:
1. **Tax placement**: A line-level tax transcribed to the header changes the base the ERP uses
2. **Unit price confusion**: Gross price (tax-included) vs net price (tax-exclusive) — the document may show gross, the ERP needs net
3. **Compound tax bases**: Some taxes apply to subtotals, others to tax-on-tax cascades — structure determines base

The three rules in the brief are the system's constraints. But they are also clues:
- Rule 1 (groundedness) → never invent balance-the-books numbers → the discrepancy between ERP result and document total is information about the document's structure
- Rule 2 (real codes only) → match or leave blank → design for honest blanks
- Rule 3 (correction must survive being wrong) → any "fix" needs independent evidence → don't auto-correct unless you can prove it

### The Documents
- **42 PDFs total**: 28 INV-*, 5 HLD-*, 9 DU-*
- **37 image-based PDFs** (scanned/rendered as images), **5 text-extractable PDFs**
- **Multi-lingual**: German, English, Portuguese, Estonian, Malay, Ghanaian, South African contexts inferred from suppliers
- **Multi-currency**: EUR, GBP, GHS, MYR, ZAR, KES, others
- **Document types**: Invoices, credit memos, delivery notes, statements, POs — must classify each

### The Naming Hints
- **INV-***: Likely invoices, but not guaranteed — may be credit memos or non-payables
- **HLD-***: "Held" documents? Possibly statements, delivery notes, or ambiguous docs
- **DU-***: "DU" could be German "Du" or abbreviated doc types — delivery receipts, duty documents, multi-page accounts

---

## 2. System Architecture

### Pipeline Overview

```
PDF
 │
 ▼
[Step 1: Extraction]
 │  Text PDFs → pypdf text extraction
 │  Image PDFs → Vision LLM (moondream/ollama) → raw text
 │
 ▼
[Step 2: Classification]
 │  Invoice / Credit Memo / Delivery Note / PO / Statement / Other
 │  → Only INVOICE and CREDIT_MEMO produce payables
 │
 ▼
[Step 3: Field Extraction]
 │  LLM extracts: invoice_number, dates, supplier, buyer, totals,
 │  line items, taxes, payment terms, PO references
 │  → Faithfully from document — no inference of missing numbers
 │
 ▼
[Step 4: Master-Data Resolution]
 │  supplier_id: fuzzy match on name/VAT/address
 │  buyer codes: match entity name → BU code
 │  tax codes: match country+rate+type
 │  payment_term_id: match text or date math
 │  po_id: exact match only
 │
 ▼
[Step 5: Tax Placement Determination]
 │  Critical: determine WHERE each tax sits (line vs header)
 │  Parse document structure — each tax assigned to the level it appears on
 │
 ▼
[Step 6: ERP Validation]
 │  erp_book(payable) → will_book_gross
 │  Compare to document's gross_total
 │  On mismatch: diagnose (unit price gross vs net? wrong tax level?)
 │  Do NOT invent numbers to reconcile — log discrepancy
 │
 ▼
[Step 7: Output]
 │  output/X.json for each input X.pdf
 │  payables[] + declined[]
```

### The LLM's Role
The LLM is a **structured extractor**, not a calculator. It reads the document and fills fields. It does NOT:
- Compute totals
- Invent missing values
- Choose tax placement for convenience

The LLM IS asked to:
- Transcribe text faithfully (including locale-formatted numbers → will be converted)
- Identify document type
- Identify where on the page each tax appears (line-level vs header)
- Extract supplier/buyer entity names for master matching

### Technology Choices
| Component | Tool | Reason |
|---|---|---|
| Text extraction | pypdf | Already available, fast for text PDFs |
| Image OCR/Vision | moondream via ollama (local) | Available offline, 1.7GB, vision capable |
| LLM reasoning | qwen2.5:1.5b via ollama (local) | Available, handles structured JSON output |
| ERP validation | erp.py (stdlib) | Fixed contract, import directly |
| Master matching | Pure Python fuzzy match | No deps needed |
| Output | json stdlib | Simple, reliable |

---

## 3. The Key Insight: Tax Placement

The ERP formula is:
```
gross = sum(line_bases) - header_discount + sum(line_taxes) + sum(header_taxes) + other_charges

where:
  line_base  = round2(qty × unit_price × (1 - disc_pct/100))
  line_tax   = round2(line_base × tax_rate/100)   [if no explicit amount]
  header_tax = round2(net_base × tax_rate/100)     [if no explicit amount]
  net_base   = sum(line_bases) - header_discount
```

**Critical arithmetic consequence**: If a tax is on-line, its base = that line's net. If a tax is at-header, its base = sum of ALL line nets minus any header discount.

A document with a single tax rate applied uniformly across all lines LOOKS identical whether it's a header tax or per-line taxes. The ERP computes the same total. But:
- If lines have **different** rates → must be per-line
- If document shows tax **once at bottom** → header
- If document shows tax **on each line** → per-line

### The Gross vs Net Unit Price Problem
Many documents show prices **inclusive of tax** (gross). The schema requires NET unit price. If you pass gross unit price to the ERP, it adds tax again → double-counts → wrong gross.

Detection: if `ERP_gross - document_gross ≈ sum_of_taxes`, the unit prices are likely gross.

Resolution: `net_unit_price = gross_unit_price / (1 + tax_rate/100)`
But only apply this if independently confirmed from the document (Rule 3).

---

## 4. Master Data Resolution Strategy

### Supplier (supplier_id)
Match priority:
1. VAT ID exact match (most reliable)
2. Name exact match
3. Name fuzzy match (normalized, lowercase, remove GmbH/Ltd/Sdn Bhd etc.)
4. Address fragment match
5. Email domain match

### Buyer (company_code / BU / location)
The buyer is always BOLTGROUP. The specific BU depends on which Bolt entity the invoice is addressed to:
- "Bolt Technology" or "Bolt Technology OU" → EE001
- "Bolt Holdings" or "Bolt Holdings OU" → EE004
- "Bolt Ghana" → GH001, LOC_GH_001
- "Bolt Malaysia" → MY001, LOC_MY_001
- "Bolt South Africa" → ZA001, LOC_ZA_001
- "Bolt Operations UK" → GB001, LOC_GB_001

Fallback: infer from invoice currency/country if entity name not explicit.

### Tax (tax_type_code)
Match on: country code + tax type + rate. Rate tolerance ±0.1%.
Priority: exact (country+type+rate) > country+rate > type+rate.

### Payment Terms (payment_term_id)
1. Text aliases (case-insensitive)
2. Date math: days = due_date - invoice_date, match to nearest term

### PO (po_id)
Exact match only. Two POs in master. If printed but not matched → po_id = "".

---

## 5. Document Classification Strategy

### Naming Convention Hints
- **INV-***: Invoice-family docs (could be INVOICE, CREDIT_MEMO, or statement)
- **HLD-***: "Hold" documents — likely non-payables (delivery notes, statements, remittance advices)
- **DU-***: "DU" = German "Dokument Unterlage" (supporting documents) — likely delivery notes, account statements

### Classification Signals
1. Document title/header: "INVOICE", "Rechnung", "Factura", "Credit Note", "Delivery Note"
2. Presence of invoice number + amount payable → likely payable
3. Presence of "Balance Due" / "Amount Due" vs "For your records" / "No payment required"
4. Multi-page DU files with 10-20 pages → likely account statements (multi-payable or declined)

### DU-05s.pdf (15 pages) and DU-02.pdf (20 pages)
These are almost certainly account statements or multi-invoice documents. DU-05s is "statement supplement" to DU-05. Need vision to classify each page.

---

## 6. Handling the "Documents That Cannot Be Solved"

The README explicitly says: "At least one document asks something of you that the page does not contain the answer to."

Candidates:
- A document with ambiguous totals where the ERP cannot be made to match without inventing data
- A document in a currency/tax regime where the tax math doesn't resolve
- A document that is genuinely a non-payable despite looking like an invoice

The correct response: declined[] with an honest reason. Never fabricate.

---

## 7. ERP Reconciliation Strategy

After extracting a payable, run erp_book() and compare to document gross_total.

If they match: ✓ done
If they don't match:
1. Check delta magnitude
2. delta ≈ total tax amount → possible gross-vs-net unit price issue
3. delta ≈ individual line amounts → possible missing line
4. delta is a rounding residual (< 0.05) → acceptable for some rounding conventions
5. delta is unexplainable without inventing data → log, leave as-is (Rule 1)

The key: a mismatch without a document-grounded explanation means we accept the mismatch. We don't fix it with invented numbers.

---

## 8. File Structure

```
candidate_kit/
├── documents/           # 42 input PDFs (read-only)
├── master_data/         # reference data (read-only)
├── erp.py               # oracle (read-only, import only)
├── AUTODRAFT_SCHEMA.md  # schema reference
├── sample_autodraft.json
├── output/              # generated outputs (one per PDF)
│   ├── INV-01.json
│   └── ...
├── process.py           # MAIN ENTRY POINT — one command
├── extractor.py         # PDF text/image extraction
├── classifier.py        # document type classification
├── field_extractor.py   # LLM-based field extraction
├── master_resolver.py   # master data code resolution
├── tax_placer.py        # tax placement logic
├── erp_validator.py     # ERP reconciliation
├── utils.py             # shared helpers
└── README.md            # single documented command
```

---

## 9. Product Roadmap

### Phase 1: Foundation (NOW)
- [x] Environment assessed (ollama+moondream available, pypdf works)
- [ ] Write DESIGN.md (architecture thinking)
- [ ] Implement extraction layer (text + vision)
- [ ] Implement master data resolver

### Phase 2: Core Pipeline
- [ ] Implement classification
- [ ] Implement field extraction via LLM
- [ ] Implement tax placement logic
- [ ] Wire ERP validator

### Phase 3: Process All Documents
- [ ] Run pipeline on all 42 PDFs
- [ ] Review output quality
- [ ] Identify structural failures

### Phase 4: Diagnosis & Fix
- [ ] Debug ERP mismatches
- [ ] Handle edge cases found in actual documents
- [ ] Write DESIGN.md answers from real findings

### Phase 5: Submission
- [ ] Clean README with single command
- [ ] Final output/*.json committed
- [ ] DESIGN.md finalized

---

## 10. The Architectural Principle

**Do less, more faithfully.**

The temptation is to build clever heuristics that fix every document. The brief warns against this — a fix that fires where it shouldn't costs more than never fixing. 

The winning architecture is one that:
1. Extracts faithfully (what's on the page)
2. Classifies honestly (payable or not)
3. Resolves codes rigorously (match or blank)
4. Places taxes structurally (where the document puts them)
5. Validates with the oracle (and accepts mismatches it cannot explain)

This generalises to held-back documents because it's principled, not case-specific.
