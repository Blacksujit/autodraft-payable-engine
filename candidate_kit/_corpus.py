from autodraft.pipeline import process_pdf
from pathlib import Path
docs = sorted(Path('documents').glob('*.pdf'))
ok = declined = errors = 0
lines = []
for d in docs:
    r = process_pdf(str(d))
    if 'error' in r:
        errors += 1
        lines.append(d.name + ': ERROR ' + str(r['error']))
    elif r.get('payables'):
        ok += 1
        p = r['payables'][0]
        lines.append(d.name + ': PASS gross=' + str(p.get('gross_total')) + ' inv=' + str(p.get('invoice_number')))
    else:
        declined += 1
        lines.append(d.name + ': DECLINED ' + str(r.get('declined',[{}])[0].get('reason',''))[:70])
print('PASS/declined/errors:', ok, declined, errors, 'of', len(docs))
print('\n'.join(lines))
