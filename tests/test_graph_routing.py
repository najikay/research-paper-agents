"""
tests/test_graph_routing.py
============================
Tests for _route_after_quality_gate() in src/graph/navigator_graph.py.
No LLM calls are made — routing logic is tested in isolation.
"""

from __future__ import annotations

import pytest

from src.graph.navigator_graph import _route_after_quality_gate
from src.graph.nodes import MAX_REMEDIATIONS


def _state(verdict: str, remediation_count: int, score: int = 80) -> dict:
    """Build a minimal PipelineState-compatible dict for routing tests."""
    return {
        "topic": "test",
        "quality_verdict": verdict,
        "quality_score": score,
        "remediation_count": remediation_count,
        "failed_sections": [],
    }


# ---------------------------------------------------------------------------
# Parametrized routing tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("verdict,count,expected", [
    ("PASS", 0,                "end"),
    ("PASS", 1,                "end"),
    ("PASS", MAX_REMEDIATIONS, "end"),
    ("FAIL", 0,                "remediate"),
    ("FAIL", 1,                "remediate"),
    ("FAIL", MAX_REMEDIATIONS, "end"),
    ("FAIL", MAX_REMEDIATIONS + 3, "end"),
])
def test_routing(verdict, count, expected):
    """_route_after_quality_gate must return the correct next node for each case."""
    result = _route_after_quality_gate(_state(verdict, count))
    assert result == expected, (
        f"verdict={verdict!r}, count={count} → expected {expected!r}, got {result!r}"
    )


# Keep individually named tests as required by the spec, delegating to the parametrize above:

def test_route_pass_goes_to_end():
    """PASS verdict must route to 'end'."""
    assert _route_after_quality_gate(_state("PASS", 0)) == "end"


def test_route_fail_remediation_count_zero():
    """FAIL with remediation_count=0 must route to 'remediate'."""
    assert _route_after_quality_gate(_state("FAIL", 0)) == "remediate"


def test_route_fail_remediation_count_one():
    """FAIL with remediation_count=1 must route to 'remediate'."""
    assert _route_after_quality_gate(_state("FAIL", 1)) == "remediate"


def test_route_fail_max_remediations_reached():
    """FAIL with remediation_count==MAX_REMEDIATIONS must route to 'end'."""
    assert _route_after_quality_gate(_state("FAIL", MAX_REMEDIATIONS)) == "end"


def test_route_fail_over_max_remediations():
    """FAIL with remediation_count > MAX_REMEDIATIONS must also route to 'end'."""
    assert _route_after_quality_gate(_state("FAIL", 5)) == "end"


# ---------------------------------------------------------------------------
# Graph build smoke test
# ---------------------------------------------------------------------------

def test_graph_builds_without_error():
    """build_navigator_graph() must compile without raising any exception."""
    from src.graph.navigator_graph import build_navigator_graph
    graph = build_navigator_graph()
    assert graph is not None
