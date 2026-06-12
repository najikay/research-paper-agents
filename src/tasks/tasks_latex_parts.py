"""
src/tasks/tasks_latex_parts.py — 2-way LaTeX split (part1/part2) + remediation alias.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING
from src.tasks.tasks_latex_rules import _latex_shared_rules

def create_task_latex_part1(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """
    Part 1 of 2: writes abstract + ch01–ch05 + references.bib.
    """
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are writing the FIRST HALF of a 25–30 page IEEE paper in XeLaTeX (Hebrew primary language).

STEP 1 — READ INPUTS (FileReaderTool for each, in order):
    FileReaderTool("{_STAGING}/paper_outline.md")      ← chapter titles, structure, figure names
    FileReaderTool("{_STAGING}/hebrew_prose.md")       ← primary prose content for ALL chapters
    FileReaderTool("{_STAGING}/research_briefs.md")    ← fallback if hebrew_prose.md is missing/empty

    IMPORTANT: If hebrew_prose.md is missing, contains only "HEBREW PROSE COMPLETE", or is
    otherwise empty/unusable — write the Hebrew academic prose yourself directly from the
    research_briefs.md content. Translate/write quality Hebrew academic text. Do NOT skip chapters.

STEP 2 — PLAN: for each file you will write, state in ONE LINE the section title and key content.
    Then write each file IMMEDIATELY — do not plan all files before writing any.

STEP 3 — WRITE these 7 files ONE AT A TIME (write each immediately after planning it):

  *** CRITICAL FILENAME RULE ***
  You MUST use EXACTLY these filenames. Do NOT invent different filenames.
  Do NOT create any .tex files other than the ones listed below.
  Wrong filenames will be INVISIBLE to the compiler and your work will be LOST.

  FILE 1: {chapters_dir}/abstract.tex
      Short abstract (200–300 words Hebrew). No equations, no figures, no \\section command.
      Wrap the text directly — it is inserted inside \\begin{{abstract}}...\\end{{abstract}}.

  FILE 2: {chapters_dir}/ch01_intro.tex     ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for this chapter.
      ≥2500 words. Cover: motivation, problem statement, contributions overview, paper structure.
      Must have: ≥4 \\subsection{{}} blocks, ≥2 equations, ≥2 \\cite{{}} calls.

  FILE 3: {chapters_dir}/ch02_bio_basis.tex ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 2.
      ≥3200 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 4: {chapters_dir}/ch03_sensors.tex   ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 3.
      ≥3200 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 5: {chapters_dir}/ch04_slam.tex      ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 4.
      ≥3200 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 6: {chapters_dir}/ch05_fusion.tex    ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 5.
      ≥3200 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 7: {bib_path}
      Full BibTeX file. Collect ALL \\cite{{}} keys you used in the chapters above.
      MUST contain ≥14 topic-relevant BibTeX entries. Use real author/title/year from
      the research briefs and domain files. Do NOT fabricate citation metadata.

{rules}
""".strip(),
        expected_output=(
            "7 files written: abstract.tex, ch01_intro.tex, ch02–ch05.tex, references.bib. "
            "Each chapter uses Hebrew section title from paper_outline.md. "
            "≥2500w for ch01, ≥3200w for ch02–ch05, ≥5 equations, ≥1 figure (ch02–ch05). "
            "references.bib has ≥14 entries. "
            "Confirmation: 'LATEX PART 1 COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status_part1.md",
    )


def create_task_latex_part2(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """
    Part 2 of 2: writes ch06–ch09 + appendix.
    Context provides hebrew_prose content directly — no need to re-read the file.
    """
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are writing the SECOND HALF of a 25–30 page IEEE paper in XeLaTeX (Hebrew primary language).
Part 1 (abstract, ch01–ch05, references.bib) is already written.
The Hebrew prose content from the previous task is available in your context.

STEP 1 — READ (FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")      ← chapter titles for ch06–ch09
    FileReaderTool("{_STAGING}/figures_manifest.md")   ← exact figure filenames and captions
    FileReaderTool("{_STAGING}/research_briefs.md")    ← fallback for prose if hebrew_prose is missing

    IMPORTANT: If figures_manifest.md does not contain actual filenames (e.g. it says only
    "figures saved" or is a short status message), list the PNG files actually present in the
    figures/ directory by inferring names from the outline, using the format fig_<keyword>.png.

    IMPORTANT: If hebrew_prose.md content is not available in your context, read it:
    FileReaderTool("{_STAGING}/hebrew_prose.md") — if still empty/missing, write Hebrew
    academic prose yourself from research_briefs.md. Do NOT skip any chapter.

STEP 2 — PLAN: for each file, state in ONE LINE the section title and key content.
    Then write each file IMMEDIATELY — do not plan all files before writing any.

STEP 3 — WRITE these 4 files ONE AT A TIME:

  *** CRITICAL FILENAME RULE ***
  You MUST use EXACTLY these filenames. Do NOT invent different filenames.
  Do NOT create any .tex files other than the ones listed below.
  Wrong filenames will be INVISIBLE to the compiler and your work will be LOST.

  FILE 1: {chapters_dir}/ch06_algorithm.tex  ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 6.
      ≥4000 words. The algorithm/methodology chapter — the longest and most detailed.
      Must have: ≥6 \\subsection{{}}, ≥6 equations (numbered), ≥1 lstlisting pseudocode block,
      ≥1 figure, ≥3 citations, complexity analysis table.

  FILE 2: {chapters_dir}/ch07_oursystem.tex  ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 7.
      ≥3200 words. The system design / implementation chapter.
      Must have: ≥5 \\subsection{{}}, ≥4 equations, ≥1 figure, ≥3 citations.

  FILE 3: {chapters_dir}/ch08_results.tex    ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 8.
      ≥4000 words. Simulation/experimental results — detailed quantitative analysis.
      Must have: ≥6 \\subsection{{}}, ≥4 equations, ≥2 figures from manifest, ≥2 results tables,
      ≥3 citations. Quantitative data with numerical values.

  FILE 4: {chapters_dir}/ch09_conclusion.tex ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 9.
      ≥2000 words for conclusion. After the conclusion section, add:
          \\appendix
          \\section{{רשימת סמלים ומשתנים}}
          booktabs table: Symbol | Definition | Units (≥15 rows).

{rules}
""".strip(),
        expected_output=(
            "4 files written: ch06_algorithm.tex (≥4000w), ch07_oursystem.tex (≥3200w), "
            "ch08_results.tex (≥4000w), ch09_conclusion.tex (≥2000w + appendix). "
            "All use Hebrew section titles from paper_outline.md. Labels unique with chapter prefix. "
            "Confirmation: 'LATEX PART 2 COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status.md",
    )


# Keep the single-task version as an alias for backward compat with remediation


def create_task_latex(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """Backward-compatible wrapper used by remediation node. Calls part2 logic."""
    return create_task_latex_part2(author, context, run_folder=run_folder)


# ---------------------------------------------------------------------------
# 3-way LaTeX split (v6 architecture — 3 separate writers)
# ---------------------------------------------------------------------------
