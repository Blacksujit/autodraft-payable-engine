from autodraft.ocr import ocr_words
from autodraft.geom import cluster_lines, group_lines_by_bands
from autodraft.structure import clean_numeric, amount_value, _has_decimal, _numeric_word, _cluster_centers, _is_summary_label

words = ocr_words('.work/pages/INV-10_p1.png')
lines = cluster_lines(words)
rows = group_lines_by_bands(lines)

# Find best run
def row_has_money(row):
    for ln in row:
        for w in ln.words:
            if clean_numeric(w.text) and amount_value(w.text) is not None and _has_decimal(w.text):
                return True
    return False

numeric_rows = [row_has_money(r) for r in rows]
run_start = -1
best_start = best_end = -1
for i, is_num in enumerate(numeric_rows):
    if is_num:
        if run_start < 0:
            run_start = i
    else:
        if run_start >= 0 and (i - 1) - run_start + 1 > best_end - best_start:
            best_start, best_end = run_start, i - 1
        run_start = -1
if run_start >= 0 and len(rows) - 1 - run_start + 1 > best_end - best_start:
    best_start, best_end = run_start, len(rows) - 1

run = rows[best_start : best_end + 1]
words_in_run = [w for r in run for ln in r for w in ln.words]
xmin = min(w.box.x0 for w in words_in_run)
xmax = max(w.box.x1 for w in words_in_run)
width = max(1e-9, xmax - xmin)
tol = max(4.0, 0.03 * width)

num_words = [w for w in words_in_run if _numeric_word(w) is not None]
centers = [w.box.x0 for w in num_words]
bands = _cluster_centers(centers, tol)

class Col:
    def __init__(self, i, b):
        self.index = i
        self.center = sum(b)/len(b)
        self.x0 = min(b) - tol/2
        self.x1 = max(b) + tol/2
        self.rows = {}

columns = [Col(i, b) for i, b in enumerate(bands)]
money_cols = [1, 2]
leftmost_money_band = min(c.center for c in columns if c.index in money_cols)
desc_x1 = leftmost_money_band - tol
print('desc_x1:', desc_x1)

from autodraft.structure import Table

occupancy = {}
for r_i, r in enumerate(run):
    key = best_start + r_i
    row_map = {}
    for ln in r:
        for w in ln.words:
            if w.box.x0 < 864:
                col = Table.DESCR
            else:
                best_c = min(columns, key=lambda c: abs(w.box.x0 - c.center))
                if abs(w.box.x0 - best_c.center) <= tol:
                    col = best_c.index
                else:
                    col = None
            if col is not None:
                row_map.setdefault(col, []).append((w.box, w.text))
    occupancy[key] = row_map

# desc edge computation
leftmost = []
for key, row_map in occupancy.items():
    if key == best_start:
        continue
    if not any(i >= 0 and i in money_cols for i in row_map):
        print(f'Row {key}: no money cols')
        continue
    if not row_map.get(Table.DESCR):
        print(f'Row {key}: no DESCR')
        continue
    desc_texts = [tx for _, tx in row_map[Table.DESCR]]
    combined_desc = ' '.join(desc_texts).strip()
    if _is_summary_label(combined_desc):
        print(f'Row {key}: summary - {combined_desc[:60]}')
        continue
    desc_xs = []
    for bx, tx in row_map[Table.DESCR]:
        stripped = tx.strip()
        if stripped.isdigit():
            continue
        if len(stripped) <= 3 and stripped.isalpha():
            continue
        if any(c.isalpha() for c in stripped):
            desc_xs.append(bx.x0)
    if desc_xs:
        print(f'Row {key}: desc_xs={desc_xs}, min={min(desc_xs)}, desc="{combined_desc[:60]}"')
        leftmost.append(min(desc_xs))
    else:
        print(f'Row {key}: no desc_xs, desc="{combined_desc[:60]}"')

print('Leftmost:', leftmost)
if not leftmost:
    print('RETURNING None - no leftmost!')
else:
    from autodraft.structure import _cluster_centers
    lc = _cluster_centers(sorted(leftmost), tol)
    lc.sort(key=len, reverse=True)
    desc_edge = sum(lc[0]) / len(lc[0])
    print('desc_edge:', desc_edge)

    def is_data_row(key, row_map):
        if not row_map:
            return False
        if not any(i >= 0 and i in money_cols for i in row_map):
            return False
        for toks in row_map.get(Table.DESCR, []):
            bx, tx = toks
            dist = abs(bx.x0 - desc_edge)
            if dist <= tol:
                return True
        return False

    for key in sorted(occupancy):
        if key == best_start:
            continue
        result = is_data_row(key, occupancy[key])
        print(f'Row {key}: is_data_row={result}')