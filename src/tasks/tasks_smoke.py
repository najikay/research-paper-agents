"""
src/tasks/tasks_smoke.py — 2-task smoke pipeline factories.
"""
from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

from src.tasks.staging import _STAGING
from src.tasks.tasks_research_core import create_task_outline


def create_task_latex_smoke(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """
    Single combined task for --smoke mode.
    Writes ALL 11 files (abstract + ch01–ch09 + references.bib) in one pass.
    Content is minimal-but-quality-gate-passing — no prose step needed.
    """
    latex_dir    = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path     = f"{latex_dir}/references.bib"

    return Task(
        description=f"""
Write ALL 11 XeLaTeX files for a minimal IEEE paper. Speed is critical — write each file
IMMEDIATELY, one after another. Do NOT re-read files between writes.

STEP 1 — Read the outline ONCE:
    FileReaderTool("{_STAGING}/paper_outline.md")
    Extract all Hebrew section titles. Then write all files without stopping.

STEP 2 — Write in this exact order, calling SafeFileWriterTool once per file:

  *** CRITICAL: Use EXACTLY these filenames. Do NOT invent other names. ***

  1. {chapters_dir}/abstract.tex
     \\selectlanguage{{hebrew}}
     150 Hebrew words summarising the paper. No \\section. No equations.

  2. {chapters_dir}/ch01_intro.tex      ← EXACT name
     \\selectlanguage{{hebrew}} + \\section{{<Hebrew title from outline>}} + \\label{{sec:ch01}}
     ≥4 \\subsection, ≥1 \\begin{{equation}}...\\end{{equation}}, ≥2 \\cite{{}}, ≥1200 Hebrew words.

  3. {chapters_dir}/ch02_bio_basis.tex  ← EXACT name
  4. {chapters_dir}/ch03_sensors.tex    ← EXACT name
  5. {chapters_dir}/ch04_slam.tex       ← EXACT name
  6. {chapters_dir}/ch05_fusion.tex     ← EXACT name
  7. {chapters_dir}/ch06_algorithm.tex  ← EXACT name
  8. {chapters_dir}/ch07_oursystem.tex  ← EXACT name
     Each: \\selectlanguage{{hebrew}} + \\section + \\label, ≥5 \\subsection, ≥4 equations,
     ≥1 figure using figures/fig_stub.png, ≥2 \\cite, ≥1500 Hebrew words.
     ch06 must include one \\begin{{lstlisting}}...\\end{{lstlisting}} pseudocode block.

  9. {chapters_dir}/ch08_results.tex    ← EXACT name
     Same as ch02–ch07 above but ≥2 figures using figures/fig_stub.png and ≥1800 words.

  10. {chapters_dir}/ch09_conclusion.tex ← EXACT name
     \\selectlanguage{{hebrew}} + \\section + \\label, ≥3 \\subsection, ≥1 \\cite, ≥800 Hebrew words.

  11. {bib_path}
     ≥14 BibTeX entries. Keys MUST match every \\cite{{}} used above. No undefined keys.

ABSOLUTE RULES (breaking any of these crashes XeLaTeX):
    • \\selectlanguage{{hebrew}} MUST be the first line of every chapter file.
    • Every English word in Hebrew prose: \\en{{SLAM}}, \\en{{EKF}}, \\en{{UAV}}, etc.
    • ALL math/Greek in \\caption{{}} or \\section{{}} MUST be inside $...$  (e.g. $\\sigma$, $\\alpha$).
    • Figures: use \\begin{{figure}}[htbp]\\centering ... \\end{{figure}}. NEVER \\begin{{center}} or [H].
    • NO em dash character (—), \\textemdash, or \\textendash anywhere in Hebrew prose.
    • Code blocks: wrap in \\begin{{english}}...\\end{{english}} around the lstlisting.
    • Every \\label{{}} must be globally unique — prefix with chapter: \\label{{eq:ch03_1}}.
    • Use SafeFileWriterTool for EVERY file. Write file 1, then 2, then 3 … do not skip any.
""".strip(),
        expected_output=(
            "11 files written: abstract.tex + ch01–ch09.tex + references.bib. "
            "Minimal valid XeLaTeX passing quality gate. "
            "Confirmation: 'SMOKE LATEX COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status.md",
    )


def create_smoke_tasks(
    director,
    author,
    topic: str,
    run_folder: Path | None = None,
) -> list[Task]:
    """
    2-task smoke pipeline: outline (5 iter) → latex_all (45 iter).
    Total ~35–50 LLM calls → ~3–8 minutes.
    No research, no domain experts, no figures, no prose step.
    """
    t_outline = create_task_outline(director, topic)
    t_latex   = create_task_latex_smoke(author, [t_outline], run_folder=run_folder)
    return [t_outline, t_latex]
