"""Unit tests for src/runner/compile.py (compile_pdf)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import src.runner.compile as compile_mod
from src.runner.compile import compile_pdf


def _build_run_folder(tmp_path: Path, *, with_missing_figure: bool = True) -> Path:
    """Create a minimal run_folder/latex tree for compile tests."""
    run_folder = tmp_path / "run"
    latex_dir = run_folder / "latex"
    chapters_dir = latex_dir / "chapters"
    figures_dir = latex_dir / "figures"
    chapters_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    (latex_dir / "main.tex").write_text(
        r"\documentclass{article}\begin{document}\input{chapters/ch01}\end{document}",
        encoding="utf-8",
    )
    fig_ref = "missing_plot.png" if with_missing_figure else "fig_stub.png"
    (chapters_dir / "ch01.tex").write_text(
        r"\section{Intro}" "\n"
        r"\includegraphics[width=0.8\textwidth]{figures/" + fig_ref + "}\n",
        encoding="utf-8",
    )
    (figures_dir / "fig_stub.png").write_bytes(b"\x89PNG\r\n\x1a\n stub")
    return run_folder


def _ok_result(stdout: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout)


def _fail_result(stdout: str = "boom") -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout=stdout)


def test_compile_pdf_success_creates_paper_pdf(tmp_path, monkeypatch):
    """Fake xelatex creates a >1000-byte main.pdf -> paper.pdf is produced."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"

    def fake_run(cmd, **kwargs):
        (latex_dir / "main.pdf").write_bytes(b"%PDF-1.5\n" + b"x" * 2000)
        return _ok_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    result = compile_pdf(run_folder)
    assert result == run_folder / "paper.pdf"
    assert result.exists()
    assert result.stat().st_size > 1000


def test_compile_pdf_stubs_missing_figure(tmp_path, monkeypatch):
    """A missing figure referenced via includegraphics is stubbed."""
    run_folder = _build_run_folder(tmp_path, with_missing_figure=True)
    latex_dir = run_folder / "latex"
    figures_dir = latex_dir / "figures"

    def fake_run(cmd, **kwargs):
        (latex_dir / "main.pdf").write_bytes(b"%PDF-1.5\n" + b"x" * 2000)
        return _ok_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    assert not (figures_dir / "missing_plot.png").exists()
    compile_pdf(run_folder)
    assert (figures_dir / "missing_plot.png").exists()


def test_compile_pdf_success_logs_fatal_errors_from_log(tmp_path, monkeypatch):
    """main.log lines starting with '!' trigger the fatal-error logging branch."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"
    (latex_dir / "main.log").write_text(
        "Some normal output\n! Undefined control sequence.\n! Missing $ inserted.\n",
        encoding="utf-8",
    )

    def fake_run(cmd, **kwargs):
        (latex_dir / "main.pdf").write_bytes(b"%PDF-1.5\n" + b"x" * 2000)
        return _ok_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    result = compile_pdf(run_folder)
    assert result == run_folder / "paper.pdf"
    assert result.exists()


def test_compile_pdf_no_pdf_returns_none(tmp_path, monkeypatch):
    """Non-zero exit and no main.pdf produced -> compile_pdf returns None."""
    run_folder = _build_run_folder(tmp_path)

    def fake_run(cmd, **kwargs):
        return _fail_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    assert compile_pdf(run_folder) is None


def test_compile_pdf_tiny_pdf_returns_none(tmp_path, monkeypatch):
    """A main.pdf <= 1000 bytes is treated as failure -> None."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"

    def fake_run(cmd, **kwargs):
        (latex_dir / "main.pdf").write_bytes(b"%PDF tiny")
        return _ok_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    assert compile_pdf(run_folder) is None


def test_compile_pdf_failure_logs_fatal_errors_from_log(tmp_path, monkeypatch):
    """Failure path logs '!' lines from main.log (the else branch)."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"
    (latex_dir / "main.log").write_text(
        "! Emergency stop.\n! ==> Fatal error occurred.\n", encoding="utf-8",
    )

    def fake_run(cmd, **kwargs):
        return _fail_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    assert compile_pdf(run_folder) is None


def test_compile_pdf_timeout_branch(tmp_path, monkeypatch):
    """subprocess.TimeoutExpired is caught per-pass; with no PDF -> None."""
    run_folder = _build_run_folder(tmp_path)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=600)

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    assert compile_pdf(run_folder) is None


def test_compile_pdf_cleans_stale_artifacts(tmp_path, monkeypatch):
    """Stale build artifacts (e.g. main.aux) are deleted before compilation."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"
    stale = latex_dir / "main.aux"
    stale.write_text("stale", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        return _fail_result()

    monkeypatch.setattr(compile_mod.subprocess, "run", fake_run)
    compile_pdf(run_folder)
    assert not stale.exists()
