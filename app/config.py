from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, *, minimum: int = 1) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_base_url: str
    secure_cookies: bool
    enable_dev_login: bool
    password_reset_ttl_minutes: int
    mail_mode: str
    mail_from: str
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_tls: bool
    smtp_use_ssl: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_secure = app_env == "production"

    return Settings(
        app_env=app_env,
        app_base_url=os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        secure_cookies=_as_bool(os.getenv("SECURE_COOKIES"), default_secure),
        enable_dev_login=_as_bool(os.getenv("ENABLE_DEV_LOGIN"), False),
        password_reset_ttl_minutes=_as_int(
            os.getenv("PASSWORD_RESET_TTL_MINUTES"), 30, minimum=5
        ),
        mail_mode=os.getenv("MAIL_MODE", "console").strip().lower(),
        mail_from=os.getenv("MAIL_FROM", "WikiDev <no-reply@wikidev.local>"),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=_as_int(os.getenv("SMTP_PORT"), 587),
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_use_tls=_as_bool(os.getenv("SMTP_USE_TLS"), True),
        smtp_use_ssl=_as_bool(os.getenv("SMTP_USE_SSL"), False),
    )
