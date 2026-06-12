"""
tests/test_quality_gate_b.py — Quality gate tests (part 2 of 2).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.graph.nodes import AGENT_CHAPTERS, run_quality_gate
from tests.test_quality_gate import _make_state, _patch_project_root, _setup_latex

# ---------------------------------------------------------------------------
# Quality gate integration tests (part 2)
# ---------------------------------------------------------------------------

class TestQualityGateB:

    def test_quality_gate_sanitizer_fixes_em_dash(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """Em dashes are auto-fixed by the sanitizer before scoring."""
        _patch_project_root(monkeypatch, tmp_path)
        words = " ".join(["word"] * 2500)
        em_dash_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n" + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}"
            + r"\subsection{D}" + r"\subsection{E}" + "\n"
            + r"\begin{equation}x=1\label{eq:a}\end{equation}" + "\n"
            + r"\begin{equation}y=2\label{eq:b}\end{equation}" + "\n"
            + r"\begin{equation}z=3\label{eq:c}\end{equation}" + "\n"
            + r"\includegraphics{figures/fig.png}" + "\n"
            + r"\cite{A}\cite{B}\cite{C}" + "\n"
            + "Em\u2014dash here\n"
        )
        _setup_latex(tmp_path, em_dash_content, full_bib_content)
        sample = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text(encoding="utf-8")
        assert "\u2014" in sample, "em dash should be present before quality gate"
        result = run_quality_gate(_make_state(tmp_path))
        cleaned = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text(encoding="utf-8")
        assert "\u2014" not in cleaned, "sanitizer should remove em dashes"
        assert result["quality_score"] >= 90

    def test_quality_gate_sanitizer_fixes_center_env(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        r"""The sanitizer replaces \begin{center} with \centering before scoring."""
        _patch_project_root(monkeypatch, tmp_path)
        words = " ".join(["word"] * 2500)
        center_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n" + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}"
            + r"\subsection{D}" + r"\subsection{E}" + "\n"
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
        sample = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text(encoding="utf-8")
        assert r"\begin{center}" in sample
        result = run_quality_gate(_make_state(tmp_path))
        cleaned = (tmp_path / "latex" / "chapters" / AGENT_CHAPTERS[1]).read_text(encoding="utf-8")
        assert r"\begin{center}" not in cleaned, "sanitizer should remove \\begin{center}"
        assert r"\centering" in cleaned, "sanitizer should replace with \\centering"
        assert result["quality_score"] >= 90

    def test_quality_gate_fail_placeholder(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """A chapter with PLACEHOLDER text must reduce the score."""
        _patch_project_root(monkeypatch, tmp_path)
        words = " ".join(["word"] * 2500)
        placeholder_content = (
            r"\selectlanguage{hebrew}" + "\n"
            r"\section{Test}" + "\n" + words + "\n"
            + r"\subsection{A}" + r"\subsection{B}" + r"\subsection{C}"
            + r"\subsection{D}" + r"\subsection{E}" + "\n"
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
        report_text = (
            tmp_path / "outputs" / "current" / "quality_report.md"
        ).read_text(encoding="utf-8")
        match = re.search(r"```json\s*(\{.*?\})\s*```", report_text, re.DOTALL)
        assert match is not None, "Report must contain a ```json ... ``` block"
        verdict_data = json.loads(match.group(1))
        assert "verdict" in verdict_data
        assert "score" in verdict_data
        assert "failed_sections" in verdict_data
        assert verdict_data["verdict"] in ("PASS", "FAIL")
