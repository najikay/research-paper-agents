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
