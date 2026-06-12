"""
src/tasks/tasks_latex_split.py — 3-way LaTeX split (writers A/B/C).
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING
from src.tasks.tasks_latex_rules import _latex_shared_rules

def create_task_latex_a(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """Writer A: abstract + ch01 + ch02 + ch03 + references.bib (5 files)."""
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are LaTeX Writer A. Write the OPENING chapters of a 25–30 page IEEE paper in XeLaTeX (Hebrew).

STEP 1 — READ INPUTS (FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/hebrew_prose.md")
    FileReaderTool("{_STAGING}/figures_manifest.md")
    FileReaderTool("{_STAGING}/research_briefs.md")    ← USE for supplementing thin prose

    If hebrew_prose.md is missing or thin for a chapter — supplement from research_briefs.md.

STEP 2 — WRITE these 5 files ONE AT A TIME using SafeFileWriterTool:

  FILE 1: {chapters_dir}/abstract.tex
      Short abstract (200–300 words Hebrew). No equations, no figures, no \\section command.

  FILE 2: {chapters_dir}/ch01_intro.tex
      ≥2500 words (MINIMUM — this must be a FULL introduction, not a short overview).
      Content: motivation + background, problem statement, contributions (numbered list),
      mathematical formulation preview, paper structure paragraph.
      ≥4 \\subsection{{}}, ≥2 equations, ≥3 \\cite{{}} calls.

  FILE 3: {chapters_dir}/ch02_bio_basis.tex
      ≥3200 words. Biological foundations. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 4: {chapters_dir}/ch03_sensors.tex
      ≥3200 words. Sensor systems. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 5: {bib_path}
      Full BibTeX file with ≥14 topic-relevant entries covering ALL chapters (ch01–ch09).
      Use real author/title/year from the research briefs. Do NOT fabricate citations.

{rules}
""".strip(),
        expected_output=(
            "5 files: abstract.tex, ch01_intro.tex, ch02_bio_basis.tex, ch03_sensors.tex, references.bib. "
            "Confirmation: 'LATEX PART A COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status_a.md",
    )


def create_task_latex_b(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """Writer B: ch04 + ch05 + ch06 (3 files)."""
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are LaTeX Writer B. Write the CORE TECHNICAL chapters of a 25–30 page IEEE paper in XeLaTeX (Hebrew).

STEP 1 — READ INPUTS (FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/hebrew_prose.md")
    FileReaderTool("{_STAGING}/figures_manifest.md")
    FileReaderTool("{bib_path}")                       ← read to know available \\cite{{}} keys
    FileReaderTool("{_STAGING}/research_briefs.md")    ← fallback if hebrew_prose is thin

    If hebrew_prose.md is missing or thin for a chapter — supplement from research_briefs.md.

STEP 2 — WRITE these 3 files ONE AT A TIME using SafeFileWriterTool:

  FILE 1: {chapters_dir}/ch04_slam.tex
      ≥3200 words. SLAM and mapping. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 \\cite{{}} calls.

  FILE 2: {chapters_dir}/ch05_fusion.tex
      ≥3200 words. Sensor fusion. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 \\cite{{}} calls.

  FILE 3: {chapters_dir}/ch06_algorithm.tex
      ≥4000 words. Algorithm/methodology — the most detailed technical chapter.
      ≥6 \\subsection{{}}, ≥6 equations, ≥1 lstlisting pseudocode block, ≥1 figure, ≥1 table.
      CRITICAL: ≥4 \\cite{{}} calls using keys from references.bib. This chapter MUST have citations.

{rules}
""".strip(),
        expected_output=(
            "3 files: ch04_slam.tex, ch05_fusion.tex, ch06_algorithm.tex. "
            "Confirmation: 'LATEX PART B COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status_b.md",
    )


def create_task_latex_c(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """Writer C: ch07 + ch08 + ch09 (3 files)."""
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are LaTeX Writer C. Write the SYSTEM, RESULTS, and CONCLUSION chapters of a 25–30 page IEEE paper in XeLaTeX (Hebrew).

STEP 1 — READ INPUTS (FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/hebrew_prose.md")
    FileReaderTool("{_STAGING}/figures_manifest.md")
    FileReaderTool("{bib_path}")                       ← read to know available \\cite{{}} keys
    FileReaderTool("{_STAGING}/research_briefs.md")    ← USE THIS to expand thin prose sections

    IMPORTANT: If hebrew_prose.md content for ch07/ch08/ch09 is thin (each section
    shorter than 800 words), you MUST supplement heavily from research_briefs.md.
    Write verbose, detailed content — these chapters carry the paper's technical weight.

STEP 2 — WRITE these 3 files ONE AT A TIME using SafeFileWriterTool:

  FILE 1: {chapters_dir}/ch07_oursystem.tex
      ≥3200 words. System design/implementation. ≥5 \\subsection{{}}, ≥4 equations, ≥1 figure, ≥1 table, ≥3 \\cite{{}} calls.
      Include: architecture overview, hardware specs, software pipeline, integration details.

  FILE 2: {chapters_dir}/ch08_results.tex
      ≥4000 words. Results and performance — MUST be the longest chapter after ch06.
      ≥6 \\subsection{{}}, ≥4 equations, ≥2 figures, ≥2 tables, ≥4 \\cite{{}} calls.
      Include: experimental setup, datasets, metrics (ATE/RPE/RMSE), ablation study,
      comparison tables, statistical analysis, failure modes, computational cost.

  FILE 3: {chapters_dir}/ch09_conclusion.tex
      ≥2000 words for conclusion. After the conclusion section, add:
          \\appendix
          \\section{{רשימת סמלים ומשתנים}}
          booktabs table: Symbol | Definition | Units (≥15 rows).

{rules}
""".strip(),
        expected_output=(
            "3 files: ch07_oursystem.tex, ch08_results.tex, ch09_conclusion.tex. "
            "Confirmation: 'LATEX PART C COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status_c.md",
    )


# ---------------------------------------------------------------------------
# Crew-building helpers for split architecture (v6)
# ---------------------------------------------------------------------------
