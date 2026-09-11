# Architecture

*Autodraft* turns a folder of supplier PDFs into ERP-ready payable records.
It must satisfy three properties:

1. **Grounded** — every value emitted appears on the document (no invented numbers).
2. **Structured faithfully** — quantities, prices, discounts, taxes and charges stay
   decomposed and keep the position the document gives them (header vs line).
3. **General** — a held-back document must stand the same chance as an open one;
   the system's margin, not its memorisation, is what is graded.

This document records the architecture and the reasons each decision was made.

---

## 1. The problem, reframed

The scoreboard is a sealed ERP oracle (`erp.py`). Given one payable's *raw
components*, it recomputes the gross it will book:

```
erp_book(payable) -> {"will_book_gross": float, "currency": str}
```

Correctness is **not** "did the numbers match at the end". It is:

> Reconstruct, from the parts the ERP can consume, a record whose recomputed
> gross *equals* the gross the document states — where every part is grounded
> in the document and placed where the document placed it.

Two consequences drive the whole design:

- **Same total, wrong structure, is a wrong answer.** If a document puts a 19%
  tax *at the line* and we hoist it to the header (changing the tax base), the
  ERP recomputes a different gross even though "the total looks fine". Placement
  is a correctness constraint, not a style choice.
- **The held-back set out-weights the open set.** The reported metric is the
  *distance* between open and held-back performance. Fitting the 43 open
  documents is strategically pointless; building machinery that generalises is
  everything. There is therefore **zero per-file special-casing** in the system.

## 2. Runtime posture and the two-source policy

The whole pipeline runs free and local: CPU-only Python, open-source wheels,
and a locally-installed Ollama for the small-LLM layers. No API keys are
required for the default run; premium vision is an optional, backported backend.

Every page yields words in one of two ways:

| Source | When | Producer | Shape |
|---|---|---|---|
| **Text layer** | embedded, extractable text (≥12 chars) | `pdfplumber` | `Word(Box, text, conf=1.0)` |
| **OCR** | no usable text layer | `RapidOCR` (ONNX, CPU, multilingual) | `Word(Box, text, conf∈[0,1])` |

Both emit the same `Word` dataclass, so *everything downstream is source-agnostic*.
`Box`es are stored at producer-native scale; every geometric decision is
**ratio-based or relative**, never absolute-pixel — OCR scale varies (RapidOCR
returns ~3× page units), and held-back documents may render at any DPI.

Vision backends (`moondream`, `llava:7b` via Ollama) are used only for diagnosis
and as a *second opinion* on structure when geometry-based reconstruction is
too low-confidence — never as a source of numbers on their own. See §7.

## 3. Component map

```
 documents/*.pdf
      │
      ▼
 ┌─────────────┐   ┌──────────────────────────────┐
 │ render.py   │──▶│ PageSource per page:          │
 │ (pymupdf)   │   │  words (text-layer) OR        │
 └─────────────┘   │  PNG path for OCR             │
      └────────────▶ ocr.py (RapidOCR)             │
                  └──────────────────────────────┘
      │
      ▼
 ┌──────────────┐   cluster into lines & text rows
 │ structure.py │   detect & split columns, tables
 └──────────────┘   tag regions: header/footer/table
      │
      ▼
 ┌──────────────┐   currency + date-locale detection
 │ normalize.py │   number parsing to dot-decimal
 └──────────────┘   date parsing to ISO
      │
      ▼
 ┌──────────────┐   header fields: invoice#, dates, supplier,
 │ fields.py    │   VAT, PO, totals, terms
 └──────────────┘   line items: qty / unit / total / tax
      │
      ▼
 ┌──────────────┐   doc-type triage → INVOICE | CREDIT_MEMO | NOT_A_PAYABLE
 │ classify.py  │
 └──────────────┘
      │
      ▼
 ┌──────────────┐   resolve every code against the masters
 │ resolve.py   │   supplier_id · org codes · tax_type_code ·
 └──────────────┘   payment_term_id · po_id
      │
      ▼
 ┌──────────────┐   assemble payable · run the sealed oracle
 │ oracle.py    │   compare will_book_gross vs printed gross
 └──────────────┘   apply the three refusal rules
      │
      ▼
  output/X.json   (payables[] / declined[])  +  per-doc report
```

Strictly one-way: early stages never consult the masters; late stages never
re-read the page. A deterministic core owns faithfulness; learning layers
(name only) patch gaps — never contradict.

## 4. The reconstruction core (deterministic, source-agnostic)

### 4.1 Lines → rows → regions

Words are clustered into **visual lines** by y-band overlap
(`cluster_lines`), and lines into **text rows** (`group_lines_by_bands`) so a
wrapped cell becomes one logical row. Rows carry a union bbox, so every
decision below stays relative to the *page's own* word bounding box.

A page is then partitioned into **regions**:

- **Header / footer**: rows above the first table line and below the last.
- **Table**: contiguous rows with enough numeric alignment to form columns.

Column detection is deliberately geometric, not regex-driven: group row tokens
by x-centre into column bands, then verify each band is occupied consistently
down the table. This is what lets an invoice we have never seen — with columns
we have never named — still yield its line items.

### 4.2 Fields

Header fields live in label:value pairs; labels are matched **multilingually**
(`Rechnung Nr.` / `Invoice #` / `Factura Nº` / `Arve nr` / …). Values that a
label anchors are grounded **by proximity to the label's box**, and every value
parsed into the record is tracked back to the exact words that produced it
(§6: grounding ledger).

Line items come from the table region: each row's cells map to
`description / quantity / unit price / line total / per-line tax`, with the
column → role assignment inferred from header labels and value shapes (a cell
with a bare integer is a quantity; a currency cell under a "Menge" label is a
quantity; …). No role is assumed until at least two independent signals agree.

### 4.3 Locale handling (the numbers must not lie)

One document already shows *mixed* separators within a single total row
(`73,00` units, `438.00` grand total). Blind parsing would corrupt it.

`normalize.py` therefore:

1. Detects the **currency** from the strongest signal (symbol, ISO code, or
   the master-data country of the page's supplier).
2. Detects the **numeric locale** of each number individually from its
   separator pattern (`1.234,56` ⇒ thousands-dot/decimals-comma; `1,234.56`
   ⇒ the reverse; `1234.56` and `1234` are locale-transparent).
3. Emits **dot-decimal** into the JSON (the ERP does no locale parsing).

Dates follow the same rule set (`DD.MM.YYYY`, `MM/DD/YYYY`, `YYYY-MM-DD`,
`DD/MM/YYYY`), disambiguated by label semantics and document-level consistency;
the ISO `YYYY-MM-DD` form is written to the record. Where the label, the value
pattern, and a consistent day-range cannot jointly disambiguate, the date is
left empty rather than guessed.

## 5. Classification and the refusal rules (the third rule, enforced)

`classify.py` decides, per document:

- `INVOICE` — the normal case; fields expected: supplier, dates, items, a stated
  payables total.
- `CREDIT_MEMO` — the *same schema, credit values* (positive magnitudes; the
  ERP applies sign). Detected from credit-native signals: a negative/credit
  total, "credit note" / "Gutschrift" / "Nota de crédito" labels, a negative
  line extension, or a document that refunds a previous invoice. **A credit is
  still a payable** — it books.
- `NOT_A_PAYABLE` → `declined[]` with a reason. Quotes, pro-forma/estimates,
  statements (no payables total, list account movements), packing/delivery
  notes, terms-and-conditions pages, boilerplate attachments.

Three refusal rules are coded literally, and each is also a **grounding gatel**:

1. **No invented values.** A number may enter the record only if a word (or a
   mathematically airtight derivation from present words, e.g. tax = rate × base
   where all three are printed) produced it. If "balancing the books" tempts a
   number, the temptation is treated as evidence the document means something
   else — and the document is re-examined rather than patched.
2. **No invented codes.** Master codes resolve by explicit, scored matching
   against the masters; `""` is a legitimate, preferred answer over a guess.
3. **No creative corrections.** A "fix" (recomputation, sign flip, rounding
   change, header↔line migration) is applied only when an *independent fact on
   the document* justifies it (a printed rate agreeing with the tax master,
   an explicit "reverse charge" statement, a printed credit note word). A
   correction that would fire where it should not is worse than no correction.

## 6. Grounding ledger (how we keep the grader's invisible checks honest)

The document is read by an *ORCAd __ledger__*: every parsed token, every value
slot, and every resolved code retains a provenance record

```
{ field, page, box, words: ["Rechnung","Nr.",":"],"852566"], confidence, derived-from }
```

- A value slot is **grounded** iff its words exist on the page (opened for the
  ocr/text source).
- A **code is real** iff its resolve() match ties it to one specific master row
  that also agrees on an independent attribute (name/company, VAT id, country,
  rate).
- The oracle compare (below) is the final ground-truth assertion the system
  itself can run.

## 7. The small-LLM layer (Ollama; optional, never authoritative)

Ollama (installed; free, local, no keys) provides `llama3.2` (text) and the
vision models `moondream` (1.7 GB, fast) / `llava:7b`. The layer is
**consultative**, with hard constraints:

- **Input** is what the deterministic core already grounded (a *rendered page's
  OCR words*, not a raw binary blob the model can dream from).
- **Output** is a *tagged structure* (doc-type verdict, column roles, field
  bindings) that the core validates against the grounding ledger.
- **The LLM never emits numbers into the record.** Its numbers may only name
  candidates already present in the page words; the core re-extracts them from
  the page with its own deterministic parser.
- Escalation is **automatic and per-page**: geometry confidence below threshold
  ⇒ `moondream` verdict ⇒ still low ⇒ `llava:7b`. Low-latency path (text layer,
  clean OCR) never consults the LLM at all.

This posture keeps the model share **voluntary and bounded**: on easy pages it
is absent; on pathological pages it only *re-phrases* evidence the core then
verifies. A held-back document that triggers the LLM stands the same chance as
one that does not.

## 8. Master resolution (`resolve.py`)

| Autodraft field | Master | Match signals (strength, high → low) |
|---|---|---|
| `supplier.supplier_id` | `suppliers.json` | exact VAT id · exact name · normalised name (rapidfuzz) · country+city corroboration |
| `buyer.*` (org) | `chart_of_books.json` | exact org/business-unit/location name; invoice-to address |
| `taxes[].tax_type_code` | `tax_master.json` | country+rate+type triple; printed name alias |
| `payment_term_id` | `payment_terms.json` | printed term text ⇒ alias table ⇒ days |
| `po_id` | `po_master.json` | raw `po_number` printed on the doc matched to `po_number`, corroborated by supplier+currency |

Matching is **name-normalising + scored** (rapidfuzz token-set over lowercased,
diacritic-folded, punctuation-stripped strings), and a match must clear a
threshold and agree on one independent corroborating attribute. Sub-threshold
or ambiguous ⇒ honest `""`, never the nearest string.

### 8.1 Where the masters bite

`suppliers.json` includes rows for **Portugal** (`Zoomcopia Impressao Lda`,
`Distribeer Bebidas Lda`) while `tax_master.json` carries Portuguese `IVA`
rates — the corpus reaches beyond English/German. The tax master encodes
country-specific rates (e.g. `DE_190_VAT` 19%, `EST_220_VAT` 22%, `PT_230_IVA`
23%). Resolution uses the supplier's country to narrow the tax search space, so
a 23% line item on a Portuguese invoice resolves to `PT_230_IVA`, not to a
foreign 23% that does not exist.

## 9. The oracle and the on-run validator (`oracle.py`)

For every candidate payable the pipeline:

1. Assembles the payable exactly as the schema requires (decomposed components,
   header vs line placement, dot-decimal, codes).
2. Runs the sealed `erp_book()` (imported, never modified).
3. Compares `will_book_gross` to the document's stated gross.
4. **Passes only if they match** (and the grounding ledger is fully covered);
   otherwise the document is either re-examined once via the LLM escalation, or
   declined with a precise reason — **never force-booked**.

This loop is the system's own test harness: it runs on every file at runtime
and is what `make run` verifies last.

## 10. Failure semantics (the cost asymmetry is encoded)

- **False book** (booked a wrong or non-payable) = corrupts the ledger; the
  worst outcome. The validator refuses it structurally.
- **False decline** (failed to book a real payable) = a missed payable; the
  next-rank outcome, far less costly.
- The thresholds are therefore set **conservative by default**: emit when
  grounded + oracle-matching + structurally faithful; otherwise decline with
  a reason that names exactly which gate failed. A document we decline honestly
  earns more than one we book dishonestly.

## 11. Runtime, reproducibility, extension

- `python -m autodraft documents output` (one command; see `README.md`).
- Deterministic: fixed OCR DPI, fixed seeds where any randomness exists,
  cached page renders under `.work/`.
- **Extension seam**: a `VisionBackend` protocol with the Ollama default and a
  reserved premium-API implementation — the core is unaware of which backend
  satisfies detection, so a fancy-API swap is configuration, not a rewrite.
- Holds the brief's own standard: open-set scores AND (more importantly) the
  open→held-back **distance**. Every rule, threshold, and scorer in this
  document exists to shrink that distance.

## 12. Design notes / open questions still under investigation

- **Held-back posture for pathological docs**: the brief promises at least one
  document the open set "cannot solve the way the others were solved". Our
  position (documented in `DESIGN.md`) is to *recognise* it, capture exactly
  what the page does and does not support, and decline rather than fake it.
- **The `DU-*` customs consolidated invoice** (20-page, English) is a
  multi-invoice file — it must yield multiple `payables[]` entries. Page-level
  totals (`Page N of M`, per-page summary) are being triaged vs the one true
  payable total. This is the first place the multi-payable rule is exercised.