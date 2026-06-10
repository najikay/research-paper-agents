"""
tests/test_config.py
====================
Unit tests for src/config.py constants and validate_config().
"""

from __future__ import annotations

import pytest

from src.config import (
    AGENT_MAX_ITER,
    PAPER_MAX_PAGES,
    PAPER_MIN_PAGES,
    PAPER_TARGET_PAGES,
    PROJECT_ROOT,
    PROTECTED_FILES,
    WRITABLE_DIRS,
    validate_config,
)


def test_project_root_exists():
    """PROJECT_ROOT must point to a real directory on disk."""
    assert PROJECT_ROOT.is_dir(), f"PROJECT_ROOT={PROJECT_ROOT} is not a directory"


def test_protected_files_contains_critical_paths():
    """PROTECTED_FILES must include the static-only tex files (cover + main)."""
    for expected in (
        "latex/chapters/cover.tex",
        "latex/main.tex",
    ):
        assert expected in PROTECTED_FILES, f"{expected!r} missing from PROTECTED_FILES"


def test_ch01_ch04_not_in_protected_files():
    """ch01_intro.tex and ch04_slam.tex must NOT be in PROTECTED_FILES (they are now agent-written)."""
    assert "latex/chapters/ch01_intro.tex" not in PROTECTED_FILES, (
        "ch01_intro.tex should be dynamic; remove it from PROTECTED_FILES"
    )
    assert "latex/chapters/ch04_slam.tex" not in PROTECTED_FILES, (
        "ch04_slam.tex should be dynamic; remove it from PROTECTED_FILES"
    )


def test_protected_files_contains_env():
    """.env must be listed in PROTECTED_FILES."""
    assert ".env" in PROTECTED_FILES


def test_writable_dirs():
    """latex, outputs, and docs must all be in WRITABLE_DIRS."""
    for d in ("latex", "outputs", "docs"):
        assert d in WRITABLE_DIRS, f"{d!r} missing from WRITABLE_DIRS"


def test_agent_max_iter_keys():
    """All agent keys must be present in AGENT_MAX_ITER."""
    expected_keys = {
        "research_director",
        "deep_researcher",
        "data_visualizer",
        "hebrew_writer",
        "latex_author",
        "biology_expert",
        "vision_ai_expert",
        "physics_expert",
        "algorithms_expert",
        "aerospace_marine_expert",
        "signal_processing_expert",
        "control_systems_expert",
        "ml_expert",
    }
    assert expected_keys.issubset(AGENT_MAX_ITER.keys()), (
        f"Missing keys: {expected_keys - set(AGENT_MAX_ITER.keys())}"
    )


def test_paper_page_targets():
    """PAPER_MIN_PAGES=25, PAPER_MAX_PAGES=30, PAPER_TARGET_PAGES=28."""
    assert PAPER_MIN_PAGES == 25
    assert PAPER_MAX_PAGES == 30
    assert PAPER_TARGET_PAGES == 28


def test_validate_config_passes_with_deepseek(monkeypatch):
    """validate_config() should not raise when DEEPSEEK_API_KEY and SERPER_API_KEY are set."""
    import os
    monkeypatch.setenv("ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-serper-key")

    import src.config as cfg
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "sk-test-deepseek-key")

    # Should not raise
    validate_config()


def test_validate_config_fails_missing_deepseek(monkeypatch):
    """validate_config() must raise EnvironmentError when ACTIVE_PROVIDER=deepseek and key absent."""
    import src.config as cfg
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("SERPER_API_KEY", "test-serper-key")

    with pytest.raises(EnvironmentError):
        validate_config()


def test_validate_config_fails_missing_serper(monkeypatch):
    """validate_config() must raise EnvironmentError when SERPER_API_KEY is absent."""
    import src.config as cfg
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "sk-test-deepseek-key")
    # Ensure os.getenv("SERPER_API_KEY") returns ""
    monkeypatch.setenv("SERPER_API_KEY", "")

    with pytest.raises(EnvironmentError):
        validate_config()
