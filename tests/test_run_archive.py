"""
tests/test_run_archive.py
=========================
Unit tests for the helper functions in main.py:
  _topic_slug(), create_run_folder(), finalize_run().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main import _topic_slug, create_run_folder, finalize_run


# ---------------------------------------------------------------------------
# _topic_slug
# ---------------------------------------------------------------------------

def test_topic_slug_basic():
    """'Bat-Inspired Navigation' must produce 'bat-inspired-navigation'."""
    assert _topic_slug("Bat-Inspired Navigation") == "bat-inspired-navigation"


def test_topic_slug_special_chars():
    """Special characters (parens, ampersand) must be replaced with hyphens."""
    slug = _topic_slug("SLAM & EKF (2026)")
    assert "(" not in slug
    assert ")" not in slug
    assert "&" not in slug
    assert "slam" in slug
    assert "ekf" in slug
    assert "2026" in slug


def test_topic_slug_max_length():
    """Very long topics must be truncated to at most 40 characters."""
    long_topic = "A" * 100 + " very long topic with many words and letters"
    slug = _topic_slug(long_topic)
    assert len(slug) <= 40


def test_topic_slug_strips_leading_trailing_hyphens():
    """Slug must not start or end with a hyphen."""
    slug = _topic_slug("  ---Topic With Spaces---  ")
    assert not slug.startswith("-")
    assert not slug.endswith("-")


# ---------------------------------------------------------------------------
# create_run_folder
# ---------------------------------------------------------------------------

def test_create_run_folder_creates_dir(tmp_path, monkeypatch):
    """create_run_folder must create the run directory and return its Path."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    folder = create_run_folder("Test Topic")

    assert folder.exists()
    assert folder.is_dir()
    assert "test-topic" in folder.name


def test_create_run_folder_versioning(tmp_path, monkeypatch):
    """Calling create_run_folder twice on the same day must produce a -v2 suffix."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    folder1 = create_run_folder("Version Test")
    folder2 = create_run_folder("Version Test")

    assert folder1 != folder2
    assert folder1.exists()
    assert folder2.exists()
    assert "-v2" in folder2.name


def test_create_run_folder_triple_versioning(tmp_path, monkeypatch):
    """Three calls on the same day must produce -v3 on the third call."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    folder1 = create_run_folder("Triple Test")
    folder2 = create_run_folder("Triple Test")
    folder3 = create_run_folder("Triple Test")

    assert "-v3" in folder3.name
    assert folder3.exists()


# ---------------------------------------------------------------------------
# finalize_run helpers
# ---------------------------------------------------------------------------

def _setup_run_dirs(run_folder: Path) -> None:
    """Create the minimal run folder structure expected by finalize_run."""
    (run_folder / "latex" / "figures").mkdir(parents=True)
    (run_folder / "latex" / "chapters").mkdir(parents=True)
    (run_folder / "outputs").mkdir(parents=True, exist_ok=True)


def test_finalize_run_moves_outputs(tmp_path, monkeypatch):
    """finalize_run must move agent .md files from outputs/current/ into run_folder/outputs/."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    # Staging directory is outputs/current/
    staging = tmp_path / "outputs" / "current"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "paper_outline.md").write_text("# Outline\n", encoding="utf-8")

    finalize_run(run_folder)

    assert (run_folder / "outputs" / "paper_outline.md").exists()


def test_finalize_run_cleans_staging(tmp_path, monkeypatch):
    """finalize_run must remove the staging directory after moving files."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    staging = tmp_path / "outputs" / "current"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "research_briefs.md").write_text("# Briefs\n", encoding="utf-8")

    finalize_run(run_folder)

    assert not staging.exists(), "Staging directory must be removed after finalize_run"


def test_finalize_run_no_crash_without_staging(tmp_path, monkeypatch):
    """finalize_run must not crash when the staging directory does not exist."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    # No staging directory — must not raise
    finalize_run(run_folder)

    assert (run_folder / "run_manifest.txt").exists()


def test_finalize_run_writes_manifest(tmp_path, monkeypatch):
    """finalize_run must write run_manifest.txt containing 'NavigatorCrew'."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    finalize_run(run_folder)

    manifest_path = run_folder / "run_manifest.txt"
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    assert "NavigatorCrew" in content


def test_finalize_run_manifest_lists_figures(tmp_path, monkeypatch):
    """run_manifest.txt must include the name of each figure in run_folder/latex/figures/."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    fig_name = "fig_trajectory_3d.png"
    (run_folder / "latex" / "figures" / fig_name).write_bytes(b"\x89PNG\r\n\x1a\n")

    finalize_run(run_folder)

    manifest = (run_folder / "run_manifest.txt").read_text(encoding="utf-8")
    assert fig_name in manifest


def test_finalize_run_latex_in_run_folder(tmp_path, monkeypatch):
    """The run folder must contain latex/ as the primary LaTeX source (set up by setup_run_latex).
    finalize_run must leave it untouched.
    """
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)
    # Simulate that setup_run_latex already created the latex tree in run_folder
    (run_folder / "latex" / "main.tex").write_text("% main\n", encoding="utf-8")

    finalize_run(run_folder)

    assert (run_folder / "latex").exists(), (
        "latex/ must remain in the run folder after finalize_run"
    )
    assert (run_folder / "latex" / "main.tex").exists()
