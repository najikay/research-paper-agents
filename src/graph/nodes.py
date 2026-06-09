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

# Minimum number of BibTeX entries required in references.bib.
# Topic-agnostic — agents cite whatever is relevant to the dynamic topic.
MIN_BIB_ENTRIES = 10

# All content chapters are now agent-written (ch01–ch09 + abstract).
# cover.tex is the only static file (excluded from quality checks).
AGENT_CHAPTERS = [
    "abstract.tex",
    "ch01_intro.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]

# Per-chapter minimum requirements — relaxed for structural chapters
# that naturally have fewer equations/figures (intro, conclusion, abstract).
_CHAPTER_MIN_REQS: dict[str, dict] = {
    "abstract.tex":        {"eq": 0, "fig": 0, "sub": 0, "cite": 0, "words": 50},
    "ch01_intro.tex":      {"eq": 1, "fig": 0, "sub": 2, "cite": 2, "words": 400},
    "ch09_conclusion.tex": {"eq": 0, "fig": 0, "sub": 2, "cite": 1, "words": 300},
}
_DEFAULT_MIN_REQS: dict = {"eq": 3, "fig": 1, "sub": 3, "cite": 2, "words": 600}


# ---------------------------------------------------------------------------
# Node 1: run_main_pipeline
# ---------------------------------------------------------------------------
def run_main_pipeline(state: PipelineState) -> dict:
    """
    Runs the full CrewAI pipeline (outline → research → figures → latex).
    """
    from src.crew import build_crew  # lazy import avoids circular deps

    logger.info("[Graph] NODE: run_main_pipeline")
    fast_mode  = state.get("fast_mode",  False)
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
    for fname in AGENT_CHAPTERS:
        fpath = chapters_dir / fname
        if not fpath.exists():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")

        reqs = _CHAPTER_MIN_REQS.get(fname, _DEFAULT_MIN_REQS)
        eq_count   = len(re.findall(r"\\begin\{equation\}", text))
        fig_count  = len(re.findall(r"\\includegraphics", text))
        sub_count  = len(re.findall(r"\\subsection\{", text))
        cite_count = len(re.findall(r"\\cite\{", text))
        word_est   = len(text.split())

        chapter_issues = []
        if eq_count < reqs["eq"]:
            chapter_issues.append(f"equations={eq_count}<{reqs['eq']}")
            score -= 3
        if fig_count < reqs["fig"]:
            chapter_issues.append(f"figures={fig_count}<{reqs['fig']}")
            score -= 3
        if sub_count < reqs["sub"]:
            chapter_issues.append(f"subsections={sub_count}<{reqs['sub']}")
            score -= 2
        if cite_count < reqs["cite"]:
            chapter_issues.append(f"citations={cite_count}<{reqs['cite']}")
            score -= 2
        if word_est < reqs["words"]:
            chapter_issues.append(f"words≈{word_est}<{reqs['words']}")
            score -= 4
            failed_sections.append("methodology")

        if chapter_issues:
            issues.append(f"{fname}: " + ", ".join(chapter_issues))

    # ── 3. Check references.bib has enough entries ───────────────────────
    # Topic-agnostic: we require a minimum count, not specific key names,
    # since ch01 and ch04 are now dynamic and cite topic-appropriate references.
    if bib_path.exists():
        bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
        entry_count = len(re.findall(r"@\w+\{", bib_text))
        if entry_count < MIN_BIB_ENTRIES:
            issues.append(f"references.bib has only {entry_count} entries (need ≥{MIN_BIB_ENTRIES})")
            score -= max(0, (MIN_BIB_ENTRIES - entry_count) * 2)
            failed_sections.append("references")
    else:
        issues.append("references.bib does not exist")
        score -= 20
        failed_sections.append("references")

    # ── 4a. Check figure references point to real files ──────────────────
    # Penalty is capped at -20 total so that a single component failure
    # (e.g. visualization engineer timing out) doesn't crater the whole score.
    figures_dir = run_folder / "latex" / "figures"
    all_tex = list(chapters_dir.glob("*.tex"))
    missing_fig_penalty = 0
    for fpath in all_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text):
            if not (figures_dir / fig_ref).exists():
                issues.append(f"{fpath.name}: missing figure file 'figures/{fig_ref}'")
                failed_sections.append("figures")
                if missing_fig_penalty < 20:   # cap cascading damage
                    missing_fig_penalty += 2
    score -= missing_fig_penalty

    # ── 4b. Check for forbidden patterns ─────────────────────────────────
    # Only cover.tex is static now — all chapter files are agent-written.
    _STATIC = {"cover.tex"}
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
        score -= 2
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
- Equations per chapter (≥3 default; abstract=0, ch01=1, ch09=0)
- Figures per chapter (≥1 default; abstract/ch01/ch09=0)
- Subsections per chapter (≥3 default; abstract=0, ch01/ch09=2)
- Citations per chapter (≥2 default; abstract=0, ch09=1)
- Word count estimate per chapter (≥600 default; abstract=50, ch01=400, ch09=300)
- references.bib entry count (≥{MIN_BIB_ENTRIES} required)
- Missing figure files (≤-20 total penalty, capped to prevent cascade)
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
