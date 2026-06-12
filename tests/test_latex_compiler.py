"""
tests/test_latex_compiler.py
=============================
Tests for validate_and_fix_chapters and compile_pdf in src/pipeline/latex_compiler.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from loguru import logger

from src.pipeline.latex_compiler import (
    EXPECTED_CHAPTERS,
    compile_pdf,
    validate_and_fix_chapters,
)


@pytest.fixture
def log_sink():
    """Capture loguru messages into a list for assertion."""
    messages: list[str] = []
    handler_id = logger.add(lambda m: messages.append(m.record["message"]), level="DEBUG")
    yield messages
    logger.remove(handler_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chapters_dir(run_folder: Path, files: dict[str, str] | None = None) -> Path:
    chapters = run_folder / "latex" / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    if files:
        for name, content in files.items():
            (chapters / name).write_text(content, encoding="utf-8")
    return chapters


def _make_compile_env(run_folder: Path, pdf_size: int = 2000) -> Path:
    """Set up a minimal latex/ directory for compile_pdf tests."""
    latex_dir = run_folder / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = latex_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    figures_dir = latex_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    # Write a minimal main.tex so sanitizer doesn't crash
    (latex_dir / "main.tex").write_text(r"\documentclass{article}", encoding="utf-8")
    if pdf_size > 0:
        (latex_dir / "main.pdf").write_bytes(b"%" * pdf_size)
    return latex_dir


# ---------------------------------------------------------------------------
# validate_and_fix_chapters: extra coverage
# ---------------------------------------------------------------------------

def test_validate_nonexistent_chapters_dir(tmp_path):
    """When latex/chapters/ doesn't exist, return early without error."""
    validate_and_fix_chapters(tmp_path)  # no exception


def test_validate_renames_wrong_name(tmp_path):
    """A misnamed ch05_kalman.tex should be renamed to ch05_fusion.tex."""
    chapters = _make_chapters_dir(tmp_path, {
        "ch05_kalman.tex": r"\section{Fusion}" + " word" * 100,
    })

    validate_and_fix_chapters(tmp_path)

    assert (chapters / "ch05_fusion.tex").exists()
    assert not (chapters / "ch05_kalman.tex").exists()


def test_validate_warns_on_extra_files(tmp_path, log_sink):
    """Extra files not in EXPECTED_CHAPTERS should trigger a warning log."""
    files = dict.fromkeys(EXPECTED_CHAPTERS, "content")
    files["ch99_bonus.tex"] = "extra content"
    _make_chapters_dir(tmp_path, files)

    validate_and_fix_chapters(tmp_path)

    assert any("Extra chapter files" in m for m in log_sink)


# ---------------------------------------------------------------------------
# compile_pdf: success path
# ---------------------------------------------------------------------------

def _noop_run(*_args, **_kwargs):
    """Fake subprocess.run that always succeeds."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    return result


def test_compile_pdf_success(tmp_path, monkeypatch):
    """When main.pdf exists and is large enough, compile_pdf returns pdf_dst."""
    _make_compile_env(tmp_path, pdf_size=2000)

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    result = compile_pdf(tmp_path)

    assert result is not None
    assert result == tmp_path / "paper.pdf"
    assert result.exists()


def test_compile_pdf_copies_content(tmp_path, monkeypatch):
    """The output paper.pdf should contain the same bytes as main.pdf."""
    latex_dir = _make_compile_env(tmp_path, pdf_size=5000)

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    pdf_path = compile_pdf(tmp_path)
    assert pdf_path is not None
    assert pdf_path.stat().st_size == (latex_dir / "main.pdf").stat().st_size


# ---------------------------------------------------------------------------
# compile_pdf: failure path
# ---------------------------------------------------------------------------

def test_compile_pdf_no_pdf_returns_none(tmp_path, monkeypatch):
    """When main.pdf does not exist after compilation, return None."""
    _make_compile_env(tmp_path, pdf_size=0)  # no pdf written

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    result = compile_pdf(tmp_path)
    assert result is None


def test_compile_pdf_too_small_returns_none(tmp_path, monkeypatch):
    """A main.pdf smaller than 1000 bytes is treated as a failed build."""
    _make_compile_env(tmp_path, pdf_size=500)

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    result = compile_pdf(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# compile_pdf: fatal errors in log
# ---------------------------------------------------------------------------

def test_compile_pdf_with_fatal_log_errors(tmp_path, monkeypatch, log_sink):
    """Fatal errors in main.log should be logged as warnings but PDF still returned."""
    latex_dir = _make_compile_env(tmp_path, pdf_size=2000)
    log_content = "Some info\n! Undefined control sequence.\n! Missing $ inserted.\nMore info\n"
    (latex_dir / "main.log").write_text(log_content, encoding="utf-8")

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    result = compile_pdf(tmp_path)

    assert result is not None
    assert any("fatal error" in m.lower() for m in log_sink)


def test_compile_pdf_failure_logs_fatal_errors(tmp_path, monkeypatch, log_sink):
    """On compilation failure with a log file, fatal errors are logged at error level."""
    latex_dir = _make_compile_env(tmp_path, pdf_size=0)
    log_content = "! Emergency stop.\n! Missing \\begin{document}.\n"
    (latex_dir / "main.log").write_text(log_content, encoding="utf-8")

    monkeypatch.setattr("src.pipeline.latex_compiler.subprocess.run", _noop_run)
    monkeypatch.setattr("src.pipeline.latex_compiler._sanitize_tex_files", lambda d: None)

    result = compile_pdf(tmp_path)

    assert result is None
    assert any("Emergency stop" in m for m in log_sink)
