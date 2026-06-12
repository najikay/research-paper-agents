"""
test_compile_dryrun_b.py
========================
Split from test_compile_dryrun.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import src.runner.compile as compile_mod
import src.runner.dryrun as dryrun_mod
from src.runner.compile import compile_pdf
from src.runner.dryrun import run_dry_run


def test_compile_pdf_failure_logs_fatal_errors_from_log(tmp_path, monkeypatch):
    """Failure path logs '!' lines from main.log (the else branch)."""
    run_folder = _build_run_folder(tmp_path)
    latex_dir = run_folder / "latex"
    (latex_dir / "main.log").write_text(
        "! Emergency stop.\n! ==> Fatal error occurred.\n",
        encoding="utf-8",
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


# ---------------------------------------------------------------------------
# run_dry_run
# ---------------------------------------------------------------------------

def _make_args(**overrides):
    base = {
        "topic": "Test Topic",
        "no_pdf": False,
        "no_archive": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _patch_dryrun_collaborators(monkeypatch, *, calls: dict, pdf_path=None):
    """Patch every collaborator run_dry_run touches so it stays offline."""
    import src.graph.nodes as nodes_mod
    import src.stubs as stubs_mod

    def fake_write_stub_chapters(run_folder, topic):
        calls["write_stub"] = (Path(run_folder), topic)

    def fake_run_quality_gate(state):
        calls["quality_gate"] = state
        return {"quality_score": 73, "quality_verdict": "PASS"}

    def fake_compile_pdf(run_folder):
        calls["compile"] = Path(run_folder)
        return pdf_path

    def fake_finalize_run(run_folder):
        calls["finalize"] = Path(run_folder)

    monkeypatch.setattr(stubs_mod, "write_stub_chapters", fake_write_stub_chapters)
    monkeypatch.setattr(nodes_mod, "run_quality_gate", fake_run_quality_gate)
    monkeypatch.setattr(dryrun_mod, "compile_pdf", fake_compile_pdf)
    monkeypatch.setattr(dryrun_mod, "finalize_run", fake_finalize_run)


def test_run_dry_run_full_flow(tmp_path, monkeypatch, capsys):
    """Happy path: stubs written, gate run, PDF compiled, folder kept."""
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    pdf_path = run_folder / "paper.pdf"
    calls: dict = {}
    _patch_dryrun_collaborators(monkeypatch, calls=calls, pdf_path=pdf_path)

    args = _make_args(no_pdf=False, no_archive=False)
    run_dry_run(args, run_folder)

    assert calls["write_stub"] == (run_folder, "Test Topic")
    assert calls["quality_gate"]["topic"] == "Test Topic"
    assert calls["compile"] == run_folder
    assert calls["finalize"] == run_folder

    out = capsys.readouterr().out
    assert "DRY-RUN COMPLETE" in out
    assert "73/100" in out
    assert "PASS" in out
    assert str(pdf_path) in out
    assert str(run_folder) in out
    # Folder kept (no_archive False) so it still exists.
    assert run_folder.exists()


def test_run_dry_run_no_pdf_skips_compile(tmp_path, monkeypatch, capsys):
    """--no-pdf: compile_pdf is never called and no PDF line is printed."""
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    calls: dict = {}
    _patch_dryrun_collaborators(monkeypatch, calls=calls, pdf_path=None)

    args = _make_args(no_pdf=True, no_archive=False)
    run_dry_run(args, run_folder)

    assert "compile" not in calls
    out = capsys.readouterr().out
    assert "PDF              :" not in out


def test_run_dry_run_no_archive_removes_folder(tmp_path, monkeypatch, capsys):
    """--no-archive: run folder is deleted and omitted from the banner."""
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    pdf_path = run_folder / "paper.pdf"
    calls: dict = {}
    _patch_dryrun_collaborators(monkeypatch, calls=calls, pdf_path=pdf_path)

    args = _make_args(no_pdf=False, no_archive=True)
    run_dry_run(args, run_folder)

    assert not run_folder.exists()
    out = capsys.readouterr().out
    assert "Run Folder       :" not in out
