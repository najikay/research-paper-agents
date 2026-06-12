"""
tests/test_nodes_extended.py
============================
Extended coverage for graph node functions:
  - nodes_validation.validate_and_fix_research
  - nodes.run_main_pipeline, run_research_phase, run_writing_phase
  - nodes_remediation.run_remediation
  - navigator_graph._route_after_quality_gate, build_navigator_graph
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.graph.nodes_validation import _DOMAIN_KEYS, _MIN_DOMAIN_BYTES

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_BASE = {
    "topic": "test-topic", "run_folder": "/tmp/fake", "remediation_count": 0,
    "failed_sections": [], "quality_verdict": "PENDING", "quality_score": 0,
    "fast_mode": False, "smoke_mode": False, "research_fix_count": 0,
}

def _state(**overrides) -> dict:
    return {**_BASE, **overrides}

VALID_BODY = "A" * (_MIN_DOMAIN_BYTES + 100)

def _populate_staging(staging: Path, *, skip: list[str] | None = None,
                      small: list[str] | None = None,
                      loop: list[str] | None = None,
                      stub: list[str] | None = None):
    """Create domain_*.md files in *staging* with controlled content."""
    staging.mkdir(parents=True, exist_ok=True)
    skip, small, loop, stub = skip or [], small or [], loop or [], stub or []
    for key in _DOMAIN_KEYS:
        if key in skip:
            continue
        fpath = staging / f"domain_{key}.md"
        if key in small:
            fpath.write_text("tiny", encoding="utf-8")
        elif key in loop:
            fpath.write_text("STEP 1\nSTEP 1\nSTEP 1\n" + VALID_BODY, encoding="utf-8")
        elif key in stub:
            fpath.write_text("DOMAIN EXPERT COMPLETE", encoding="utf-8")
        else:
            fpath.write_text(VALID_BODY, encoding="utf-8")


# ===========================================================================
# nodes_validation  — validate_and_fix_research
# ===========================================================================
class TestValidateAndFixResearch:
    """Cover lines 26-85 of nodes_validation.py."""

    def _run(self, tmp_path, monkeypatch, **pop_kw):
        import src.graph.nodes_validation as mod
        monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
        _populate_staging(tmp_path / "outputs" / "current", **pop_kw)
        with patch("src.crew_fixer.build_fixer_crew") as mock_fix:
            mock_fix.return_value = (MagicMock(), None)
            result = mod.validate_and_fix_research(_state())
        return result, mock_fix

    def test_all_valid(self, tmp_path, monkeypatch):
        result, mock_fix = self._run(tmp_path, monkeypatch)
        assert result == {"research_fix_count": 0}
        mock_fix.assert_not_called()

    def test_missing_file(self, tmp_path, monkeypatch):
        result, _ = self._run(tmp_path, monkeypatch, skip=["physics"])
        assert result["research_fix_count"] == 1

    def test_too_small_file(self, tmp_path, monkeypatch):
        result, _ = self._run(tmp_path, monkeypatch, small=["ml"])
        assert result["research_fix_count"] == 1

    def test_loop_pattern_detected(self, tmp_path, monkeypatch):
        result, _ = self._run(tmp_path, monkeypatch, loop=["algorithms"])
        assert result["research_fix_count"] == 1

    def test_stub_shortcut_detected(self, tmp_path, monkeypatch):
        result, _ = self._run(tmp_path, monkeypatch, stub=["biology"])
        assert result["research_fix_count"] == 1

    def test_multiple_failures_with_outline(self, tmp_path, monkeypatch):
        import src.graph.nodes_validation as mod
        monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
        _populate_staging(tmp_path / "outputs" / "current",
                          skip=["physics"], small=["ml"], stub=["biology"])
        outline = tmp_path / "outputs" / "current" / "paper_outline.md"
        outline.write_text("# Outline\nSome outline text", encoding="utf-8")
        with patch("src.crew_fixer.build_fixer_crew") as mock_fix:
            mock_fix.return_value = (MagicMock(), None)
            result = mod.validate_and_fix_research(_state())
        assert result["research_fix_count"] == 3
        mock_fix.assert_called_once()


# ===========================================================================
# nodes.py  — crew launcher nodes
# ===========================================================================
class TestCrewNodes:
    """Cover lines 40-79 of nodes.py (run_main_pipeline / research / writing)."""

    def test_run_main_pipeline(self):
        with patch("src.crew_legacy.build_crew") as mock_bc:
            mock_bc.return_value = (MagicMock(), MagicMock())
            from src.graph.nodes import run_main_pipeline
            result = run_main_pipeline(_state())
        assert result["quality_verdict"] == "PENDING"

    def test_run_research_phase(self):
        with patch("src.crew.build_research_crew") as mock_rc:
            mock_rc.return_value = (MagicMock(), MagicMock())
            from src.graph.nodes import run_research_phase
            result = run_research_phase(_state())
        assert result == {"quality_verdict": "PENDING", "research_fix_count": 0}

    def test_run_writing_phase(self):
        with patch("src.crew.build_writing_crew") as mock_wc:
            mock_wc.return_value = (MagicMock(), MagicMock())
            from src.graph.nodes import run_writing_phase
            result = run_writing_phase(_state())
        assert result == {"quality_verdict": "PENDING"}


# ===========================================================================
# nodes_remediation.py  — run_remediation
# ===========================================================================
class TestRunRemediation:
    """Cover lines 23-60 of nodes_remediation.py."""

    @patch("src.graph.nodes_remediation.Crew")
    @patch("src.graph.nodes_remediation.create_remediation_task")
    @patch("src.graph.nodes_remediation.create_latex_author")
    def test_run_remediation_basic(self, mock_author, mock_task, mock_crew, tmp_path):
        mock_author.return_value = MagicMock(max_iter=12)
        mock_task.return_value = MagicMock()
        mock_crew_inst = MagicMock()
        mock_crew.return_value = mock_crew_inst
        from src.graph.nodes_remediation import run_remediation
        result = run_remediation(_state(
            run_folder=str(tmp_path), failed_sections=["ch04_slam.tex"],
        ))
        assert result == {"remediation_count": 1, "quality_verdict": "PENDING"}
        mock_crew_inst.kickoff.assert_called_once()


# ===========================================================================
# navigator_graph.py  — routing + graph construction
# ===========================================================================
class TestNavigatorGraph:
    """Cover _route_after_quality_gate and build_navigator_graph(split_mode=False)."""

    def test_route_pass(self):
        from src.graph.navigator_graph import _route_after_quality_gate
        assert _route_after_quality_gate(_state(quality_verdict="PASS")) == "end"

    def test_route_fail_max_remediations(self):
        from src.graph.navigator_graph import MAX_REMEDIATIONS, _route_after_quality_gate
        s = _state(quality_verdict="FAIL", remediation_count=MAX_REMEDIATIONS, quality_score=50)
        assert _route_after_quality_gate(s) == "end"

    def test_route_fail_needs_remediation(self):
        from src.graph.navigator_graph import _route_after_quality_gate
        s = _state(quality_verdict="FAIL", remediation_count=0, quality_score=50)
        assert _route_after_quality_gate(s) == "remediate"

    def test_build_graph_legacy_mode(self):
        from src.graph.navigator_graph import build_navigator_graph
        compiled = build_navigator_graph(split_mode=False)
        assert compiled is not None
