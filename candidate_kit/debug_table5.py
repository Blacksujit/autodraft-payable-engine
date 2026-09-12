from autodraft.ocr import ocr_words
from autodraft.geom import cluster_lines, group_lines_by_bands
from autodraft.structure import clean_numeric, amount_value, _has_decimal, _numeric_word, _cluster_centers, _is_summary_label

words = ocr_words('.work/pages/INV-10_p1.png')
lines = cluster_lines(words)
rows = group_lines_by_bands(lines)

# Find best run
from autodraft.structure import clean_numeric, amount_value, _has_decimal, _numeric_word, _cluster_centers, _is_summary_label

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

has_header = False
with_header = best_start
if best_start > 0:
    n_words = sum(len(ln.words) for ln in rows[best_start - 1])
    if n_words >= 3:
        with_header = best_start - 1
        has_header = True

print('with_header:', with_header, 'best_end:', best_end, 'has_header:', has_header)

# Now manually trace _build_table
from autodraft.structure import Table, _cluster_centers, _is_summary_label, _numeric_word

run = rows[with_header : best_end + 1]
words = [w for r in run for ln in r for w in ln.words]
if not words:
    print('NO WORDS')
    exit()

xmin = min(w.box.x0 for w in words)
xmax = max(w.box.x1 for w in words)
width = max(1e-9, xmax - xmin)
tol = max(4.0, 0.03 * width)

num_words = [w for w in words if _numeric_word(w) is not None]
centers = [w.box.x0 for w in num_words]
bands = _cluster_centers(centers, tol)
print('Bands:', bands)

columns = [
    type('Col', (), {'index': i, 'center': sum(b)/len(b), 'x0': min(b) - tol/2, 'x1': max(b) + tol/2, 'rows': {}})
    for i, b in enumerate(bands)
]
money_cols = [c.index for c in columns if c.index in [1, 2]]
print('money_cols:', money_cols)

leftmost_money_band = min(c.center for c in columns if c.index in money_cols)
desc_x1 = leftmost_money_band - tol
print('desc_x1:', desc_x1)

# occupancy
occupancy = {}
for r_i, r in enumerate(run):
    key = with_header + r_i
    row_map = {}
    for ln in r:
        for w in ln.words:
            if w.box.x0 < desc_x1:
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

# desc edge
leftmost = []
for key, row_map in occupancy.items():
    if key == with_header and has_header:
        continue
    if not any(i >= 0 and i in money_cols for i in row_map):
        print(f'Key {key}: no money cols')
        continue
    if not row_map.get(Table.DESCR):
        print(f'Key {key}: no DESCR')
        continue
    desc_texts = [tx for _, tx in row_map[Table.DESCR]]
    combined_desc = ' '.join(desc_texts).strip()
    if _is_summary_label(combined_desc):
        print(f'Key {key}: summary - {combined_desc[:60]}')
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
        print(f'Key {key}: desc_xs={desc_xs}, min={min(desc_xs)}, desc="{combined_desc[:60]}"')
        leftmost.append(min(desc_xs))
    else:
        print(f'Key {key}: no desc_xs, desc="{combined_desc[:60]}"')

print('Leftmost:', leftmost)
if not leftmost:
    print('NO LEFTMOST - returning None')
    exit()

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

data_rows_found = 0
for key in sorted(occupancy):
    if key == with_header and has_header:
        print(f'Key {key}: header row')
        continue
    result = is_data_row(key, occupancy[key])
    print(f'Key {key}: is_data_row={result}')
    if result:
        data_rows_found += 1

print(f'Data rows found: {data_rows_found}')
if data_rows_found == 0:
    print('NO DATA ROWS - returning None')