import json
from erp import erp_book

files = ['INV-10', 'INV-11', 'INV-13', 'INV-14', 'INV-15', 'INV-16']
expected = {
    'INV-10': (594.30, 'EUR'),
    'INV-11': (83.21, 'EUR'),
    'INV-13': (152587.46, 'EUR'),
    'INV-14': (29253.72, 'GBP'),
    'INV-15': (29253.72, 'GBP'),
    'INV-16': (26.47, 'EUR'),
}

for f in files:
    with open('output/' + f + '.json', encoding='utf-8') as fh:
        data = json.load(fh)
    for i, p in enumerate(data['payables']):
        result = erp_book(p)
        exp_gross, exp_curr = expected[f]
        erp_gross = result['will_book_gross']
        erp_curr = result['currency']
        match = 'OK' if abs(erp_gross - exp_gross) < 0.005 else 'FAIL'
        print(f + '[' + str(i) + ']: ERP=' + str(erp_gross) + ' ' + erp_curr + '  expected=' + str(exp_gross) + ' ' + exp_curr + '  ' + match)
