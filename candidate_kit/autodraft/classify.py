"""classify.py - document kind. Order matters; the first rule that fires wins."""
from __future__ import annotations
import re
from typing import Optional

from autodraft.fields import ExtractedDoc

CREDIT = re.compile(r"\b(credit\s*(memo|note)|gutschrift|kredit(nota|rechnung)|(?:kredit|kreedit)\w*arve\w*|storno|stornorechnung|crdnr?|nota\s*de\s*cr[eé]dito)\b", re.I)
CUSTOMS = re.compile(r"\b(customs|zoll|consolidated\s*invoice|bill\s*of\s*lading|shipment\s*advice|cartage\s*advice|net\s*weight|gross\s*weight|boxes\s*no\.?|hscode|hs\s*code|hts\w*:|tariff\s*code|country\s*of\s*origin|incoterms|commercial\s*invoice|packing\s*list|certificate\s*of\s*origin|HS\s*code|HTS|commodity\s*code|country\s*code|KG\s+CN|KG\s+DE|KG\s+US|KG\s+GB|EAR99|NLR|export\s*control|customs\s*declaration|import\s*declaration|entry\s*summary|manifest|estancia\s*aduan(?:eira|iera)|declara(?:c|c)a[oã]o|expedidor|destinatario|valor\s*aduan(?:e|e)iro|peso\s*bruto|peso\s*liquido|peso\s*neto|pais\s*de\s*orig(?:e|i)m|codigo\s*das\s*mercadorias|codigo\s*arancelario|incoterms?|frete|seguro|despachante|transit(?:a|á)rio|adicao|mercadorias|ncm|nbm|regime|tratamento|tributos|ipi|icms|pis|cofins|armazem|deposito|aduana|declaracion|expedidor|destinatario|valor\s*en\s*aduan|peso\s*bruto|peso\s*neto|pais\s*de\s*origen|codigo\s*arancelario|incoterms|flete|seguro|despachante|transitario|adicion|mercancias|partida\s*arancelaria|tasa|arancel)\b", re.I)
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
    doc_type = "TAX_INVOICE" if re.search(r"\btax\s*invoice\b|\bVAT\s*invoice\b|\btax\s*invoice\b|undisdoc", t, re.I) else "INVOICE"
    return "INVOICE", doc_type, ""
