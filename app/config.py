"""Configuration, driven by environment variables (see .env.example)."""
from __future__ import annotations

import os


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = "development"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    # Relative paths are resolved against Flask's instance/ folder.
    DATABASE = os.environ.get("DATABASE_PATH", "mrt.db")
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Manila")
    FLAT_FARE = int(os.environ.get("FLAT_FARE", "55"))

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    # Prefer ADMIN_PASSWORD_HASH (werkzeug hash). ADMIN_PASSWORD is hashed at startup.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    CSRF_ENABLED = True
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 300

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    APP_ENV = "testing"
    TESTING = True
    CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "test-password"
    ADMIN_PASSWORD_HASH = ""


class ProductionConfig(Config):
    APP_ENV = "production"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)

    @classmethod
    def validate(cls) -> None:
        problems = []
        if cls.SECRET_KEY == "dev-only-change-me":
            problems.append("SECRET_KEY must be set")
        if not cls.ADMIN_PASSWORD_HASH and os.environ.get("ADMIN_PASSWORD") in (None, "", "password"):
            problems.append("ADMIN_PASSWORD_HASH (or a non-default ADMIN_PASSWORD) must be set")
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
