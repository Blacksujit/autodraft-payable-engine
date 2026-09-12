"""
Tests for autodraft.classify module
"""

import pytest
from autodraft.classify import decide
from autodraft.fields import ExtractedDoc


class TestDecide:
    def test_credit_memo_detection(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Credit Note for Invoice 123")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CREDIT_MEMO"
        assert invoice_type == "CREDIT_MEMO"
        assert decline_reason == ""

    def test_credit_memo_german(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Gutschrift über 100 EUR")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CREDIT_MEMO"
        assert invoice_type == "CREDIT_MEMO"

    def test_credit_memo_spanish(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Nota de crédito 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CREDIT_MEMO"
        assert invoice_type == "CREDIT_MEMO"

    def test_customs_detection(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Customs Declaration 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CUSTOMS_INVOICE"
        assert invoice_type == "INVOICE"
        assert decline_reason == "customs_statement"

    def test_customs_consolidated(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Consolidated Invoice for Customs")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CUSTOMS_INVOICE"
        assert decline_reason == "customs_statement"

    def test_quote_detection(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Quotation for services")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "NOT_A_PAYABLE"
        assert invoice_type == "QUOTE"
        assert decline_reason == "quote_or_proforma"

    def test_proforma_detection(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Proforma Invoice 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "NOT_A_PAYABLE"
        assert decline_reason == "quote_or_proforma"

    def test_delivery_note(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Delivery Note 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "NOT_A_PAYABLE"
        assert decline_reason == "quote_or_proforma"

    def test_utility_reimbursement(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Utility reimburse for condenser")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "NOT_A_PAYABLE"
        assert invoice_type == "UTILITY_REIMBURSEMENT"
        assert decline_reason == "utility_reimbursement"

    def test_tax_invoice(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Tax Invoice 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert invoice_type == "TAX_INVOICE"
        assert doc_type == "INVOICE"

    def test_standard_invoice(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Invoice 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "INVOICE"
        assert invoice_type == "INVOICE"
        assert decline_reason == ""

    def test_empty_text(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "INVOICE"
        assert invoice_type == "INVOICE"

    def test_storno(self):
        doc = ExtractedDoc(path="test.pdf", page_index=0, page_text="Storno Rechnung 12345")
        doc_type, invoice_type, decline_reason = decide(doc)
        assert doc_type == "CREDIT_MEMO"
        assert invoice_type == "CREDIT_MEMO"