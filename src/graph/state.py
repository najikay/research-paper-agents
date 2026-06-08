"""
src/graph/state.py
==================
LangGraph state schema for the NavigatorCrew pipeline.
Each field is the authoritative checkpoint between phases.
"""
from __future__ import annotations
from typing import TypedDict

class PipelineState(TypedDict):
    topic: str
    run_folder: str              # Absolute path to this run's folder
    remediation_count: int       # How many remediation loops have run
    failed_sections: list[str]   # Section names that failed quality check
    quality_verdict: str         # "PENDING" | "PASS" | "FAIL"
    quality_score: int           # 0-100 score from editor's structured report
