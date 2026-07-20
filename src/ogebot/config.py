"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed configuration for the bot.

    Values are read from environment variables first, then from a local ``.env``
    file. See ``.env.example`` for the full list of supported options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Telegram ---
    bot_token: str = Field(..., description="Telegram Bot API token from @BotFather")

    # --- Database ---
    # Default: local SQLite file (zero-config). Switch to Postgres by setting
    # DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/ogebot
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ogebot.db",
        description="Async SQLAlchemy database URL.",
    )
    # Automatically create tables on startup (handy for SQLite / quick start).
    # Set to False in production and rely on Alembic migrations instead.
    init_db_on_startup: bool = Field(default=True)
    sql_echo: bool = Field(default=False, description="Log every SQL statement.")

    # --- FSM storage ---
    # When a redis_url is provided, an aiogram RedisStorage is used so that user
    # progress survives restarts; otherwise an in-memory storage is used.
    redis_url: str | None = Field(default=None)

    # --- Access control ---
    admin_ids: list[int] = Field(
        default_factory=list,
        description="Telegram user IDs allowed to run admin commands.",
    )

    # --- Data ---
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory with YAML task banks used by the seeder and /reload.",
    )

    # --- Exam behaviour ---
    # Show whether an answer was right immediately after it is submitted.
    # Set to False to emulate a real exam (score revealed only at the end).
    immediate_feedback: bool = Field(default=True)

    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False, description="Emit structured JSON logs.")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        """Allow ADMIN_IDS to be given as a comma-separated string."""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [int(part) for part in value.replace(" ", "").split(",") if part]
        return value

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
