"""
conftest.py - Shared pytest fixtures

Provides reusable fixtures for all agent and pipeline tests:
    - sample_input_path: path to case_001_clean (clean, all-compliant bundle)
    - run_dir: temporary run directory (auto-cleaned after test)
    - mock_context: a pre-built ContextPacket for unit tests that skip Agent A
"""
import pytest
from pathlib import Path

SAMPLE_DOCS = Path(__file__).parent.parent / "data" / "sample_documents"


@pytest.fixture
def sample_input_path() -> Path:
    """Returns path to the clean, all-compliant test bundle."""
    return SAMPLE_DOCS / "case_001_clean"


@pytest.fixture
def sanctions_hit_path() -> Path:
    """Returns path to the sanctions-hit test bundle."""
    return SAMPLE_DOCS / "case_003_sanctions_hit"


@pytest.fixture
def invoice_mismatch_path() -> Path:
    """Returns path to the invoice-mismatch test bundle."""
    return SAMPLE_DOCS / "case_002_invoice_mismatch"


@pytest.fixture
def tmp_run_dir(tmp_path) -> Path:
    """Returns a temporary run directory cleaned up after each test."""
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()
    return run_dir
