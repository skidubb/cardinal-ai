"""Configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

from ce_shared.env import find_and_load_dotenv


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    default_model: str = "claude-opus-4-6"
    judge_model: str = "claude-opus-4-6"
    judge_models: list[str] = [
        "claude-opus-4-6",
        "gpt-5.2",
        "gemini-3.1-pro-preview",
    ]
    project_root: Path = Path(__file__).resolve().parent.parent.parent

    model_config = {"env_prefix": "", "extra": "ignore"}


_settings: Settings | None = None
_env_loaded = False


def get_settings() -> Settings:
    global _settings, _env_loaded
    if not _env_loaded:
        find_and_load_dotenv(project="evals")
        _env_loaded = True
    if _settings is None:
        _settings = Settings()
    return _settings
