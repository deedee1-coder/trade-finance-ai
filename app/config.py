"""Shared project settings."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
SAMPLE_DOCUMENTS_DIR = DATA_DIR / "sample_documents"
RUNS_DIR = BASE_DIR / "runs"
POLICIES_DIR = BASE_DIR / "policies"
