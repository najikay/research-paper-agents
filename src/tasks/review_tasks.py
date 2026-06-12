"""
src/tasks/review_tasks.py
=========================
Factory functions for quality review and remediation tasks.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

_STAGING = "outputs/current"


def create_task_review(editor: Agent, context: list[Task]) -> Task:
    """Create the peer-review quality gate task."""
    return Task(
        description=f"""
Conduct a peer review of all LaTeX files and output a report to {_STAGING}/quality_report.md.

**MANDATORY**: Your report MUST end with a machine-readable JSON verdict block:

```json
{{
  "verdict": "PASS" or "FAIL",
  "score": <integer 0-100>,
  "failed_sections": ["section_name", ...]
}}
```

Score below 75 = FAIL. Failed sections must use these exact names if applicable:
methodology, algorithms, related_work, equations, introduction, conclusion, references, figures.
""",
        expected_output=f"Quality report in {_STAGING}/quality_report.md ending with a JSON verdict block.",
        agent=editor,
        context=context,
        output_file=f"{_STAGING}/quality_report.md"
    )


def create_remediation_task(
    agent: Agent,
    failed_sections: list[str],
    quality_report_path: str,
    output_file: str,
    run_folder: Path | None = None,
) -> Task:
    """Create a targeted fix task for chapters that failed the quality gate."""
    sections_str = ", ".join(failed_sections)
    paths_note = ""
    bib_path = "latex/references.bib"
    if run_folder is not None:
        chapters_dir = run_folder / "latex" / "chapters"
        bib_path = run_folder / "latex" / "references.bib"
        paths_note = f"""
FILE PATHS — CRITICAL: chapter .tex files are stored in the run folder, NOT in outputs/current/.

READ existing chapters with FileReaderTool (use these EXACT paths):
    {chapters_dir}/ch01_intro.tex
    {chapters_dir}/ch02_bio_basis.tex
    {chapters_dir}/ch03_sensors.tex
    {chapters_dir}/ch04_slam.tex
    {chapters_dir}/ch05_fusion.tex
    {chapters_dir}/ch06_algorithm.tex
    {chapters_dir}/ch07_oursystem.tex
    {chapters_dir}/ch08_results.tex
    {chapters_dir}/ch09_conclusion.tex
    {bib_path}

WRITE fixed chapters with SafeFileWriterTool to the SAME paths above.
    Do NOT write to outputs/current/ — write directly to the run folder paths.
"""

    return Task(
        description=f"""
REMEDIATION TASK. Expand and fix chapters that failed the quality gate.

STEP 1 — Read the quality report AND the references.bib:
    FileReaderTool("{quality_report_path}")
    FileReaderTool("{bib_path}")  <- you need the \\cite{{}} keys for adding citations

STEP 2 — For EACH failing chapter listed below, read + expand + write back.
    Process ALL failing chapters — do not stop after fixing just one.

STEP 3 — For EACH failing chapter:
    a) Read it: FileReaderTool("<path>")
    b) KEEP ALL existing content — do NOT delete or rewrite from scratch.
    c) ADD new content. You MUST add at least 400 words per chapter, using these techniques:
       - Add 2 new \\subsection{{}} blocks with 250+ Hebrew words each
       - Extend existing subsections: add technical comparisons, mathematical derivations,
         parameter sensitivity analysis, implementation considerations
       - Add equations: \\begin{{equation}} ... \\label{{eq:chNN_name}} \\end{{equation}}
       - Add \\cite{{}} calls using REAL keys from references.bib (read it in Step 1)
       - Add comparison tables (\\begin{{table}}[htbp])
       - Wrap English terms in \\en{{}}: \\en{{SLAM}}, \\en{{EKF}}, etc.
    d) Write the ENTIRE expanded file using SafeFileWriterTool (not just new parts).

    SPECIFIC FIX RULES:
    * "words~N<M": add at least (M - N + 200) words of Hebrew academic prose
    * "citations=N<M": add \\cite{{}} calls using keys from references.bib
    * "equations=N<M": add numbered equations with \\label{{eq:chNN_...}}
    * "subsections=N<M": add new \\subsection{{}} blocks with 200+ words each
    * "em dashes": replace every — (U+2014) with colon (:) or comma (,)

    EM DASH RULE: character — is FORBIDDEN. Use colon (:) or comma (,).
    INLINE ENGLISH: every English word in Hebrew prose MUST be in \\en{{}}.

STEP 4 — After fixing ALL chapters, confirm: 'REMEDIATION COMPLETE'.

Failed sections to fix: [{sections_str}]
Do NOT modify chapters that passed — only fix the ones listed above.
{paths_note}
""",
        expected_output=(
            f"Fixed chapter file(s) addressing failures in: {sections_str}. "
            f"Confirmation: 'REMEDIATION COMPLETE'."
        ),
        agent=agent,
        output_file=output_file,
    )
