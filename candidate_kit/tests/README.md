# Autodraft Test Suite

Comprehensive test suite for the autodraft project - a system that converts supplier PDF invoices into ERP-bookable payable records.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_geom.py             # Geometry primitives (Box, Word, Line, clustering)
├── test_normalize.py        # Number/date/currency normalization
├── test_structure.py        # PDF layout analysis (tables, columns, regions)
├── test_fields.py           # Field extraction (header, line items, taxes, totals)
├── test_classify.py         # Document classification (invoice/credit/customs/quote)
├── test_resolve.py          # Master data resolution (suppliers, buyers, taxes, POs)
├── test_oracle.py           # ERP gate validation and payable assembly
├── test_pipeline.py         # Full pipeline integration
├── test_audit.py            # Fidelity auditing (ERP gate, grounding, codes)
└── test_integration.py      # Full pipeline tests with real documents
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_geom.py -v

# Run with coverage
python -m pytest tests/ --cov=autodraft --cov-report=html

# Run integration tests (requires PDF documents)
python -m pytest tests/test_integration.py -v

# Run with verbose output
python -m pytest tests/ -v --tb=short
```

## Test Categories

### Unit Tests (Fast, No External Dependencies)
- `test_geom.py` - Box, Word, Line, clustering algorithms
- `test_normalize.py` - Number parsing, date parsing, currency detection
- `test_structure.py` - Layout analysis, table detection
- `test_fields.py` - Field extraction, regex patterns, line items
- `test_classify.py` - Document type classification
- `test_resolve.py` - Master data matching
- `test_oracle.py` - ERP gate, payable variants
- `test_pipeline.py` - Pipeline orchestration
- `test_audit.py` - Fidelity checks

### Integration Tests (Requires PDF Documents)
- `test_integration.py` - Full pipeline with real PDFs

## Fixtures

Defined in `conftest.py`:
- `sample_words` - Sample OCR word data
- `sample_extracted_doc` - Pre-populated ExtractedDoc
- `mock_pdf_path` - Path to a test PDF (if available)

## Running in CI/CD

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install -e ".[dev]"
    python -m pytest tests/ --cov=autodraft --cov-report=xml
```

## Test Data

Tests use the real PDF documents in `../documents/` for integration testing. The documents include:
- INV-* : Standard invoices (some pass, some fail)
- DU-* : Customs declarations (should be declined)
- HLD-* : Various document types

## Adding New Tests

1. Create test file in `tests/test_<module>.py`
2. Follow naming convention: `Test<ClassName>` for classes, `test_<function>` for functions
3. Use fixtures from `conftest.py`
3. Add integration tests to `test_integration.py` if they need real PDFs