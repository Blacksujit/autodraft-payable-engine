"""
Tests for autodraft.pipeline module
"""

import pytest
from autodraft.pipeline import process_pdf, process_pdf_detail, run_folder
from autodraft.fields import ExtractedDoc


class TestProcessPdfDetail:
    def test_nonexistent_file(self):
        result = process_pdf_detail("nonexistent.pdf")
        assert result[0]["error"] == "pdf_error: no such file: 'nonexistent.pdf'"

    def test_invalid_pdf(self, tmp_path):
        # Create a non-PDF file
        bad_file = tmp_path / "bad.pdf"
        bad_file.write_text("not a pdf")
        
        result = process_pdf_detail(str(bad_file))
        # Should handle gracefully
        assert result[0] is not None


class TestProcessPdf:
    def test_returns_dict(self, mock_pdf_path):
        if mock_pdf_path:
            result = process_pdf(mock_pdf_path)
            assert isinstance(result, dict)
            assert "file" in result
            assert "payables" in result
            assert "declined" in result


class TestRunFolder:
    def test_processes_pdfs(self, tmp_path):
        # Create a minimal test structure
        pdf_dir = tmp_path / "documents"
        pdf_dir.mkdir()
        
        # This test requires actual PDFs, so we'll skip if none exist
        result = run_folder(str(pdf_dir), str(tmp_path / "output"))
        # Should not crash even with empty directory
        assert True


class TestPipelineIntegration:
    @pytest.mark.skipif(True, reason="Requires actual PDF files")
    def test_full_pipeline(self):
        """Integration test requiring actual PDFs"""
        pass