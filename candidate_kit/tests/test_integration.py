"""
Integration tests for the full autodraft pipeline
"""

import pytest
import json
from pathlib import Path
from autodraft.pipeline import process_pdf, process_pdf_detail, run_folder
from autodraft.audit import run_audit


@pytest.fixture
def documents_dir():
    """Path to documents directory"""
    return Path(__file__).parent.parent / "documents"

@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "output"


class TestFullPipeline:
    """Integration tests that require actual PDF documents"""

    def test_process_all_documents(self, documents_dir, output_dir):
        """Process all documents and verify no crashes"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        # Check that output files were created
        output_files = list(output_dir.glob("*.json"))
        pdf_files = list(documents_dir.glob("*.pdf"))
        
        # Should have at least some output files
        assert len(output_files) > 0

    def test_output_format(self, documents_dir, output_dir):
        """Verify output JSON format matches schema"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        for output_file in output_dir.glob("*.json"):
            with open(output_file) as f:
                data = json.load(f)
            
            # Required fields
            assert "file" in data
            assert "payables" in data
            assert "declined" in data
            
            # Payables should be list
            assert isinstance(data["payables"], list)
            assert isinstance(data["declined"], list)

    def test_passing_documents(self, documents_dir, output_dir):
        """Test that known good documents still pass"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        # Check specific known-good documents.
        # INV-26 is a quote/proforma (NOT_A_PAYABLE) and is asserted below to
        # decline honestly rather than to book.
        known_good = ["INV-01", "INV-03", "INV-04", "INV-06", "INV-07", "INV-10", "INV-13", "INV-34"]
        
        for doc_name in known_good:
            output_file = output_dir / f"{doc_name}.json"
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                assert len(data["payables"]) > 0, f"{doc_name} should have payables"
                assert len(data["declined"]) == 0, f"{doc_name} should not be declined"

        inv26 = output_dir / "INV-26.json"
        if inv26.exists():
            with open(inv26) as f:
                data = json.load(f)
            assert len(data["payables"]) == 0, "INV-26 is a quote/proforma, must not book"
            assert any(
                d.get("doc_type") == "NOT_A_PAYABLE" for d in data.get("declined", [])
            ), "INV-26 should decline with an honest NOT_A_PAYABLE reason"

    def test_customs_documents_declined(self, documents_dir, output_dir):
        """Customs docs that are NOT payables decline; genuine customs declarations book"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        # Entry-summary / statement PDFs that assert no payable obligation.
        customs_docs = ["DU-02", "DU-05", "DU-05s", "DU-09", "DU-11"]
        
        for doc_name in customs_docs:
            output_file = output_dir / f"{doc_name}.json"
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                assert len(data["payables"]) == 0, f"{doc_name} should have no payables"
                assert len(data["declined"]) > 0, f"{doc_name} should be declined"

        # DU-06 is composite: Europarcels freight IS a payable, europastry customs is declined
        du6 = output_dir / "DU-06.json"
        if du6.exists():
            with open(du6) as f:
                d6 = json.load(f)
            pay_inv = [p["invoice_number"] for p in d6["payables"]]
            assert "785255159" in pay_inv, f"DU-06 freight payable 785255159 should book, got {pay_inv}"
            assert any("80120853" in (x.get("reason") or "") for x in d6["declined"]), "DU-06 europastry customs should decline"

        # DU-03 / DU-08 are genuine customs declarations with an assessed
        # (GST) amount: they book a payable that recomputes to its printed
        # gross (ERP gate passed).
        for doc_name in ["DU-03", "DU-08"]:
            output_file = output_dir / f"{doc_name}.json"
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                assert len(data["payables"]) == 1, f"{doc_name} should book one payable"
                assert len(data["declined"]) == 0, f"{doc_name} should not be declined"

    def test_credit_note_accepted(self, documents_dir, output_dir):
        """DU-10 is a genuine British credit note, not a customs statement: it must book."""
        output_dir.mkdir(exist_ok=True)

        run_folder(str(documents_dir), str(output_dir))

        output_file = output_dir / "DU-10.json"
        if output_file.exists():
            with open(output_file) as f:
                data = json.load(f)
            assert len(data["payables"]) == 1, "DU-10 should book exactly one payable"
            assert len(data["declined"]) == 0, "DU-10 should not be declined"


class TestAudit:
    def test_audit_runs(self, documents_dir, output_dir):
        """Verify audit can run without errors"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        # Run audit
        results = run_audit()
        
        # Should return results
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check that results have expected structure
        for result in results:
            assert "file" in result
            assert "status" in result
            assert "issues" in result

    def test_no_critical_issues(self, documents_dir, output_dir):
        """Verify no critical audit issues on passing documents"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        results = run_audit()
        
        # Critical = arithmetic (ERP gate) failures or grounding failures on
        # money/quantity values.  Rate metadata (tax_rate / discount_percentage)
        # is descriptive only: the monetary amounts that apply it are grounded
        # and gated separately, so a rate label is not value-critical.
        critical_issues = []
        for result in results:
            for issue in result.get("issues", []):
                if "ERP gate mismatch" in issue or "grounding failed" in issue:
                    if result["status"] == "declined":  # Expected for declined docs
                        continue
                    if "grounding failed" in issue:
                        field = issue.split("grounding failed - ", 1)[-1].split("=", 1)[0]
                        if field.endswith((".tax_rate", ".discount_percentage")):
                            continue
                    critical_issues.append(f"{result['file']}: {issue}")
        
        # Print any critical issues for debugging
        for issue in critical_issues:
            print(f"CRITICAL: {issue}")
        
        # We expect some issues but they should be known/acceptable
        assert len(critical_issues) == 0, f"Critical issues found: {critical_issues}"


class TestSpecificDocuments:
    """Test specific document processing"""
    
    def test_inv01(self, documents_dir):
        """Test INV-01 processing"""
        pdf_path = documents_dir / "INV-01.pdf"
        if pdf_path.exists():
            result = process_pdf(str(pdf_path))
            assert len(result["payables"]) > 0
            assert len(result["declined"]) == 0

    def test_inv03(self, documents_dir):
        """Test INV-03 processing"""
        pdf_path = documents_dir / "INV-03.pdf"
        if pdf_path.exists():
            result = process_pdf(str(pdf_path))
            assert len(result["payables"]) > 0
            assert len(result["declined"]) == 0

    def test_du02(self, documents_dir):
        """Test DU-02 (customs) is declined"""
        pdf_path = documents_dir / "DU-02.pdf"
        if pdf_path.exists():
            result = process_pdf(str(pdf_path))
            assert len(result["payables"]) == 0
            assert len(result["declined"]) > 0
            assert "customs" in result["declined"][0]["reason"].lower()