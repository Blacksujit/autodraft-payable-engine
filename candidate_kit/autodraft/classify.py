"""classify.py - document kind. Order matters; the first rule that fires wins."""
from __future__ import annotations
import re
from typing import Optional

from autodraft.fields import ExtractedDoc

CREDIT = re.compile(r"\b(credit\s*(memo|note)|gutschrift|kredit(nota|rechnung)|(?:kredit|kreedit)\w*arve\w*|storno|stornorechnung|crdnr?)\b", re.I)
CUSTOMS = re.compile(r"\b(customs|zoll|consolidated\s*invoice|bill\s*of\s*lading)\b", re.I)
NOTPAY = re.compile(r"\b(quote|quotation|estimate|proforma|goods?\s*received|delivery\s*note|pick\s*list|cancel(lation)?)\b", re.I)
DEDUCTION = re.compile(r"\b(reimburse|deduct|offset|adjust)\b", re.I)


def decide(doc: ExtractedDoc) -> tuple:
    """(doc_type, invoice_type, decline_reason). decline_reason non-empty => NOT_A_PAYABLE."""
    t = doc.page_text
    low = t.lower()
    if CREDIT.search(t):
        return "CREDIT_MEMO", "CREDIT_MEMO", ""
    if CUSTOMS.search(t):
        return "CUSTOMS_INVOICE", "INVOICE", "customs_statement"
    if NOTPAY.search(low):
        return "NOT_A_PAYABLE", "QUOTE", "quote_or_proforma"
    if re.search(r"\butilities?\b|\belectric(i|al)?\b|\bcondenser\b", t, re.I) and DEDUCTION.search(t):
        return "NOT_A_PAYABLE", "UTILITY_REIMBURSEMENT", "utility_reimbursement"
    doc_type = "TAX_INVOICE" if re.search(r"\btax\s*invoice\b|\bVAT\s*invoice\b|undisdoc", t, re.I) else "INVOICE"
    return "INVOICE", doc_type, ""
