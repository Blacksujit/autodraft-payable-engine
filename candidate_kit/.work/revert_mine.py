import io
s = open('autodraft/fields.py', encoding='utf-8').read()
s = s.replace('roles = {"unit": -1, "qty": -1, "total": -1, "discount": -1, "pos": -1, "tax": -1}',
              'roles = {"unit": -1, "qty": -1, "total": -1, "discount": -1, "pos": -1}')
old = """                elif _is_tax_header(label):
                    roles["tax"] = col_idx

"""
s = s.replace(old, '')
i = s.find('def _rate_token(s: str)')
j = s.find('def _extract_line_items_from_text(')
assert 0 < i < j, (i, j)
s = s[:i] + s[j:]
s = s.replace('''    if layout.table is not None:
        _attach_line_taxes(doc, layout.table, g)

''', '')
# qty loop exclusion
s = s.replace(' and c.index != roles["tax"]', '')
# tax fallback block
k = s.find('    if roles["tax"] < 0:')
m = s.find('    best, best_score = None, -1', k)
assert 0 < k < m, (k, m)
s = s[:k] + s[m:]
open('autodraft/fields.py', 'w', encoding='utf-8').write(s)
print('reverted-mine ok', k, m, i, j)
