"""
src/graph/nodes.py
==================
LangGraph node functions (v6 — split pipeline with validation gate).

Graph topology:
  run_research_phase → validate_and_fix_research → run_writing_phase
    → run_quality_gate → [PASS → END | FAIL → run_remediation → run_quality_gate]

Each node:
  - Receives the full PipelineState
  - Does its work (runs a CrewAI sub-crew or programmatic check)
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

QUALITY_THRESHOLD = 90   # score below this triggers remediation
MAX_REMEDIATIONS  = 4    # hard cap — prevents infinite loops

# Minimum number of BibTeX entries required in references.bib.
MIN_BIB_ENTRIES = 10

# All content chapters are now agent-written (ch01–ch09 + abstract).
AGENT_CHAPTERS = [
    "abstract.tex",
    "ch01_intro.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]

# Per-chapter minimum requirements — v11: calibrated to actual LLM output.
# DeepSeek V3 reliably produces 1100-1800 words per chapter (LaTeX tokens).
# Thresholds set ~10% below observed output so most chapters pass on first
# attempt, while genuinely thin chapters still get flagged for remediation.
_CHAPTER_MIN_REQS: dict[str, dict] = {
    "abstract.tex":        {"eq": 0, "fig": 0, "sub": 0, "cite": 0, "words": 80},
    "ch01_intro.tex":      {"eq": 1, "fig": 0, "sub": 3, "cite": 2, "words": 1400},
    "ch06_algorithm.tex":  {"eq": 3, "fig": 1, "sub": 5, "cite": 3, "words": 1800},
    "ch07_oursystem.tex":  {"eq": 2, "fig": 1, "sub": 4, "cite": 2, "words": 1600},
    "ch08_results.tex":    {"eq": 2, "fig": 1, "sub": 5, "cite": 3, "words": 1800},
    "ch09_conclusion.tex": {"eq": 0, "fig": 0, "sub": 2, "cite": 1, "words": 700},
}
_DEFAULT_MIN_REQS: dict = {"eq": 2, "fig": 1, "sub": 3, "cite": 2, "words": 1400}

# Domain expert output validation thresholds
_MIN_DOMAIN_BYTES = 500   # files smaller than this are considered failures
_LOOP_PATTERN = re.compile(r"(STEP 1|Let me read|Read existing work)", re.IGNORECASE)
_LOOP_THRESHOLD = 3       # repeated loop phrases = stuck agent


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
# Node 1b: validate_and_fix_research (programmatic + fixer crew)
# ---------------------------------------------------------------------------
def validate_and_fix_research(state: PipelineState) -> dict:
    """
    Validation gate between research and writing phases.

    1. Programmatic check: scan all domain_*.md files for failures
       (empty, trivially short, or stuck-in-loop output).
    2. For any failures: spawn a Fixer crew that writes the missing content.
       The Fixer is a SEPARATE agent — not a retry of the failed one.
    3. Log results and return the count of fixed domains.
    """
    logger.info("[Graph] NODE: validate_and_fix_research")

    staging = PROJECT_ROOT / "outputs" / "current"

    # All domain keys we expect (8 total)
    domain_keys = [
        "vision_ai", "physics", "algorithms", "aerospace", "biology",
        "signal_processing", "control_systems", "ml",
    ]

    failed_domains: list[str] = []

    for key in domain_keys:
        fpath = staging / f"domain_{key}.md"

        # Check 1: file exists and has minimum size
        if not fpath.exists():
            logger.warning(f"[Validate] domain_{key}.md does not exist")
            failed_domains.append(key)
            continue

        content = fpath.read_text(encoding="utf-8", errors="replace")
        size = len(content.encode("utf-8"))

        if size < _MIN_DOMAIN_BYTES:
            logger.warning(f"[Validate] domain_{key}.md too small ({size} bytes)")
            failed_domains.append(key)
            continue

        # Check 2: detect loop patterns (agent said "let me read" N times)
        loop_matches = _LOOP_PATTERN.findall(content)
        if len(loop_matches) >= _LOOP_THRESHOLD:
            logger.warning(
                f"[Validate] domain_{key}.md has loop pattern "
                f"({len(loop_matches)} matches) — agent was stuck"
            )
            failed_domains.append(key)
            continue

        # Check 3: detect shortcut (just "DOMAIN EXPERT COMPLETE" or "DOMAIN SKIP")
        stripped = content.strip()
        if stripped in ("DOMAIN EXPERT COMPLETE", "DOMAIN SKIP") or len(stripped) < 100:
            logger.warning(f"[Validate] domain_{key}.md is a shortcut/stub")
            failed_domains.append(key)
            continue

        logger.info(f"[Validate] domain_{key}.md OK ({size} bytes)")

    if not failed_domains:
        logger.info("[Validate] All domain expert outputs valid — no fixes needed")
        return {"research_fix_count": 0}

    # Read outline for the fixer (it needs the paper structure)
    outline_path = staging / "paper_outline.md"
    outline_content = ""
    if outline_path.exists():
        outline_content = outline_path.read_text(encoding="utf-8", errors="replace")

    logger.info(
        f"[Validate] {len(failed_domains)} domain(s) failed: {failed_domains} — "
        f"spawning Fixer crew"
    )

    from src.crew import build_fixer_crew
    fixer_crew, _ = build_fixer_crew(
        topic=state["topic"],
        failed_domains=failed_domains,
        outline_content=outline_content,
    )
    fixer_crew.kickoff()

    logger.info(f"[Validate] Fixer crew completed for: {failed_domains}")
    return {"research_fix_count": len(failed_domains)}


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


# ---------------------------------------------------------------------------
# Node 2: run_quality_gate  (programmatic — no LLM loop risk)
# ---------------------------------------------------------------------------
def run_quality_gate(state: PipelineState) -> dict:
    """
    Programmatic quality check of generated LaTeX files.
    Scores the paper based on structural completeness and correctness.

    Before scoring, runs:
      1. validate_and_fix_chapters — renames any wrong-named chapter files
      2. _generate_fallback_figures — creates matplotlib figures for missing PNGs
      3. _sanitize_tex_files — fixes common LaTeX errors
    """
    logger.info("[Graph] NODE: run_quality_gate (programmatic)")

    run_folder   = Path(state["run_folder"])

    # Pre-scoring fixups
    from main import (validate_and_fix_chapters, _diversify_stub_figures,
                      _generate_fallback_figures, _sanitize_tex_files)
    validate_and_fix_chapters(run_folder)
    _diversify_stub_figures(run_folder)
    _generate_fallback_figures(run_folder)
    _sanitize_tex_files(run_folder / "latex" / "chapters")

    chapters_dir = run_folder / "latex" / "chapters"
    bib_path     = run_folder / "latex" / "references.bib"

    issues: list[str] = []
    failed_sections: list[str] = []
    score = 100

    # 1. Check all chapter files exist
    missing_files = []
    for fname in AGENT_CHAPTERS:
        fpath = chapters_dir / fname
        if not fpath.exists() or fpath.stat().st_size < 200:
            missing_files.append(fname)
            score -= 8
    if missing_files:
        issues.append(f"Missing or empty chapter files: {missing_files}")
        failed_sections.extend(["introduction", "methodology", "algorithms"])

    # 2. Check structural elements per chapter
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

    # 3. Check references.bib
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

    # 4a. Check figure references
    figures_dir = run_folder / "latex" / "figures"
    all_tex = list(chapters_dir.glob("*.tex"))
    missing_fig_penalty = 0
    for fpath in all_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text):
            if not (figures_dir / fig_ref).exists():
                issues.append(f"{fpath.name}: missing figure file 'figures/{fig_ref}'")
                failed_sections.append("figures")
                if missing_fig_penalty < 20:
                    missing_fig_penalty += 2
    score -= missing_fig_penalty

    # 4b. Check for forbidden patterns
    _STATIC = {"cover.tex"}
    agent_tex = [f for f in chapters_dir.glob("*.tex") if f.name not in _STATIC]
    placeholder_files, emdash_files, center_files = [], [], []
    for fpath in agent_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if "PLACEHOLDER" in text or r"\fbox{\parbox" in text:
            placeholder_files.append(fpath.name)
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

    # 5. Clamp score and deduplicate
    score = max(0, min(100, score))
    failed_sections = sorted(set(failed_sections))
    verdict = "PASS" if score >= QUALITY_THRESHOLD else "FAIL"

    # 6. Write quality report
    report_path = PROJECT_ROOT / "outputs" / "current" / "quality_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    issue_lines = "\n".join(f"- {i}" for i in issues) if issues else "- None"

    # Build dynamic thresholds summary from actual _CHAPTER_MIN_REQS
    _def = _DEFAULT_MIN_REQS
    thresholds_lines = [f"- Default: eq>={_def['eq']}, fig>={_def['fig']}, sub>={_def['sub']}, cite>={_def['cite']}, words>={_def['words']}"]
    for fname, reqs in sorted(_CHAPTER_MIN_REQS.items()):
        diffs = [f"{k}>={v}" for k, v in reqs.items() if v != _def.get(k)]
        if diffs:
            thresholds_lines.append(f"- {fname}: {', '.join(diffs)}")

    report_content = f"""# Quality Gate Report

**Verdict:** {verdict}
**Score:** {score}/100
**Threshold:** {QUALITY_THRESHOLD}
**Failed Sections:** {failed_sections or 'none'}

## Issues Found

{issue_lines}

## Per-Chapter Thresholds

{chr(10).join(thresholds_lines)}
- references.bib: >={MIN_BIB_ENTRIES} entries
- Missing figure files: <=-20 total penalty (capped)

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
        for issue in issues[:5]:
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
    Targeted remediation: builds a minimal sub-crew that reads the quality
    report and fixes ONLY the failing chapter files in-place.
    """
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
            # Capture ALL chapter-level issues (words, equations, figures, citations, subsections)
            if line.startswith("- ch") and any(k in line for k in ("words", "equations", "figures", "citations", "subsections")):
                chapter_issues.append(stripped)
            elif line.startswith("- Missing") and "chapter" in line.lower():
                chapter_issues.append(stripped)
    # Always pass chapter-specific issues so remediation knows WHICH files to fix
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
