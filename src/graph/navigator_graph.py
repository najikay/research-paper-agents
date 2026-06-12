"""
src/graph/navigator_graph.py
=============================
Builds and returns the compiled LangGraph state machine (v6 — split pipeline).

Graph topology (full mode):

  [run_research_phase]          ← 10 agents: director + researcher + 8 domain experts
          |
          v
  [validate_and_fix_research]   ← programmatic check + Fixer crew for failures
          |
          v
  [run_writing_phase]           ← 5 agents: visualizer + Hebrew writer + 3 LaTeX authors
          |
          v
  [run_quality_gate]  ──PASS──>  [END]
          |
         FAIL
          |
          v
  [run_remediation]
          |
          v
  [run_quality_gate]  ──PASS──>  [END]
          |
         FAIL (if remediation_count >= MAX_REMEDIATIONS)
          |
          v
         [END]  (graceful degradation)

Graph topology (fast/smoke mode — legacy single crew):

  [run_main_pipeline]
          |
          v
  [run_quality_gate]  ──PASS──>  [END]
          |
         FAIL
          |
          v
  [run_remediation] → [run_quality_gate] → ...
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.config import logger
from src.graph.nodes import (
    MAX_REMEDIATIONS,
    QUALITY_THRESHOLD,
    run_main_pipeline,
    run_quality_gate,
    run_remediation,
    run_research_phase,
    run_writing_phase,
    validate_and_fix_research,
)
from src.graph.state import PipelineState


def _route_after_quality_gate(state: PipelineState) -> str:
    """Conditional edge: decides what happens after the quality gate."""
    if state["quality_verdict"] == "PASS":
        logger.info("[Graph] ROUTE: Quality PASSED → END")
        return "end"

    if state["remediation_count"] >= MAX_REMEDIATIONS:
        logger.warning(
            f"[Graph] ROUTE: Quality FAILED after {MAX_REMEDIATIONS} remediations "
            f"(score={state['quality_score']}) — accepting current output → END"
        )
        return "end"

    logger.info(
        f"[Graph] ROUTE: Quality FAILED (score={state['quality_score']} < {QUALITY_THRESHOLD}) "
        f"→ remediation #{state['remediation_count'] + 1}"
    )
    return "remediate"


def build_navigator_graph(split_mode: bool = True):
    """
    Compile and return the NavigatorCrew LangGraph state machine.

    Args:
        split_mode: If True (default), use the v6 split pipeline with validation.
                    If False, use the legacy single-crew pipeline (fast/smoke modes).
    """
    graph = StateGraph(PipelineState)

    if split_mode:
        # v6 split architecture: research → validate → writing → quality → remediation
        graph.add_node("run_research_phase",         run_research_phase)
        graph.add_node("validate_and_fix_research",  validate_and_fix_research)
        graph.add_node("run_writing_phase",          run_writing_phase)
        graph.add_node("run_quality_gate",           run_quality_gate)
        graph.add_node("run_remediation",            run_remediation)

        graph.set_entry_point("run_research_phase")
        graph.add_edge("run_research_phase",        "validate_and_fix_research")
        graph.add_edge("validate_and_fix_research", "run_writing_phase")
        graph.add_edge("run_writing_phase",         "run_quality_gate")
        graph.add_edge("run_remediation",           "run_quality_gate")
    else:
        # Legacy single-crew pipeline (fast/smoke modes)
        graph.add_node("run_main_pipeline", run_main_pipeline)
        graph.add_node("run_quality_gate",  run_quality_gate)
        graph.add_node("run_remediation",   run_remediation)

        graph.set_entry_point("run_main_pipeline")
        graph.add_edge("run_main_pipeline", "run_quality_gate")
        graph.add_edge("run_remediation",   "run_quality_gate")

    # Conditional edge from quality gate (shared by both modes)
    graph.add_conditional_edges(
        "run_quality_gate",
        _route_after_quality_gate,
        {
            "end":       END,
            "remediate": "run_remediation",
        },
    )

    return graph.compile()
