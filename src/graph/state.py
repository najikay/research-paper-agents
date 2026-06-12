"""
src/graph/state.py
==================
LangGraph state schema for the NavigatorCrew pipeline.
Each field is the authoritative checkpoint between phases.
"""
from __future__ import annotations

from typing import TypedDict


class PipelineState(TypedDict):
    """
    LangGraph state schema shared across the NavigatorCrew pipeline phases.
    Tracks the run topic and folder, the quality-gate verdict/score and failed
    sections, remediation and research-fix counts, and the fast/smoke mode flags.
    """
    topic: str
    run_folder: str              # Absolute path to this run's folder
    remediation_count: int       # How many remediation loops have run
    failed_sections: list[str]   # Section names that failed quality check
    quality_verdict: str         # "PENDING" | "PASS" | "FAIL"
    quality_score: int           # 0-100 score from editor's structured report
    fast_mode: bool              # If True, skip domain expert agents (6 tasks)
    smoke_mode: bool             # If True, 2-task pipeline: outline + latex_all (~5 min)
    research_fix_count: int      # How many domain expert outputs were fixed by validator
