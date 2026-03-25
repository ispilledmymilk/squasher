# backend/utils/config.py

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    # Environment: development | production
    ENV = os.getenv("ENV", "development").lower()
    IS_PRODUCTION = ENV == "production"

    # API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

    # Optional: require Authorization: Bearer <token> on API routes (extension + CI)
    API_SECRET_KEY = os.getenv("API_SECRET_KEY", "").strip()

    # CORS: comma-separated origins; empty in production = deny browser CORS (use extension only)
    # Example: CORS_ORIGINS=http://localhost:5173,https://your-app.com
    _cors_raw = os.getenv("CORS_ORIGINS", "").strip()
    CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

    # Do not return raw exception messages to clients in production
    EXPOSE_ERROR_DETAILS = os.getenv("EXPOSE_ERROR_DETAILS", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # Paths - BASE_DIR is codedecay/
    _backend_dir = Path(__file__).resolve().parent.parent
    BASE_DIR = _backend_dir.parent
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "data" / "vectordb"))
    METRICS_DB_PATH = os.getenv("METRICS_DB_PATH", str(BASE_DIR / "data" / "metrics.db"))
    MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "data" / "models"))

    # Analysis / QA limits (production guardrails)
    COMPLEXITY_THRESHOLD = 10
    CHANGE_FREQUENCY_WINDOW = 90  # days
    PREDICTION_HORIZON = 90  # days
    MAX_PRE_COMMIT_FILES = int(os.getenv("MAX_PRE_COMMIT_FILES", "200"))
    MAX_FILE_BYTES_FOR_SCAN = int(
        os.getenv("MAX_FILE_BYTES_FOR_SCAN", str(2 * 1024 * 1024))
    )  # 2 MiB default
    MAX_PATH_LENGTH = int(os.getenv("MAX_PATH_LENGTH", "4096"))

    # GitHub remote analysis (clone / raw fetch); bounded to avoid abuse
    GITHUB_CACHE_DIR = os.getenv(
        "GITHUB_CACHE_DIR",
        str(BASE_DIR / "data" / "github_cache"),
    )
    MAX_GITHUB_ANALYSIS_FILES = int(os.getenv("MAX_GITHUB_ANALYSIS_FILES", "60"))
    GITHUB_CLONE_TIMEOUT_SEC = int(os.getenv("GITHUB_CLONE_TIMEOUT_SEC", "120"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        os.makedirs(cls.VECTOR_DB_PATH, exist_ok=True)
        os.makedirs(cls.MODEL_PATH, exist_ok=True)
        parent = os.path.dirname(cls.METRICS_DB_PATH)
        if parent:
            os.makedirs(parent, exist_ok=True)
        os.makedirs(cls.GITHUB_CACHE_DIR, exist_ok=True)

config = Config()
config.ensure_directories()
