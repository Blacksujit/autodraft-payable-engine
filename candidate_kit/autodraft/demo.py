"""demo.py - interactive CLI demo for Autodraft.

Gives a reviewer a self-serve way to test the pipeline in real time and
reproduce the headline claim: the machine is honest on documents it has never
seen.  Every document, open or held-back, runs through the same unmodified
pipeline and the same ERP gate; a record is emitted only when the components
recompute to the printed gross within 0.01, and everything else is declined
with a named reason.

Commands:
  python -m autodraft demo [corpus...]
      Interactive menu over one or more corpora.  Each corpus is a directory
      of PDFs; the default is `documents` plus `heldback/documents`.

  python -m autodraft demo --doc <stem>
      Process one document non-interactively and print its full report.

  python -m autodraft demo --all
      Run every corpus and print a verdict table (PASS / DECLINED / ERROR).

  python -m autodraft demo --json <outdir>
      Also write the emitted records under <outdir>/<stem>.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from autodraft.pipeline import process_pdf_detail
from autodraft.audit import audit_file
from erp import erp_book

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPORA = ["documents", "heldback/documents"]

# ground-truth gross for the held-back set, from heldback/build_synthetic.py
HELD_GROUND_TRUTH = {
    "HELD-01": "210.00",
    "HELD-02": "1500.60",
    "HELD-03": "32.36",
    "HELD-04": "87.12",
    "HELD-05": "36.89",
    "HELD-06": "600.00 (x2 invoices)",
    "HELD-07": "1100.00",
    "HELD-08": "70.00",
}


def _num(v) -> float:
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _printline(char="-", width=78):
    print(char * width)


def _docs_in(corpus: str):
    """Yield (stem, pdf_path) for every PDF in a corpus directory."""
    d = Path(corpus)
    if not d.is_dir():
        return []
    return [(p.stem, str(p)) for p in sorted(d.glob("*.pdf"))]


def _verdict(result: dict) -> str:
    if result.get("error"):
        return "ERROR"
    if result.get("payables"):
        return "PASS"
    return "DECLINED"


def _money(v, currency="") -> str:
    if v is None or str(v).strip() == "":
        return "-"
    s = f"{_num(v):,.2f}"
    return f"{s} {currency}".strip()


def _placement_label(placement: str) -> str:
    """Explain what a placement tag means to a reviewer."""
    if not placement:
        return "-"
    known = {
        "keep": "overall tax kept at header (as printed)",
        "line_rate": "line entities carry their own rate",
        "header_amount": "one header tax amount, whole subtotal base",
        "header_rate": "header rate applied to full subtotal",
        "force_header": "line-carved taxes re-homed to header to foot",
        "credit_note": "credit path (negative) handled",
        "solo_header": "single header tax, no line carving",
        "solo_line": "single line tax carried on the line",
        "ex_gst": "AU/NZ ex-GST genre applied",
        "declaration": "GST import duty declaration genre applied",
    }
    return known.get(placement, placement)


def _tax_rows(payable: dict):
    out = []
    for t in payable.get("taxes") or []:
        out.append(
            f"  tax  {t.get('tax_name') or t.get('tax_type') or '?'}  "
            f"rate={t.get('tax_rate') or '-'}%  amount={_money(t.get('tax_amount'), payable.get('currency'))}"
        )
    return out


def _recompute(payable: dict):
    """Recompute the gross the ERP would book from exactly the emitted parts."""
    try:
        book = erp_book(payable)
        return book["will_book_gross"]
    except Exception as e:
        return f"ERR {e}"


def _gate_line(payable: dict, printed_gross) -> str:
    recomputed = _recompute(payable)
    if isinstance(recomputed, str):
        return f"ERP recompute: {recomputed}"
    printed = _num(printed_gross)
    ok = abs(recomputed - printed) < 0.011
    tag = "GATE PASS" if ok else "GATE FAIL"
    return f"ERP recompute from emitted components = {recomputed:,.2f}  vs printed gross {printed:,.2f}  ->  {tag}"


def report_one(stem: str, pdf_path: str, show_text=False) -> dict:
    """Run the full pipeline on one PDF and print a reviewer-facing report."""
    ppath = Path(pdf_path)
    corpus = "heldback" if "heldback" in ppath.parts else ppath.parent.name

    _printline("=")
    print(f"{stem}   [corpus: {corpus}]")
    _printline("=")

    raw = process_pdf_detail(pdf_path)
    if len(raw) != 5:
        result = raw[0] if raw else {"error": "no result"}
        ext = None
        placement = None
        note = ""
    else:
        result, ext, payable, placement, note = raw

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return result

    payables = result.get("payables") or []
    declined = result.get("declined") or []

    if payables:
        for i, p in enumerate(payables, 1):
            if len(payables) > 1:
                _printline("-")
                print(f"PAYABLE {i} / {len(payables)}")
                _printline("-")
            gt = ""
            if corpus.startswith("heldback"):
                exp = HELD_GROUND_TRUTH.get(stem, "")
                if exp:
                    home_ok = _num(exp.split(" ")[0])
                    got = _num(p.get("gross_total"))
                    mark = "OK" if abs(home_ok - got) < 0.011 else "MISMATCH"
                    gt = f"   [held-back ground truth: {exp} - {mark}]"
                    if "x2" in exp and len(payables) < 2:
                        gt += "   WARNING: source PDF holds 2 invoices, only 1 emitted"
            print(f"gross_total      {_money(p.get('gross_total'), p.get('currency'))}{gt}")
            print(f"subtotal         {_money(p.get('subtotal'), p.get('currency'))}")
            print(f"tax_total        {_money(p.get('total_tax_amount'), p.get('currency'))}")
            print(f"invoice_number   {p.get('invoice_number') or '-'}")
            print(f"invoice_date     {p.get('invoice_date') or '-'}")
            print(f"due_date         {p.get('due_date') or '-'}")
            print(f"supplier         {(p.get('supplier') or {}).get('name') or '-'}")
            print(f"PO               {p.get('po_number') or '-'}")
            print(f"payment_term     {p.get('payment_term_id') or '-'}")
            print(f"invoice_type     {p.get('invoice_type') or '-'}")
            print(f"currency         {p.get('currency') or '-'}")
            print(f"line_items       {len(p.get('line_items') or [])}")
            for _t in _tax_rows(p):
                print(_t)
            print(f"placement        {_placement_label(placement)}")
            print(_gate_line(p, p.get("gross_total")))
            if note:
                print(f"note             {note}")
    else:
        print("NO PAYABLE EMITTED")
        for d in declined:
            print(f"  doc_type : {d.get('doc_type')}")
            print(f"  reason   : {d.get('reason')}")
        if note and not any(re.search(rf"{note}", str(d.get('reason', ''))) for d in declined):
            print(f"  pipeline note : {note}")

    # Fidelity audit for this single document (re-checks grounding/master codes)
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, f"{stem}.json")
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
            aud = audit_file(pdf_path, out_path)
        if aud.get("status") == "ok":
            print("fidelity audit  CLEAN (every emitted number is grounded on the page)")
        else:
            print(f"fidelity audit  ISSUES: {len(aud.get('issues', []))}")
            for iss in aud.get("issues", [])[:10]:
                print(f"   - {iss}")
    except Exception as e:
        print(f"fidelity audit  skipped ({e})")

    if show_text and ext is not None:
        _printline(".")
        print("PAGE TEXT (raw OCR view):")
        print(ext.page_text[:1600])
    return result


def _report_or_return(stem: str, pdf: str) -> dict:
    res = report_one(stem, pdf)
    _printline("-")
    return res


def interactive(corpora: list[str]):
    docs = []
    for c in corpora:
        for stem, pdf in _docs_in(c):
            docs.append((stem, pdf, c))

    if not docs:
        print("No PDFs found in " + ", ".join(corpora))
        return 1

    print("Autodraft interactive demo")
    print(f"Corpora: {', '.join(str(Path(c)) for c in corpora)}  ({len(docs)} documents)")
    _printline("=")
    print("Choose a document by its ID, or:  all | q")
    print("  q        quit")
    print("  all      verdict table for every document")
    _printline("=")

    selected = {}
    # memoise results so re-lookups are instant after first run
    while True:
        print()
        for idx, (stem, _pdf, corpus) in enumerate(docs):
            tag = ""
            if corpus.startswith("heldback"):
                tag = "  [H]"
            print(f"  {idx:>3}.  {stem}{tag}")
        print()
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice.lower() in ("q", "quit", "exit"):
            break
        if choice.lower() in ("a", "all"):
            print()
            print(f"{'VERDICT':<9} {'STEM':<24} {'GROSS':>24}   CORPUS")
            _printline("-", 76)
            for stem, pdf, corpus in docs:
                res = selected.get(stem) or report_one(stem, pdf)
                selected[stem] = res
                v = _verdict(res)
                gt = ""
                if corpus.startswith("heldback") and v == "PASS":
                    exp = HELD_GROUND_TRUTH.get(stem, "")
                    if exp:
                        p0 = (res.get("payables") or [{}])[0]
                        home_ok = _num(exp.split(" ")[0])
                        got = _num(p0.get("gross_total"))
                        gt = "  (gt ok)" if abs(home_ok - got) < 0.011 else "  (gt MISMATCH)"
                gross = ""
                if res.get("payables"):
                    p0 = res["payables"][0]
                    gross = _money(p0.get("gross_total"), p0.get("currency"))
                elif res.get("declined"):
                    gross = f"declined: {res['declined'][0].get('doc_type', '?')}"
                tag = "[H] " if corpus.startswith("heldback") else "    "
                print(f"{v:<9} {tag}{stem:<20} {gross:>24}   {Path(corpus).name.split(chr(92))[-1]}")
                _printline("-", 76)
            continue
        try:
            idx = int(choice)
        except ValueError:
            print(f"unknown input: {choice!r}")
            continue
        if not (0 <= idx < len(docs)):
            print(f"index {idx} out of range (0..{len(docs)-1})")
            continue
        stem, pdf, _corpus = docs[idx]
        print()
        res = _report_or_return(stem, pdf)
        selected[stem] = res
    return 0


def run_all(corpora: list[str], json_out: str = ""):
    if json_out:
        os.makedirs(json_out, exist_ok=True)
    print(f"{'VERDICT':<9} {'STEM':<24} {'GROSS':>12}  CORPUS")
    _printline("-", 72)
    for c in corpora:
        for stem, pdf in _docs_in(c):
            res = report_one(stem, pdf)
            if json_out:
                with open(os.path.join(json_out, f"{stem}.json"), "w", encoding="utf-8") as fh:
                    json.dump(res, fh, ensure_ascii=False, indent=2)
            v = _verdict(res)
            gross = ""
            if res.get("payables"):
                p0 = res["payables"][0]
                gross = _money(p0.get("gross_total"), p0.get("currency"))
            elif res.get("declined"):
                gross = f"declined: {res['declined'][0].get('doc_type', '?')}"
            print(f"{v:<9} {stem:<24} {gross:>30}  {Path(c).name}")
            _printline("-", 72)
    return 0


def main(argv: list[str] | None = None):
    argv = list(sys.argv[1:] if argv is None else argv)

    corpora = DEFAULT_CORPORA
    json_out = ""
    doc = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--heldback":
            corpora = ["documents", "heldback/documents"]
        elif a in ("--open", "--open-only"):
            corpora = ["documents"]
        elif a == "--json":
            i += 1
            if i < len(argv):
                json_out = argv[i]
        elif a == "--doc":
            i += 1
            if i < len(argv):
                doc = argv[i]
        elif a in ("--all", "--table"):
            return run_all(corpora, json_out)
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            # positional: treat as an extra corpus directory
            corpora.append(a)
            if doc is None:
                pass
        i += 1

    if doc:
        found = None
        for c in corpora:
            for stem, pdf in _docs_in(c):
                if stem.lower() == doc.lower():
                    found = (stem, pdf)
                    break
            if found:
                break
        if not found:
            print(f"document {doc!r} not found in {[str(Path(c)) for c in corpora]}")
            available = []
            for c in corpora:
                available += [s for s, _ in _docs_in(c)]
            print("available stems: " + ", ".join(sorted(available)))
            return 1
        res = report_one(*found, show_text="--text" in argv)
        if json_out:
            os.makedirs(json_out, exist_ok=True)
            with open(os.path.join(json_out, f"{found[0]}.json"), "w", encoding="utf-8") as fh:
                json.dump(res, fh, ensure_ascii=False, indent=2)
        return 0

    return interactive(corpora)


if __name__ == "__main__":
    sys.exit(main())