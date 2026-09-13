import sys, os
sys.path.insert(0, os.getcwd())
from autodraft.pipeline import process_pdf_detail
import autodraft.fields as F, autodraft.oracle as O, autodraft.resolve as R
from autodraft.fields import extract
from autodraft.structure import build_layout
from autodraft.ocr import ocr_words
from decimal import Decimal
import glob
def show(name, pages=2):
    lays=[]
    for i in range(1,pages+1):
        p=f".work/pages/{name}_p{i}.png"
        try: lays.append(build_layout(p,i-1,ocr_words(p)))
        except Exception as e: pass
    ext=F.extract(lays[0]) if lays else None
    # multi-page merge? just use pipeline path
    return
# use pipeline path
from autodraft.pipeline import process_pdf_detail
for name in ("INV-06","INV-04"):
    res, ext, raw, placement, note = process_pdf_detail(f'documents/{name}.pdf')
    print('====', name, 'placement=',placement,'note=',note)
    if ext:
        print('  gross',ext.gross,'tax_total',ext.tax_total,'disc',ext.discount_amount,'sub',ext.subtotal)
        print('  doc.taxes',[(t.tax_name,t.tax_rate,t.tax_amount) for t in ext.taxes])
        print('  lines',[(li.quantity,li.unit_price,li.total,li.tax_rate,li.tax_amount) for li in ext.line_items][:8])
    p=raw
    if p and not p.get('_declined'):
        import erp
        print('  keep erp_book', erp.erp_book(p)['will_book_gross'])
        print('  keep emitted gross', p.get('gross_total'),'sub',p.get('subtotal'),'tax',p.get('total_tax_amount'))
