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
        
        # Check specific known-good documents
        known_good = ["INV-01", "INV-03", "INV-04", "INV-06", "INV-07", "INV-10", "INV-26", "INV-34"]
        
        for doc_name in known_good:
            output_file = output_dir / f"{doc_name}.json"
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                assert len(data["payables"]) > 0, f"{doc_name} should have payables"
                assert len(data["declined"]) == 0, f"{doc_name} should not be declined"

    def test_customs_documents_declined(self, documents_dir, output_dir):
        """Test that customs documents are correctly declined"""
        output_dir.mkdir(exist_ok=True)
        
        run_folder(str(documents_dir), str(output_dir))
        
        customs_docs = ["DU-02", "DU-03", "DU-05", "DU-05s", "DU-06", "DU-08", "DU-09", "DU-10", "DU-11"]
        
        for doc_name in customs_docs:
            output_file = output_dir / f"{doc_name}.json"
            if output_file.exists():
                with open(output_file) as f:
                    data = json.load(f)
                assert len(data["payables"]) == 0, f"{doc_name} should have no payables"
                assert len(data["declined"]) > 0, f"{doc_name} should be declined"


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
        
        # Critical issues would be ERP gate failures or grounding failures
        critical_issues = []
        for result in results:
            for issue in result.get("issues", []):
                if "ERP gate mismatch" in issue or "grounding failed" in issue:
                    if result["status"] != "declined":  # Expected for declined docs
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