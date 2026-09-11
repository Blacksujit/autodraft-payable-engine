import json, os, sys
sys.path.insert(0, 'D:/candidate_kit/candidate_kit')
from erp import erp_book

out_dir = 'D:/candidate_kit/candidate_kit/output'
results = []
for fname in sorted(os.listdir(out_dir)):
    if not fname.endswith('.json'): continue
    data = json.load(open(os.path.join(out_dir, fname)))
    for i, p in enumerate(data.get('payables', [])):
        try:
            result = erp_book(p)
            erp_gross = result['will_book_gross']
            doc_gross = float(str(p.get('gross_total', '0')).replace(',',''))
            match = abs(erp_gross - doc_gross) < 0.005
            status = 'PASS' if match else 'FAIL'
            results.append((fname, i, status, erp_gross, doc_gross, result['currency']))
        except Exception as e:
            results.append((fname, i, f'ERROR:{e}', 0, 0, ''))

passes = [r for r in results if r[2] == 'PASS']
fails  = [r for r in results if r[2] == 'FAIL']
errors = [r for r in results if r[2].startswith('ERROR')]

print(f'=== ERP Validation ===')
print(f'Payables validated: {len(results)}')
print(f'PASS: {len(passes)}, FAIL: {len(fails)}, ERROR: {len(errors)}')
print()
for r in results:
    fname, i, status, erp_gross, doc_gross, currency = r
    delta = erp_gross - doc_gross if isinstance(erp_gross, float) else 0
    flag = 'OK' if status == 'PASS' else 'XX'
    print(f'{flag} {status:6} {fname}[{i}]: erp={erp_gross:.2f} doc={doc_gross:.2f} delta={delta:+.4f} {currency}')
