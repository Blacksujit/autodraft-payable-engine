import sys

with open(r'D:\candidate_kit\candidate_kit\autodraft\fields.py', 'r', encoding='utf-8') as f:
    s = f.read()

# Find the Pass 2 tax labels section
old_text = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 64]
            # Find amount after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

new_text = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 48]
            # Find amount immediately after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            # Verify this is a tax amount by checking context
            # Skip if the amount appears to be a subtotal or total
            context = low[m.start():m.end() + 64].lower()
            if any(kw in context for kw in ("subtotal", "sub total", "total inc", "total ex", "grand total", "balance", "amount due", "balance due", "total due", "zu zahlen", "betrag", "arvekokku", "tasuda", "kokku", "summa", "k\w*maksuga", "verschuldigd", "zu zahlen", "betrag", "a pagar", "montant", "saldo")):
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

with open(r'D:\candidate_kit\candidate_kit\autodraft\fields.py', 'r', encoding='utf-8') as f:
    s = f.read()

old = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 64]
            # Find amount after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

new = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 48]
            # Find amount immediately after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            # Verify this is a tax amount by checking context
            # Skip if the amount appears to be a subtotal or total
            context = low[m.start():m.end() + 64].lower()
            if any(kw in context for kw in ("subtotal", "sub total", "total inc", "total ex", "grand total", "balance", "amount due", "balance due", "total due", "zu zahlen", "betrag", "arvekokku", "tasuda", "kokku", "summa", "k\w*maksuga", "verschuldigd", "zu zahlen", "betrag", "a pagar", "montant", "saldo")):
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

with open(r'D:\candidate_kit\candidate_kit\autodraft\fields.py', 'r', encoding='utf-8') as f:
    s = f.read()

old_text = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 64]
            # Find amount after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

new_text = '''    # Pass 2: tax labels with amounts (no explicit %) - e.g., "GST $52.00"
    # Only run if Pass 1 found nothing, to avoid duplicating rate-based taxes
    if not items:
        for m in re.finditer(r"\b(gst|vat|mwst|ust|iva|btw|moms|sst|tax|steuer|k\w*maks|tax)\b", low, re.I):
            label = m.group(0)
            tail = low[m.end():m.end() + 48]
            # Find amount immediately after label (may have currency symbol)
            am = re.search(r"[\$\xe2\x82\xac\xe2\x80\xac]?\s*([\d][\d.,]{1,15})", tail)
            if not am:
                continue
            amt = _clean_amt(am.group(1))
            if amt is None:
                continue
            # Verify this is a tax amount by checking context
            # Skip if the amount appears to be a subtotal or total
            context = low[m.start():m.end() + 64].lower()
            if any(kw in context for kw in ("subtotal", "sub total", "total inc", "total ex", "grand total", "balance", "amount due", "balance due", "total due", "zu zahlen", "betrag", "arvekokku", "tasuda", "kokku", "summa", "k\w*maksuga", "verschuldigd", "zu zahlen", "betrag", "a pagar", "montant", "saldo")):
                continue
            low2 = m.group(0).lower()
            tax_type = "VAT"
            for k, ty in (("nhil", "NHIL"), ("getfl", "GETFL"), ("getfund", "GETFL"),
                          ("covid", "COVID"), ("withhold", "WHT"), ("wht", "WHT"),
                          ("sst", "SST"), ("gst", "GST"), ("moms", "MOMS"), ("iva", "IVA"),
                          ("taxe", "VAT"), ("mwst", "VAT"), ("ust", "VAT"), ("uso", "USE"), ("nicht steuerbar", "NP")):
                if k in m.group(0).lower():
                    tax_type = ty
                    break
            t = TaxItem()
            t.tax_type = tax_type
            t.tax_name = m.group(0).upper()
            t.tax_rate = ""
            t.tax_amount = amt
            items.append(t)
            g.setdefault("taxes", m.group(0))'''

with open(r'D:\candidate_kit\candidate_kit\autodraft\fields.py', 'r', encoding='utf-8') as f:
    s = f.read()

if old_text in s:
    s = s.replace(old_text, new_text)
    with open(r'D:\candidate_kit\candidate_kit\autodraft\fields.py', 'w', encoding='utf-8') as f:
        f.write(s)
    print("Replaced successfully")
else:
    print("Old text not found")
    # Try to find it
    idx = s.find('Pass 2: tax labels')
    if idx >= 0:
        print("Found at:", s[idx:idx+500])
    else:
        print("Not found")