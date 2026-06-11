"""
tests/test_quality_gate.py
==========================
Tests for the programmatic quality gate in src/graph/nodes.py.
All tests use tmp_path and monkeypatch to avoid touching real project files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.graph.nodes import (
    AGENT_CHAPTERS,
    MAX_REMEDIATIONS,
    MIN_BIB_ENTRIES,
    QUALITY_THRESHOLD,
    run_quality_gate,
)


# ---------------------------------------------------------------------------
# Constants tests (pure inspection, no filesystem needed)
# ---------------------------------------------------------------------------

def test_min_bib_entries_constant():
    """MIN_BIB_ENTRIES must be 10 (quality gate threshold for references.bib)."""
    assert MIN_BIB_ENTRIES == 10


def test_agent_chapters_count():
    """AGENT_CHAPTERS must list exactly 10 chapter files (abstract + ch01–ch09)."""
    assert len(AGENT_CHAPTERS) == 10


def test_quality_threshold():
    """QUALITY_THRESHOLD must be 90."""
    assert QUALITY_THRESHOLD == 90


def test_max_remediations():
    """MAX_REMEDIATIONS must be 4."""
    assert MAX_REMEDIATIONS == 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_latex(
    tmp_path: Path,
    chapter_content: str,
    bib_content: str,
    chapter_files: list[str] | None = None,
) -> None:
    """Write chapter files and references.bib into tmp_path/latex/."""
    chapters_dir = tmp_path / "latex" / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    figures_dir  = tmp_path / "latex" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "latex").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)

    files = chapter_files if chapter_files is not None else AGENT_CHAPTERS
    for fname in files:
        (chapters_dir / fname).write_text(chapter_content, encoding="utf-8")

    (tmp_path / "latex" / "references.bib").write_text(bib_content, encoding="utf-8")

    # Create dummy figure files for any \includegraphics references found in chapter_content
    import re as _re
    for fig_ref in _re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', chapter_content):
        (figures_dir / fig_ref).write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG magic


def _patch_project_root(monkeypatch, tmp_path: Path) -> None:
    """Monkeypatch PROJECT_ROOT in all modules that import it for quality gate."""
    import src.config as cfg
    import src.graph.nodes as nodes

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(nodes, "PROJECT_ROOT", tmp_path)


def _make_state(tmp_path: Path) -> dict:
    return {
        "topic": "test",
        "run_folder": str(tmp_path),
        "remediation_count": 0,
        "failed_sections": [],
        "quality_verdict": "PENDING",
        "quality_score": 0,
    }


# ---------------------------------------------------------------------------
# Quality gate integration tests
# ---------------------------------------------------------------------------

class TestQualityGate:

    def test_quality_gate_pass_with_good_chapters(
        self, tmp_path, monkeypatch, good_chapter_content, full_bib_content
    ):
        """All good chapters + full bib should yield verdict=PASS and score>=75."""
        _patch_project_root(monkeypatch, tmp_path)
        _setup_latex(tmp_path, good_chapter_content, full_bib_content)

        result = run_quality_gate(_make_state(tmp_path))

        assert result["quality_verdict"] == "PASS", (
            f"Expected PASS, got FAIL with score={result['quality_score']}"
        )
        assert result["quality_score"] >= 90

    def test_quality_gate_fail_missing_chapters(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """No chapter files at all must result in verdict=FAIL."""
        _patch_project_root(monkeypatch, tmp_path)
        # Setup with no chapter files at all
        _setup_latex(tmp_path, "", full_bib_content, chapter_files=[])

        result = run_quality_gate(_make_state(tmp_path))

        assert result["quality_verdict"] == "FAIL"

    def test_quality_gate_fail_missing_bib_keys(
        self, tmp_path, monkeypatch, good_chapter_content, partial_bib_content
    ):
        """Missing BibTeX keys must cause 'references' in failed_sections."""
        _patch_project_root(monkeypatch, tmp_path)
        _setup_latex(tmp_path, good_chapter_content, partial_bib_content)

        result = run_quality_gate(_make_state(tmp_path))

        assert "references" in result["failed_sections"]

    def test_quality_gate_sanitizer_fixes_em_dash(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """Em dashes are auto-fixed by the sanitizer before scoring.

        The quality gate calls _sanitize_tex_files() which replaces em dashes
        with colons, so the score should remain high — verify the sanitizer
        actually removes them from the file on disk.
        """
        _patch_project_root(monkeypatch, tmp_path)

        words = " ".join(["word"] * 2500)
        em_dash_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n"
            + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}" + r"\subsection{D}" + r"\subsection{E}" + "\n"
            + r"\begin{equation}x=1\label{eq:a}\end{equation}" + "\n"
            + r"\begin{equation}y=2\label{eq:b}\end{equation}" + "\n"
            + r"\begin{equation}z=3\label{eq:c}\end{equation}" + "\n"
            + r"\includegraphics{figures/fig.png}" + "\n"
            + r"\cite{A}\cite{B}\cite{C}" + "\n"
            + "Em\u2014dash here\n"  # U+2014
        )
        _setup_latex(tmp_path, em_dash_content, full_bib_content)

        # Verify em dash is present before quality gate
        sample = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text()
        assert "\u2014" in sample, "em dash should be present before quality gate"

        result = run_quality_gate(_make_state(tmp_path))

        # Sanitizer should have removed the em dash from the file
        cleaned = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text()
        assert "\u2014" not in cleaned, "sanitizer should remove em dashes"

        # Score should still be high (sanitizer fixed the issue)
        assert result["quality_score"] >= 90

    def test_quality_gate_sanitizer_fixes_center_env(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        r"""The sanitizer replaces \begin{center} with \centering before scoring.

        Verify the sanitizer actually removes \begin{center} from the file on
        disk so the quality gate no longer penalises it.
        """
        _patch_project_root(monkeypatch, tmp_path)

        words = " ".join(["word"] * 2500)
        center_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n"
            + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}" + r"\subsection{D}" + r"\subsection{E}" + "\n"
            + r"\begin{equation}x=1\label{eq:a}\end{equation}" + "\n"
            + r"\begin{equation}y=2\label{eq:b}\end{equation}" + "\n"
            + r"\begin{equation}z=3\label{eq:c}\end{equation}" + "\n"
            + r"\includegraphics{figures/fig.png}" + "\n"
            + r"\cite{A}\cite{B}\cite{C}" + "\n"
            + r"\begin{center}" + "\n"
            + "centered content\n"
            + r"\end{center}" + "\n"
        )
        _setup_latex(tmp_path, center_content, full_bib_content)

        # Verify \begin{center} is present before quality gate
        sample = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text()
        assert r"\begin{center}" in sample

        result = run_quality_gate(_make_state(tmp_path))

        # Sanitizer should have replaced \begin{center} with \centering
        cleaned = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text()
        assert r"\begin{center}" not in cleaned, "sanitizer should remove \\begin{center}"
        assert r"\centering" in cleaned, "sanitizer should replace with \\centering"

        # Score should still be high (sanitizer fixed the issue)
        assert result["quality_score"] >= 90

    def test_quality_gate_fail_placeholder(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """A chapter with PLACEHOLDER text must reduce the score."""
        _patch_project_root(monkeypatch, tmp_path)

        words = " ".join(["word"] * 2500)
        placeholder_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n"
            + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}" + r"\subsection{D}" + r"\subsection{E}" + "\n"
            + r"\begin{equation}x=1\label{eq:a}\end{equation}" + "\n"
            + r"\begin{equation}y=2\label{eq:b}\end{equation}" + "\n"
            + r"\begin{equation}z=3\label{eq:c}\end{equation}" + "\n"
            + r"\includegraphics{fig.png}" + "\n"
            + r"\cite{A}\cite{B}\cite{C}" + "\n"
            + "PLACEHOLDER content here\n"
        )
        _setup_latex(tmp_path, placeholder_content, full_bib_content)

        result = run_quality_gate(_make_state(tmp_path))

        assert result["quality_score"] < 100

    def test_quality_gate_score_clamped(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """Quality gate score must never exceed 100 or drop below 0."""
        _patch_project_root(monkeypatch, tmp_path)
        # Deliberately broken content to stress-test score clamping
        _setup_latex(tmp_path, "tiny", full_bib_content)

        result = run_quality_gate(_make_state(tmp_path))

        assert 0 <= result["quality_score"] <= 100

    def test_quality_gate_writes_report(
        self, tmp_path, monkeypatch, good_chapter_content, full_bib_content
    ):
        """Quality gate must write outputs/quality_report.md after running."""
        _patch_project_root(monkeypatch, tmp_path)
        _setup_latex(tmp_path, good_chapter_content, full_bib_content)

        run_quality_gate(_make_state(tmp_path))

        report_path = tmp_path / "outputs" / "current" / "quality_report.md"
        assert report_path.exists(), "quality_report.md must be created in outputs/current/"
        assert report_path.stat().st_size > 0

    def test_quality_gate_report_has_json(
        self, tmp_path, monkeypatch, good_chapter_content, full_bib_content
    ):
        """The quality report must contain a parseable JSON verdict block."""
        _patch_project_root(monkeypatch, tmp_path)
        _setup_latex(tmp_path, good_chapter_content, full_bib_content)

        run_quality_gate(_make_state(tmp_path))

        report_text = (tmp_path / "outputs" / "current" / "quality_report.md").read_text(encoding="utf-8")

        # Extract JSON block between ```json ... ```
        match = re.search(r"```json\s*(\{.*?\})\s*```", report_text, re.DOTALL)
        assert match is not None, "Report must contain a ```json ... ``` block"

        verdict_data = json.loads(match.group(1))
        assert "verdict" in verdict_data
        assert "score" in verdict_data
        assert "failed_sections" in verdict_data
        assert verdict_data["verdict"] in ("PASS", "FAIL")
