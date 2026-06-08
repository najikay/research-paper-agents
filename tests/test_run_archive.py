"""
tests/test_run_archive.py
=========================
Unit tests for the helper functions in main.py:
  _topic_slug(), create_run_folder(), archive_run().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main import _topic_slug, archive_run, create_run_folder


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
# archive_run helpers
# ---------------------------------------------------------------------------

def _setup_project_dirs(tmp_path: Path) -> None:
    """Create the minimal project structure for archive_run tests."""
    (tmp_path / "latex" / "figures").mkdir(parents=True)
    (tmp_path / "latex" / "chapters").mkdir(parents=True)
    (tmp_path / "outputs").mkdir(parents=True)
    # Minimal main.tex
    (tmp_path / "latex" / "main.tex").write_text("% main\n", encoding="utf-8")


def test_archive_run_copies_figures(tmp_path, monkeypatch):
    """archive_run must copy PNG figures into run_folder/figures/."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)
    (tmp_path / "latex" / "figures" / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)

    assert (run_folder / "figures" / "fig.png").exists()


def test_archive_run_copies_outputs(tmp_path, monkeypatch):
    """archive_run must copy agent .md output files into run_folder/outputs/."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)
    (tmp_path / "outputs" / "paper_outline.md").write_text("# Outline\n", encoding="utf-8")

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)

    assert (run_folder / "outputs" / "paper_outline.md").exists()


def test_archive_run_copies_pdf(tmp_path, monkeypatch):
    """archive_run must copy the PDF to run_folder/paper.pdf when provided."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)
    pdf_path = tmp_path / "outputs" / "NavigatorCrew_paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=pdf_path)

    assert (run_folder / "paper.pdf").exists()


def test_archive_run_no_pdf(tmp_path, monkeypatch):
    """archive_run must not crash and must not create paper.pdf when pdf_path=None."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)  # must not raise

    assert not (run_folder / "paper.pdf").exists()


def test_archive_run_writes_manifest(tmp_path, monkeypatch):
    """archive_run must write run_manifest.txt containing 'NavigatorCrew'."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)

    manifest_path = run_folder / "run_manifest.txt"
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    assert "NavigatorCrew" in content


def test_archive_run_manifest_lists_figures(tmp_path, monkeypatch):
    """run_manifest.txt must include the name of each copied figure."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)
    fig_name = "fig_trajectory_3d.png"
    (tmp_path / "latex" / "figures" / fig_name).write_bytes(b"\x89PNG\r\n\x1a\n")

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)

    manifest = (run_folder / "run_manifest.txt").read_text(encoding="utf-8")
    assert fig_name in manifest


def test_archive_run_copies_latex_source(tmp_path, monkeypatch):
    """archive_run must copy latex/main.tex into run_folder/latex/main.tex."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    _setup_project_dirs(tmp_path)

    run_folder = tmp_path / "run_test"
    run_folder.mkdir()
    archive_run(run_folder, pdf_path=None)

    assert (run_folder / "latex" / "main.tex").exists()
