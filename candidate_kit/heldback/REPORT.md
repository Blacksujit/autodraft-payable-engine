# Held-back evidence — Phase 5

Never-seen corpus run through the **same, unmodified** extraction/booking
machinery (no per-file special-casing, no numbers injected into the record).
Source: `heldback/build_synthetic.py`; inputs `heldback/documents/*.pdf`;
outputs `heldback/output/*.json` (gitignored — regenerate freely).

## Verdicts

`BOOK` = emitted payable passes the ERP oracle gate. `DECLINE` = honest
refusal with a named reason. `GAP` = a genuinely-reconcilable document failed
to book (structural limitation on display). `HIT` = correct honest outcome.

| doc          | ground truth          | actual     | verdict  |
|--------------|-----------------------|------------|----------|
| HELD-01 FR   | bookable FACTURE      | DECLINE    | GAP      |
| HELD-02 IT   | bookable FATTURA      | DECLINE    | GAP      |
| HELD-03 NL   | bookable FACTUUR      | DECLINE    | GAP      |
| HELD-04 ES   | bookable FACTURA      | DECLINE    | GAP      |
| HELD-05 DE   | bookable RECHNUNG     | DECLINE    | GAP      |
| HELD-06      | two bookable invoices | DECLINE    | GAP      |
| HELD-07      | bookable credit note  | DECLINE    | GAP      |
| HELD-08      | bookable (ambig date) | DECLINE    | GAP      |
| HELD-09      | quote → refuse        | DECLINE    | HIT      |
| HELD-10      | customs → refuse      | DECLINE    | HIT      |
| HELD-UNSOLVABLE | no amount anywhere | DECLINE | HIT (no fabricated number) |

**Distance:** 8/8 bookable documents declined (structural gap — line-item
carving does not engage without the OCR-facing table columns it was tuned for;
same root cause as the open corpus). **Every** row ends book-or-decline; no
record ever carries a number the page did not print.

## What the set actually proved

1. `\biva\b` and `\bimpuesto\b` were listed as **customs** cues, but IVA /
   impuesto are ordinary VAT words (Italian/Spanish). HELD-02 and HELD-04 were
   first mis-shipped as `CUSTOMS_INVOICE`. Removing the two tokens from the
   classifier's customs pattern re-classified them to INVOICE and **also lifted
   the open corpus: INV-34 now books** (open bookings 15 → 16, ≈36 % → 38 %),
   with zero lost bookings.
2. A general, honest checkmate case (`HELD-UNSOLVABLE`) declines with a reason
   and emits **no payable and no invented amount** — the "provably unsolvable"
   behavior the design demands.
3. Genuine quotes (`HELD-09`) and customs/packing declarations (`HELD-10`)
   refuse with the correct named reasons, including on text-layer pages built
   from scratch.

## Phase 4 seam, demonstrated on this set

With `AUTODRAFT_CONSULT=1` the low-confidence honesty layer (local Ollama,
fail-open, narrative-only) re-phrases evidence on the decline path without ever
entering the record:

```
Invoice from FACTUUR. ERP gate failed (gross_mismatch:32.36:64.72;64.72;64.72;64.72;0.00;0.00;26.74):
the printed gross cannot be recovered from the emitted components within 0.01.
  + [consult: The supplier states $32.36 as the sum owed, on the grand total line.]
```

When Ollama is down or the reply is unusable the suffix is simply absent — the
default (`AUTODRAFT_CONSULT` unset) run is byte-for-byte deterministic.

## Reproduction

```
python heldback/build_synthetic.py        # regenerates the 11 PDFs
python -m autodraft heldback/documents heldback/output
python -c "import json; [print(k, json.load(open(f'heldback/output/{k}.json', encoding='utf-8'))['declined'][0]['reason'][:90]) for k in ...]"
```