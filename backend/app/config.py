"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CodeCourt backend."""

    GITHUB_TOKEN: str = ""
    DATABASE_URL: str = "sqlite:///./codecourt.db"
    CACHE_DIR: str = "../cache"
    MAX_REPO_SIZE_MB: int = 500
    GIT_CLONE_TIMEOUT_SEC: int = 300
    DEFAULT_MAX_COMMITS: int = 5000
    MAX_FILES_PER_COMMIT: int = 100
    MAX_FILE_DIFF_LINES: int = 5000
    COMMIT_MEANINGFUL_CAP: int = 400
    TRIVIAL_COMMIT_THRESHOLD: int = 3
    LIZARD_MAX_FILE_BYTES: int = 200000
    MIN_ADDED_LINES_IN_FUNCTION: int = 2
    FUNCTION_WEIGHT_CAP: int = 100
    MIN_FUNCTIONS_FOR_QUALITY: int = 5
    QUALITY_MOD_MIN: float = 0.7
    QUALITY_MOD_MAX: float = 1.2
    MAX_BLAME_FILES: int = 500
    MAX_BLAME_FILE_BYTES: int = 300000
    BLAME_TIMEOUT_SEC: int = 30
    BLAME_WORKERS: int = 4
    MIN_BLAME_COVERAGE: float = 0.85
    SURVIVAL_SHRINK_K: int = 20
    MIN_LINES_FOR_SURVIVAL: int = 30
    GITHUB_API_BASE: str = "https://api.github.com"
    HTTP_TIMEOUT_SEC: int = 15
    MAX_PRS: int = 300
    MAX_REVIEW_PRS: int = 100
    MAX_ISSUES: int = 500
    MAX_LIST_PAGES: int = 10
    MAX_COMMIT_LOOKUP_PAGES: int = 10
    MIN_PRS_FOR_REVIEW: int = 3
    MIN_ISSUES_FOR_SIGNAL: int = 3
    MIN_SPAN_WEEKS: int = 3
    MAX_CONCURRENT_ANALYSES: int = 2
    MAX_QUEUED_ANALYSES: int = 20
    ANALYSIS_TIMEOUT_SEC: int = 900
    ANALYSIS_TTL_HOURS: int = 24
    PIPELINE_VERSION: str = "1"
    MAX_ANALYZE_PER_MINUTE_PER_IP: int = 6
    API_MAX_COMMITS: int = 20000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
