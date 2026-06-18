"""Shared project configuration."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL: str = os.getenv("MODEL", "gpt-5.4-nano")
    RUN_DIR: Path = BASE_DIR / "runs"
    POLICIES_DIR: Path = BASE_DIR / "policies"
    SCHEMAS_DIR: Path = BASE_DIR / "schemas"
    SANCTIONS_DIR: Path = BASE_DIR / "data" / "sanctions_lists"
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "data" / "sample_documents"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_TOKENS: int = _int_env("MAX_TOKENS", 900)
    SANCTIONS_MATCH_THRESHOLD: int = _int_env("SANCTIONS_MATCH_THRESHOLD", 85)
    # OCR settings (stretch goal — requires PyMuPDF + Tesseract)
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() != "false"
    OCR_DPI: int = _int_env("OCR_DPI", 200)
    OCR_TEXT_QUALITY_THRESHOLD: float = _float_env("OCR_TEXT_QUALITY_THRESHOLD", 0.65)


settings = Settings()