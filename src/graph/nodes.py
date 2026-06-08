"""
src/graph/nodes.py
==================
LangGraph node functions. Each node:
  - Receives the full PipelineState
  - Does its work (runs a CrewAI sub-crew or parses a file)
  - Returns a dict of state keys to update (LangGraph merges these)
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from crewai import Crew, Process

from src.agents import (
    create_slam_researcher,
    create_latex_author,
)
from src.graph.state import PipelineState
from src.tasks.research_tasks import (
    create_task_research,
    create_task_latex,
    create_remediation_task,
)
from src.tools import (
    ArxivSearchTool, FileReaderTool,
    NavigatorWebScraperTool, SafeFileWriterTool, SerperDevSearchTool,
)
from src.config import logger, PROJECT_ROOT

QUALITY_THRESHOLD = 75   # score below this triggers remediation
MAX_REMEDIATIONS  = 2    # hard cap — prevents infinite loops

# Required BibTeX keys that must exist in references.bib
REQUIRED_CITE_KEYS = {
    "Thrun2005ProbRobotics", "Kalman1960", "Grisetti2010g2o", "MurArtal2015ORB",
    "Julier1997CovarianceIntersection", "GriffinBatEcholocation",
    "GriffithBatEcholocation", "Simmons1979BatSonar", "Schnitzler1968DSC",
    "Schuller1974DSC", "MossEcholocation", "Rihaczek1969MatchedFilter",
    "CrewAIDocs", "AnthropicClaude",
}

# Chapters the agent is responsible for writing
AGENT_CHAPTERS = [
    "abstract.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]


# ---------------------------------------------------------------------------
# Node 1: run_main_pipeline
# ---------------------------------------------------------------------------
def run_main_pipeline(state: PipelineState) -> dict:
    """
    Runs the full CrewAI pipeline (outline → research → figures → latex).
    """
    from src.crew import build_crew  # lazy import avoids circular deps

    logger.info("[Graph] NODE: run_main_pipeline")
    crew, accountant = build_crew(topic=state["topic"], run_folder=state["run_folder"])
    crew.kickoff()
    return {"quality_verdict": "PENDING"}


# ---------------------------------------------------------------------------
# Node 2: run_quality_gate  (programmatic — no LLM loop risk)
# ---------------------------------------------------------------------------
def run_quality_gate(state: PipelineState) -> dict:
    """
    Programmatic quality check of generated LaTeX files.
    Scores the paper based on structural completeness and correctness,
    without relying on an LLM agent that can loop indefinitely.
    """
    logger.info("[Graph] NODE: run_quality_gate (programmatic)")

    run_folder   = Path(state["run_folder"])
    chapters_dir = run_folder / "latex" / "chapters"
    bib_path     = run_folder / "latex" / "references.bib"

    issues: list[str] = []
    failed_sections: list[str] = []
    score = 100

    # ── 1. Check all chapter files exist ─────────────────────────────────
    missing_files = []
    for fname in AGENT_CHAPTERS:
        fpath = chapters_dir / fname
        if not fpath.exists() or fpath.stat().st_size < 200:
            missing_files.append(fname)
            score -= 8
    if missing_files:
        issues.append(f"Missing or empty chapter files: {missing_files}")
        failed_sections.extend(["introduction", "methodology", "algorithms"])

    # ── 2. Check structural elements per chapter ──────────────────────────
    content_chapters = [f for f in AGENT_CHAPTERS if f not in ("abstract.tex",)]
    for fname in content_chapters:
        fpath = chapters_dir / fname
        if not fpath.exists():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")
        section_name = fname.replace(".tex", "").replace("ch0", "ch").replace("ch", "")

        eq_count  = len(re.findall(r"\\begin\{equation\}", text))
        fig_count = len(re.findall(r"\\includegraphics", text))
        tab_count = len(re.findall(r"\\begin\{table\}", text))
        sub_count = len(re.findall(r"\\subsection\{", text))
        cite_count = len(re.findall(r"\\cite\{", text))
        word_est  = len(text.split())

        chapter_issues = []
        if eq_count < 2:
            chapter_issues.append(f"equations={eq_count}<2")
            score -= 3
        if fig_count < 1:
            chapter_issues.append(f"figures={fig_count}<1")
            score -= 3
        if sub_count < 3:
            chapter_issues.append(f"subsections={sub_count}<3")
            score -= 2
        if cite_count < 2:
            chapter_issues.append(f"citations={cite_count}<2")
            score -= 2
        if word_est < 300:
            chapter_issues.append(f"words≈{word_est}<300")
            score -= 4
            failed_sections.append("methodology")

        if chapter_issues:
            issues.append(f"{fname}: " + ", ".join(chapter_issues))

    # ── 3. Check references.bib has required keys ────────────────────────
    if bib_path.exists():
        bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
        defined_keys = set(re.findall(r"@\w+\{(\w+),", bib_text))
        missing_keys = REQUIRED_CITE_KEYS - defined_keys
        if missing_keys:
            issues.append(f"references.bib missing keys: {sorted(missing_keys)}")
            score -= 5 * len(missing_keys)
            failed_sections.append("references")
    else:
        issues.append("references.bib does not exist")
        score -= 20
        failed_sections.append("references")

    # ── 4a. Check figure references point to real files ──────────────────
    figures_dir = run_folder / "latex" / "figures"
    all_tex = list(chapters_dir.glob("*.tex"))
    for fpath in all_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text):
            if not (figures_dir / fig_ref).exists():
                issues.append(f"{fpath.name}: missing figure file 'figures/{fig_ref}'")
                score -= 5
                failed_sections.append("figures")

    # ── 4b. Check for forbidden patterns ─────────────────────────────────
    # Only check AGENT-WRITTEN chapters — skip static/protected files.
    # ch01_intro, ch04_slam, and cover are human-written and may intentionally
    # contain em dashes; we cannot and should not penalise them.
    _STATIC = {"ch01_intro.tex", "ch04_slam.tex", "cover.tex"}
    agent_tex = [f for f in chapters_dir.glob("*.tex") if f.name not in _STATIC]
    placeholder_files, emdash_files, center_files = [], [], []
    for fpath in agent_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if "PLACEHOLDER" in text or r"\fbox{\parbox" in text:
            placeholder_files.append(fpath.name)
        # em dash outside \en{} blocks (rough heuristic)
        clean = re.sub(r"\\en\{[^}]*\}", "", text)
        if "\u2014" in clean:
            emdash_files.append(fpath.name)
        if r"\begin{center}" in text:
            center_files.append(fpath.name)

    if placeholder_files:
        issues.append(f"Placeholder boxes found in: {placeholder_files}")
        score -= 5
        failed_sections.append("figures")
    if emdash_files:
        issues.append(f"Em dashes in Hebrew prose: {emdash_files}")
        score -= 3
    if center_files:
        issues.append(f"\\begin{{center}} at document level (bidi crash risk): {center_files}")
        score -= 10
        failed_sections.append("methodology")

    # ── 5. Clamp score and deduplicate failed sections ────────────────────
    score = max(0, min(100, score))
    failed_sections = sorted(set(failed_sections))
    verdict = "PASS" if score >= QUALITY_THRESHOLD else "FAIL"

    # ── 6. Write quality report ───────────────────────────────────────────
    report_path = PROJECT_ROOT / "outputs" / "current" / "quality_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    issue_lines = "\n".join(f"- {i}" for i in issues) if issues else "- None"
    report_content = f"""# Quality Gate Report

**Verdict:** {verdict}
**Score:** {score}/100
**Threshold:** {QUALITY_THRESHOLD}
**Failed Sections:** {failed_sections or 'none'}

## Issues Found

{issue_lines}

## Checks Performed

- Chapter file existence and minimum size
- Equations per chapter (≥2 required)
- Figures per chapter (≥1 required)
- Subsections per chapter (≥3 required)
- Citations per chapter (≥2 required)
- Word count estimate per chapter (≥300 required)
- Required BibTeX keys ({len(REQUIRED_CITE_KEYS)} keys checked)
- Placeholder figure boxes
- Em dashes in Hebrew prose
- \\begin{{center}} at document level (XeLaTeX crash risk)

```json
{{
  "verdict": "{verdict}",
  "score": {score},
  "failed_sections": {json.dumps(failed_sections)}
}}
```
"""
    report_path.write_text(report_content, encoding="utf-8")

    logger.info(f"[Graph] Quality verdict={verdict} score={score} failed={failed_sections}")
    if issues:
        for issue in issues[:5]:  # log first 5 to avoid log spam
            logger.warning(f"[Graph] Quality issue: {issue}")

    return {
        "quality_verdict": verdict,
        "quality_score": score,
        "failed_sections": failed_sections,
    }


# ---------------------------------------------------------------------------
# Node 3: run_remediation
# ---------------------------------------------------------------------------
def run_remediation(state: PipelineState) -> dict:
    """
    Targeted remediation: builds a minimal sub-crew from only the agents
    responsible for the failed sections and re-runs just those tasks.
    """
    count = state["remediation_count"] + 1
    logger.info(f"[Graph] NODE: run_remediation (attempt {count}/{MAX_REMEDIATIONS})")
    logger.info(f"[Graph] Failed sections: {state['failed_sections']}")

    run_folder = Path(state["run_folder"])
    failed = state["failed_sections"]

    agents, tasks = [], []

    # Researcher is needed if content/algorithm sections failed.
    # Give it FileReaderTool so it can read the quality report — without it
    # the LLM tries to use the web-scraper on a local path, spamming errors.
    # Web scraper excluded: remediation works from existing content, not new searches.
    RESEARCH_SECTIONS = {"methodology", "algorithms", "related_work", "equations"}
    if any(s in RESEARCH_SECTIONS for s in failed):
        researcher = create_slam_researcher(tools=[
            FileReaderTool(), SerperDevSearchTool(), ArxivSearchTool()
        ])
        t_research = create_remediation_task(
            agent=researcher,
            failed_sections=[s for s in failed if s in RESEARCH_SECTIONS],
            quality_report_path="outputs/current/quality_report.md",
            output_file="outputs/current/research_briefs.md",
        )
        agents.append(researcher)
        tasks.append(t_research)

    # LaTeX author re-renders any fixed content — pass run_folder so it knows
    # the exact absolute paths to write the chapter files.
    author = create_latex_author(tools=[SafeFileWriterTool(), FileReaderTool()])
    t_latex = create_remediation_task(
        agent=author,
        failed_sections=failed,
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/latex_status.md",
        run_folder=run_folder,
    )
    agents.append(author)
    tasks.append(t_latex)

    if tasks:
        Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        ).kickoff()

    return {
        "remediation_count": count,
        "quality_verdict": "PENDING",
    }
