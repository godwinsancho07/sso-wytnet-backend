from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Resolve .env path relative to the project root (parent of /backend).
# Lets `alembic upgrade head` work whether you run it from / or /backend.
_BACKEND_DIR = Path(__file__).resolve().parents[2]   # .../backend
_PROJECT_ROOT = _BACKEND_DIR.parent                  # .../sso
_ENV_FILES = [_BACKEND_DIR / ".env", _PROJECT_ROOT / ".env"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in _ENV_FILES),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SSO Identity Provider"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change_me_in_production_use_a_long_random_string"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://sso:sso_secret@localhost:5432/sso_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT / OIDC
    private_key_path: str = "keys/private.pem"
    public_key_path: str = "keys/public.pem"
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    id_token_expire_minutes: int = 60
    auth_code_expire_minutes: int = 10
    oidc_issuer: str = "http://localhost:8000"

    # Session
    session_expire_days: int = 7
    secure_cookies: bool = False

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@sso.local"
    smtp_tls: bool = False

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    # Social: Google
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Social: GitHub
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    # Social: Microsoft
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    microsoft_tenant_id: str = "common"
    microsoft_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"

    # Social: LinkedIn
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_redirect_uri: str = "http://localhost:8000/auth/linkedin/callback"

    # Rate limiting
    rate_limit_login: str = "10/minute"
    rate_limit_register: str = "5/minute"
    rate_limit_password_reset: str = "3/minute"

    # Razorpay
    razorpay_key_id: str = "rzp_live_RMxf287wX4f7FQ"
    razorpay_key_secret: str = "1MLyIthYIvhJ7MMNWRvZ2qRO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
