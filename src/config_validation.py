"""
src/config_validation.py
=========================
Config validation, embedder config, and self-test for NavigatorCrew.
"""

from __future__ import annotations

import os

import src.config as _cfg


def _openai_key_is_real() -> bool:
    """Return True only if OPENAI_API_KEY looks like an actual key."""
    return bool(_cfg.OPENAI_API_KEY) and _cfg.OPENAI_API_KEY.startswith("sk-")


def get_embedder_config() -> dict | None:
    """Return the ChromaDB embedder config, or None if no valid embedder."""
    if _openai_key_is_real():
        _cfg.logger.info("Embedder: OpenAI text-embedding-3-small")
        return {
            "provider": "openai",
            "config": {
                "model": _cfg.EMBEDDING_MODEL,
                "api_key": _cfg.OPENAI_API_KEY,
            },
        }
    _cfg.logger.warning(
        "No valid embedder available (OPENAI_API_KEY not set or placeholder). "
        "Crew memory will be disabled."
    )
    return None


def validate_config() -> None:
    """Validate required API keys for the active provider."""
    missing: list[str] = []
    if _cfg.ACTIVE_PROVIDER == "deepseek":
        if not _cfg.DEEPSEEK_API_KEY:
            missing.append("  * DEEPSEEK_API_KEY: Get yours at platform.deepseek.com")
    else:
        if not _cfg.ANTHROPIC_API_KEY:
            missing.append("  * ANTHROPIC_API_KEY: Get yours at console.anthropic.com")
    if not os.getenv("SERPER_API_KEY", ""):
        missing.append("  * SERPER_API_KEY: Free key at serper.dev")
    if missing:
        raise OSError(
            "\n\n[NavigatorCrew] Missing required environment variables:\n"
            + "\n".join(missing)
            + "\n\nCopy .env.example -> .env and fill in the values.\n"
        )
    _cfg.logger.success(f"Config validation passed. Provider={_cfg.ACTIVE_PROVIDER}.")
