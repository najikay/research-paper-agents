"""
src/graph/nodes_remediation.py
===============================
Remediation node: targeted fixes for chapters that failed the quality gate.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Crew, Process

from src.agents import create_latex_author
from src.config import PROJECT_ROOT, logger
from src.graph.nodes_quality import MAX_REMEDIATIONS
from src.graph.state import PipelineState
from src.tasks import create_remediation_task
from src.tools import FileReaderTool, SafeFileWriterTool


def run_remediation(state: PipelineState) -> dict:
    """Build a minimal sub-crew that fixes ONLY the failing chapters in-place."""
    count = state["remediation_count"] + 1
    logger.info(f"[Graph] NODE: run_remediation (attempt {count}/{MAX_REMEDIATIONS})")
    logger.info(f"[Graph] Failed sections: {state['failed_sections']}")

    run_folder = Path(state["run_folder"])
    failed = state["failed_sections"]

    author = create_latex_author(tools=[SafeFileWriterTool(), FileReaderTool()])
    author.max_iter = 55

    report_path = PROJECT_ROOT / "outputs" / "current" / "quality_report.md"
    chapter_issues: list[str] = []
    if report_path.exists():
        for line in report_path.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip("- ")
            if line.startswith("- ch") and any(
                k in line for k in ("words", "equations", "figures", "citations", "subsections")
            ) or line.startswith("- Missing") and "chapter" in line.lower():
                chapter_issues.append(stripped)
    detailed_failed = chapter_issues if chapter_issues else failed
    logger.info(f"[Graph] Remediation targets: {detailed_failed}")

    t_latex = create_remediation_task(
        agent=author,
        failed_sections=detailed_failed,
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/latex_status.md",
        run_folder=run_folder,
    )

    Crew(
        agents=[author],
        tasks=[t_latex],
        process=Process.sequential,
        verbose=True,
    ).kickoff()

    return {
        "remediation_count": count,
        "quality_verdict": "PENDING",
    }
