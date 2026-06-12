"""
tests/test_quality_gate.py — Quality gate tests (part 1 of 2).
"""
from __future__ import annotations

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
# Constants tests
# ---------------------------------------------------------------------------

def test_min_bib_entries_constant():
    """MIN_BIB_ENTRIES must be 10."""
    assert MIN_BIB_ENTRIES == 10

def test_agent_chapters_count():
    """AGENT_CHAPTERS must list exactly 10 chapter files."""
    assert len(AGENT_CHAPTERS) == 10

def test_quality_threshold():
    """QUALITY_THRESHOLD must be 90."""
    assert QUALITY_THRESHOLD == 90

def test_max_remediations():
    """MAX_REMEDIATIONS must be 4."""
    assert MAX_REMEDIATIONS == 4

# ---------------------------------------------------------------------------
# Helpers (also imported by test_quality_gate_b)
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
    figures_dir = tmp_path / "latex" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "latex").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    files = chapter_files if chapter_files is not None else AGENT_CHAPTERS
    for fname in files:
        (chapters_dir / fname).write_text(chapter_content, encoding="utf-8")
    (tmp_path / "latex" / "references.bib").write_text(bib_content, encoding="utf-8")
    for fig_ref in re.findall(
        r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', chapter_content
    ):
        (figures_dir / fig_ref).write_bytes(b"\x89PNG\r\n\x1a\n")

def _patch_project_root(monkeypatch, tmp_path: Path) -> None:
    """Monkeypatch PROJECT_ROOT for quality gate modules."""
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
# Quality gate integration tests (part 1)
# ---------------------------------------------------------------------------

class TestQualityGate:

    def test_quality_gate_pass_with_good_chapters(
        self, tmp_path, monkeypatch, good_chapter_content, full_bib_content
    ):
        """All good chapters + full bib should yield verdict=PASS and score>=90."""
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

    def test_quality_gate_score_clamped(
        self, tmp_path, monkeypatch, full_bib_content
    ):
        """Quality gate score must never exceed 100 or drop below 0."""
        _patch_project_root(monkeypatch, tmp_path)
        _setup_latex(tmp_path, "tiny", full_bib_content)
        result = run_quality_gate(_make_state(tmp_path))
        assert 0 <= result["quality_score"] <= 100
