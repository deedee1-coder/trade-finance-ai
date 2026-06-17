import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL: str = os.getenv("MODEL", "gpt-5.4-nano")
    RUN_DIR: Path = BASE_DIR / "runs"
    POLICIES_DIR: Path = BASE_DIR / "policies"
    SCHEMAS_DIR: Path = BASE_DIR / "schemas"
    SANCTIONS_DIR: Path = BASE_DIR / "data" / "sanctions_lists"
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "data" / "sample_documents"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_TOKENS: int = 4096
    SANCTIONS_MATCH_THRESHOLD: int = 85


settings = Settings()
