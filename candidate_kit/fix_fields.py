import re

with open('autodraft/fields.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find the function
start_idx = content.find('def _extract_line_items_from_text')
if start_idx >= 0:
    # Find the end of the function
    next_def = content.find('\ndef ', content.find('return items', content.find('def _extract_line_items_from_text')) + 10)
    if next_def == -1:
        end_idx = len(content)
    else:
        end_idx = next_def

    new_func = '''def _extract_line_items_from_text(layout: PageLayout, g: Dict[str, str]) -> List[LineItemExt]:
    """Fallback: extract line items from footer text lines.
    Matches patterns like: '1x Description QTY UNIT_PRICE TOTAL' or 'Qty Description Unit Total'"""
    items = []
    # Pattern: optional quantity x, description, optional quantity, unit price, total
    # e.g., "1x AktivkolarVeritas8000komplekt 24 tundi 103,60 103,60"
    #       "2x AktivkolarNOVAVeritas12 24 tundi E20,00"
    #       "1x Linnasisenetransport Fikseeritud E50,00 50,00"
    # Handles currency prefix (E, €, $, etc.) before unit price
    # Total is optional (some lines only have unit price when qty=1)
    line_pattern = re.compile(
        r"^(\\d+)x\\s+(.+?)\\s+(\\d+(?:[.,]\\d+)?)\\s+(?:tundi|hrs?|hours?|units?|pcs?|stk|stueck)?\\s*[€$£E]?\\s*([\\d.,]+)?\\s*([\\d.,]+)?$",
        re.I
    )
    # Alternative: "1x Description Fixed E50,00 50,00" or "1x Description Fikseeritud E50,00 50,00"
    line_pattern2 = re.compile(
        r"^(\\d+)x\\s+(.+?)\\s+(?:Fixed|Fikseeritud)\\s*[€$£E]?\\s*([\\d.,]+)\\s*([\\d.,]+)$",
        re.I
    )
    # Pattern without x: "Qty Description UnitPrice Total"
    line_pattern3 = re.compile(
        r"^(\\d+(?:[.,]\\d+)?)\\s+(.+?)\\s*[€$£E]?\\s*([\\d.,]+)\\s*([\\d.,]+)$",
        re.I
    )
    # Pattern: Description Qty/Unit UnitPrice Total (e.g., "Description 1/1 EA 39.99 39.99")
    # Description can contain spaces, Qty/Unit like "1/1 EA", "2/2 EA", "1/1"
    line_pattern4 = re.compile(
        r"^(.+?)\\s+(\\d+/\\d+(?:\\s+\\w+)?)?\\s*[€$£E]?\\s*([\\d.,]+)\\s*([\\d.,]+)$",
        re.I
    )

    patterns = [line_pattern, line_pattern2, line_pattern3, line_pattern4]

    # Process individual footer lines (not joined footer_text)
    for ln in layout.footer_lines:
        line = ln.text.strip()
        if not line:
            continue
        # Skip summary/tax/total lines
        low = line.lower()
        if any(kw in low for kw in ("vahesumma", "summa", "kaibemaks", "allahindlus", "tasumata", "subtotal", "total", "vat", "tax", "mwst", "discount", "rabatt")):
            continue

        for pat in patterns:
            m = pat.search(line)
            if m:
                groups = m.groups()
                if pat == line_pattern:
                    qty_str, desc, qty2, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    if unit_price:
                        a = _money_token(unit_price)
                        if a is not None:
                            li.unit_price = str(a)
                    if total:
                        a = _money_token(total)
                        if a is not None:
                            li.total = str(a)
                    elif li.unit_price and qty_d:
                        li.total = quantize_2(Decimal(li.unit_price) * qty_d)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
                elif pat == line_pattern2:
                    qty_str, desc, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    a = _money_token(unit_price)
                    if a is not None:
                        li.unit_price = str(a)
                    a = _money_token(total)
                    if a is not None:
                        li.total = str(a)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
                elif pat == line_pattern3:
                    qty_str, desc, unit_price, total = groups
                    qty_d = _money_token(qty_str)
                    if qty_d is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    li.quantity = str(qty_d)
                    a = _money_token(unit_price)
                    if a is not None:
                        li.unit_price = str(a)
                    a = _money_token(total)
                    if a is not None:
                        li.total = str(a)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
                elif pat == line_pattern4:
                    desc, qty_unit, unit_price, total = groups
                    a = _money_token(total)
                    if a is None:
                        continue
                    li = LineItemExt(description=desc.strip())
                    # qty_unit might be like "1/1 EA" or "1/1" or None
                    if qty_unit:
                        # Extract qty from "1/1 EA" or "1/1"
                        qty_part = qty_unit.split("/")[0]
                        qty_d = _money_token(qty_part)
                        if qty_d is not None:
                            li.quantity = str(qty_d)
                    a = _money_token(unit_price)
                    if a is not None:
                        li.unit_price = str(a)
                    li.total = str(a)
                    li.item_type = _item_type(li.description)
                    items.append(li)
                    break
        return items'''

# Replace the function
start_idx = content.find('def _extract_line_items_from_text')
next_def = content.find('\ndef ', content.find('return items', content.find('def _extract_line_items_from_text')) + 10)
if next_def == -1:
    end_idx = len(content)
else:
    end_idx = next_def

new_content = content[:start_idx] + new_func + content[end_idx:]

with open('autodraft/fields.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done!')