"""
src/graph/nodes.py
==================
LangGraph node functions (v6 — split pipeline with validation gate).

Graph topology:
  run_research_phase -> validate_and_fix_research -> run_writing_phase
    -> run_quality_gate -> [PASS -> END | FAIL -> run_remediation -> run_quality_gate]

Each node:
  - Receives the full PipelineState
  - Does its work (runs a CrewAI sub-crew or programmatic check)
  - Returns a dict of state keys to update (LangGraph merges these)
"""
from __future__ import annotations

from src.config import logger

# ---------------------------------------------------------------------------
# Re-exports from split modules (backward compatibility)
# ---------------------------------------------------------------------------
from src.graph.nodes_quality import (  # noqa: F401
    AGENT_CHAPTERS,
    MAX_REMEDIATIONS,
    MIN_BIB_ENTRIES,
    QUALITY_THRESHOLD,
    run_quality_gate,
)
from src.graph.nodes_remediation import run_remediation  # noqa: F401
from src.graph.nodes_validation import validate_and_fix_research  # noqa: F401
from src.graph.state import PipelineState


# ---------------------------------------------------------------------------
# Node 1: run_main_pipeline (legacy — for fast/smoke modes)
# ---------------------------------------------------------------------------
def run_main_pipeline(state: PipelineState) -> dict:
    """
    Legacy node: runs the full single-crew pipeline.
    Used by fast and smoke modes. Full mode uses the split nodes instead.
    """
    from src.crew import build_crew

    logger.info("[Graph] NODE: run_main_pipeline (legacy)")
    fast_mode = state.get("fast_mode", False)
    smoke_mode = state.get("smoke_mode", False)
    crew, accountant = build_crew(
        topic=state["topic"],
        run_folder=state["run_folder"],
        fast_mode=fast_mode,
        smoke_mode=smoke_mode,
    )
    crew.kickoff()
    return {"quality_verdict": "PENDING"}


# ---------------------------------------------------------------------------
# Node 1a: run_research_phase (v6 split architecture)
# ---------------------------------------------------------------------------
def run_research_phase(state: PipelineState) -> dict:
    """
    Phase 1: Run the research crew — outline, deep research, 8 domain experts.
    Produces: paper_outline.md, research_briefs.md, domain_*.md
    """
    from src.crew import build_research_crew

    logger.info("[Graph] NODE: run_research_phase")
    crew, accountant = build_research_crew(
        topic=state["topic"],
        run_folder=state["run_folder"],
    )
    crew.kickoff()
    logger.info("[Graph] Research phase complete")
    return {"quality_verdict": "PENDING", "research_fix_count": 0}


# ---------------------------------------------------------------------------
# Node 1c: run_writing_phase (v6 split architecture)
# ---------------------------------------------------------------------------
def run_writing_phase(state: PipelineState) -> dict:
    """
    Phase 2: Run the writing crew — visualizer, Hebrew writer, 3 LaTeX authors.
    Reads from outputs/current/ (populated by research phase + validator).
    Produces: figures, hebrew_prose.md, all chapter .tex files, references.bib.
    """
    from src.crew import build_writing_crew

    logger.info("[Graph] NODE: run_writing_phase")
    crew, accountant = build_writing_crew(
        run_folder=state["run_folder"],
    )
    crew.kickoff()
    logger.info("[Graph] Writing phase complete")
    return {"quality_verdict": "PENDING"}
