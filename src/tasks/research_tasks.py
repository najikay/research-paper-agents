"""
src/tasks/research_tasks.py
============================
Factory functions for the 5 NavigatorCrew tasks.
Architecture: Robust Sequential Pipeline v4.0.

All intermediate outputs are staged to outputs/current/ during a run.
main.py moves them to the per-run archive folder on completion and cleans up.
"""

from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.config import logger

# Staging directory for all intermediate outputs during a run.
# Always use this constant — never hardcode "outputs/" directly.
_STAGING = "outputs/current"


def create_task_outline(director: Agent, topic: str) -> Task:
    return Task(
        description=f"""
Analyze the topic '{topic}' and create a chapter-by-chapter outline for a 25–30 page IEEE paper.
Save the outline to {_STAGING}/paper_outline.md.

STEP 1 — Decompose '{topic}' into 8 content chapters:
    Chapter 1: Introduction — problem statement, motivation, contributions, paper roadmap
    Chapters 2–7: Core technical sub-domains SPECIFIC to '{topic}' (you decide the split)
    Chapter 8: Simulation/Experimental Results and Performance Analysis
    Chapter 9: Conclusion, Limitations, Future Work

STEP 2 — For each chapter specify:
    - Hebrew title for \\section{{...}} (use appropriate Hebrew technical terms for the domain)
    - 3–5 subsection titles (Hebrew)
    - 3+ equations (with LaTeX math, e.g. $x_{{k+1}} = Ax_k + Bu_k$)
    - 2 figure filenames: fig_<short_description>.png (exactly 9 figures total across all chapters)
    - 1 table topic (comparison or summary)
    - 3–5 English search keywords for Serper/ArXiv queries (ALL searches must be in English)

STEP 3 — Write the complete outline to {_STAGING}/paper_outline.md.
    The outline MUST be self-contained: downstream agents read only this file to understand
    the paper structure. Be specific about equations, figure content, and section labels.
""".strip(),
        expected_output=(
            f"Detailed chapter-by-chapter outline in {_STAGING}/paper_outline.md with topic-specific "
            f"Hebrew chapter titles, subsections, equations, figure filenames, and search keywords. "
            f"Confirmation: 'OUTLINE COMPLETE'."
        ),
        agent=director,
        output_file=f"{_STAGING}/paper_outline.md"
    )


def create_task_research(researcher: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Produce 8 detailed technical research briefs based on {_STAGING}/paper_outline.md.
Each brief must provide enough material for a 3–4 page chapter (600+ words of content).

For each sub-domain include:
  • 2–3 paragraph technical summary (Hebrew-language prose ready to paste)
  • All relevant equations with full variable definitions
  • Algorithm descriptions (pseudocode if applicable)
  • 3–5 specific BibTeX citations with author, title, year
  • Figure descriptions (what to plot and why)
  • A comparison table (at least 3 alternatives compared on 3+ criteria)

Write to {_STAGING}/research_briefs.md.
""".strip(),
        expected_output=f"8 structured research briefs in {_STAGING}/research_briefs.md, each providing ≥600 words of technical content. Confirmation: 'RESEARCH COMPLETE'.",
        agent=researcher,
        context=context,
        output_file=f"{_STAGING}/research_briefs.md"
    )


def create_task_figures(visualizer: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    latex_figures = str(run_folder / "latex" / "figures") if run_folder else "latex/figures"
    return Task(
        description=f"""
Generate 9 IEEE-standard publication-quality figures as 300 DPI PNG files.

STEP 0 — READ THE OUTLINE to understand the topic and required figures:
    FileReaderTool("{_STAGING}/paper_outline.md")
    The outline lists required figures per chapter — use those filenames and topics.
    If the outline does not specify filenames, invent clear topic-appropriate names
    following the convention: fig_<topic_keyword>.png (e.g. fig_trajectory_3d.png).

STEP 1 — HOW TO CALL PythonCodeExecutorTool for each figure:
    - `code`: a complete matplotlib script ending with
      plt.savefig(output_path, dpi=300, bbox_inches='tight') and plt.close('all')
    - `output_filename`: the exact PNG filename (e.g. 'fig_trajectory_3d.png')

CRITICAL — `output_path` is a variable that the tool injects automatically into your script.
Do NOT hardcode any file path in plt.savefig(). Always write:
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
The tool will save the file to {latex_figures}/ automatically.

STEP 2 — GENERATE EXACTLY 9 FIGURES (call the tool once per figure, in order):
    Use the figures specified in the outline. At minimum, produce figures covering:
    1. A comparative pipeline/architecture flowchart for the paper's main contribution
    2. A 3D trajectory or spatial map (mpl_toolkits.mplot3d)
    3. A sensor confidence heatmap or occupancy grid (plt.imshow)
    4. A signal/spectrum analysis figure (spectrogram or time-frequency plot)
    5. A range/velocity or signal processing map
    6. An estimation uncertainty plot (e.g. EKF covariance ellipses or particle filter)
    7. A performance comparison bar chart (multiple algorithms × multiple metrics)
    8. A system architecture block diagram
    9. A multi-panel results summary (RMSE / ATE / RPE or equivalent metrics)

    Name each file to match the outline's specifications.

FIGURE QUALITY REQUIREMENTS:
    - plt.style.use('seaborn-v0_8-whitegrid') or equivalent clean base style
    - Wide/multi-panel figures: figsize=(16, 7) or larger
    - Minimum font size for ANY text element: 11pt
      (ax.tick_params(labelsize=11), ax.set_xlabel(..., fontsize=12))
    - All axes must have labels with units. Legends required when ≥2 series.
    - Include Hebrew labels/captions where specified in the outline.
    - Use plt.tight_layout() before savefig.

STEP 3 — After all 9 figures are saved, write a manifest to {_STAGING}/figures_manifest.md:
    One row per figure: filename | title | Hebrew caption | \\label{{fig:...}} key
""".strip(),
        expected_output=f"9 PNG files saved to {latex_figures}/ and manifest at {_STAGING}/figures_manifest.md listing all 9 filenames with captions and label keys. Confirmation: 'FIGURES COMPLETE'.",
        agent=visualizer,
        context=context,
        output_file=f"{_STAGING}/figures_status.md"  # separate from manifest content written via SafeFileWriterTool
    )


def create_task_domain_expert(
    expert: Agent,
    domain_key: str,
    domain_description: str,
    context: list[Task],
) -> Task:
    """
    Generic domain-expert enrichment task.
    Each specialist reads the outline + research briefs and contributes
    domain-specific depth (equations, algorithms, insights, references).
    If the topic is outside their domain they write a single DOMAIN SKIP line.
    """
    return Task(
        description=f"""
You are a PhD-level domain specialist contributing technical depth to an academic paper.

STEP 1 — Read existing work (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/research_briefs.md")

STEP 2 — Assess relevance of your domain to this paper topic:
    Your domain: {domain_description}

STEP 3a — If your domain IS relevant to the topic:
    Contribute content NOT already covered in the research briefs:
    • Domain-specific equations with full derivations and variable definitions
      (numbered, LaTeX-ready format)
    • Algorithms, methods, or design principles unique to your field
    • Physical, biological, or theoretical insights that deepen any chapter
    • 3–5 key BibTeX-formatted references from your domain
      (format: @article{{Key, author=..., title=..., journal=..., year=..., doi=...}})
    Precision standard: PhD-level. Cite primary sources. No padding.

STEP 3b — If your domain has NO meaningful intersection with this topic:
    Write exactly one line: "DOMAIN SKIP: [brief reason]"
    Do NOT pad with generic content — professional silence is valued.

Write your output to {_STAGING}/domain_{domain_key}.md
""".strip(),
        expected_output=(
            f"Domain contribution at {_STAGING}/domain_{domain_key}.md "
            f"with equations, algorithms, and references, OR a single 'DOMAIN SKIP:' line. "
            f"Confirmation: 'DOMAIN EXPERT COMPLETE'."
        ),
        agent=expert,
        context=context,
        output_file=f"{_STAGING}/domain_{domain_key}.md",
    )


def create_task_hebrew_prose(writer: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Read all research and domain-expert materials, then write polished Hebrew academic
prose for ALL chapters (CH01–CH09). Save prose to {_STAGING}/hebrew_prose.md.

STEP 1 — READ ALL INPUTS (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")         ← chapter structure, titles, equations
    FileReaderTool("{_STAGING}/research_briefs.md")       ← primary technical input
    FileReaderTool("{_STAGING}/domain_vision_ai.md")      ← Vision-AI expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_physics.md")        ← Physics expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_algorithms.md")     ← Algorithms expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_aerospace.md")      ← Aerospace/Marine expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_biology.md")        ← Biology expert (if not DOMAIN SKIP)
    Files that begin with "DOMAIN SKIP:" have no relevant content — skip them.

STEP 2 — Write Hebrew prose for ALL nine chapters to {_STAGING}/hebrew_prose.md.
    Use SafeFileWriterTool to write the file. Write ALL chapters in a SINGLE tool call.
    Do NOT split across multiple files. Do NOT write to hebrew_prose_remaining.md.

    TARGET: 25–30 printed pages total (~16,000–20,000 Hebrew words).
    - ch01 (introduction): 1800–2400 words
    - ch02–ch05: 2400–3000 words each
    - ch06 (algorithm): 3000–3600 words
    - ch07 (system): 2400–3000 words
    - ch08 (results): 3000–3600 words
    - ch09 (conclusion): 1400–1800 words

    Per-chapter content:
        • Section marker: ## CH01: <Hebrew title from outline>
        • 3+ subsections marked: ### <Hebrew subsection title>
        • Inline markers for equations: [EQUATION: description]
        • Inline markers for figures: [FIGURE: fig_filename.png]
        • Inline markers for tables: [TABLE: description]
        • Citation markers: [CITE: AuthorYear]

    EM DASH PROHIBITION (ABSOLUTE RULE — violating this breaks the PDF):
        The character — (U+2014) is COMPLETELY FORBIDDEN anywhere in the output.
        Use colon (:) or comma (,) instead. Check every sentence.

    Language rules:
        • Prose in Hebrew. Technical acronyms stay in English: SLAM, EKF, LiDAR, UAV, IMU.
        • Do NOT write LaTeX commands — only prose text with inline markers.

STEP 3 — After writing, output a short confirmation: 'HEBREW PROSE COMPLETE'.
    Do NOT output the full prose in your final response — just the confirmation.
    The prose is already saved to the file by SafeFileWriterTool.
""".strip(),
        expected_output=(
            f"All 9 chapters written to {_STAGING}/hebrew_prose.md via SafeFileWriterTool. "
            f"≥1800 words per chapter (ch06/ch08 ≥3000). Zero em dash characters. Confirmation: 'HEBREW PROSE COMPLETE'."
        ),
        agent=writer,
        context=context,
        output_file=f"{_STAGING}/hebrew_prose_status.md",
    )


def _latex_shared_rules(chapters_dir: str, bib_path: str, latex_dir: str) -> str:
    """Shared LaTeX writing rules injected into both latex task descriptions."""
    return f"""
CONTENT DEPTH — targeting 25–30 printed pages total:
    • ch01: ≥1800 Hebrew words, ≥4 subsections, ≥2 equations
    • ch02–ch05: ≥2400 Hebrew words each, ≥6 subsections, ≥5 equations, ≥1 figure, ≥1 table
    • ch06 (algorithm): ≥3000 Hebrew words, ≥6 subsections, ≥6 equations, ≥1 lstlisting, ≥1 figure
    • ch07 (system): ≥2400 Hebrew words, ≥5 subsections, ≥4 equations, ≥1 figure
    • ch08 (results): ≥3000 Hebrew words, ≥6 subsections, ≥4 equations, ≥2 figures, ≥1 table
    • ch09 (conclusion): ≥1400 Hebrew words, ≥3 subsections

FIGURE WIDTH AND PLACEMENT RULES:
    • Single-column figures: \\begin{{figure}}[htbp] with [width=0.98\\columnwidth]
    • Wide figures (flowcharts, multi-panel): \\begin{{figure*}}[htbp] with [width=\\textwidth]
    • NEVER use [H] for float placement — it causes overlapping in two-column IEEE.
    • NEVER use width smaller than 0.9\\columnwidth.

LABEL UNIQUENESS — every \\label{{}} must be globally unique:
    • Prefix with chapter ID: \\label{{fig:ch02_name}}, \\label{{eq:ch03_name}}, \\label{{tab:ch05_name}}
    • NEVER reuse a label name from another chapter.

INLINE ENGLISH — every English word inside Hebrew prose MUST be wrapped:
    \\en{{SLAM}}, \\en{{EKF-SLAM}}, \\en{{LiDAR}}, \\en{{ORB-SLAM3}}, \\en{{IMU}}, etc.
    Math environments ($...$, \\begin{{equation}}) do NOT need \\en{{}}.
    Section titles mixing Hebrew+English: wrap the English part in \\en{{}}.

EM DASH RULE — character — is FORBIDDEN in Hebrew prose.
    Use colon (:) or comma (,). Only permitted inside \\en{{}} expansions.

FIGURES — CRITICAL:
    Read {_STAGING}/figures_manifest.md and use ONLY the exact filenames listed there.
    NEVER invent figure names. Never write \\fbox{{\\parbox{{...PLACEHOLDER...}}}}.
    Format: \\includegraphics[width=0.98\\columnwidth]{{figures/EXACT_NAME.png}}

PSEUDOCODE / CODE BLOCKS — RTL-SAFE lstlisting:
    Code/pseudocode MUST be wrapped in english environment for correct LTR rendering:
    \\begin{{english}}
    \\begin{{lstlisting}}[language=Python, caption={{\\texthebrew{{כותרת בעברית}}}}]
    ... pseudocode here (always LTR English) ...
    \\end{{lstlisting}}
    \\end{{english}}
    The \\begin{{algorithm}} environment is NOT available. Use lstlisting for all pseudocode.
    lstlisting captions with Hebrew: wrap the Hebrew text in \\texthebrew{{}}.

RTL / LTR DIRECTION — CRITICAL for correct rendering:
    • The document is RTL (Hebrew). All code, algorithms, and pseudocode are LTR (English).
    • NEVER use \\textemdash or \\textendash in Hebrew text. Use colon (:) or comma (,).
    • Tables with mixed Hebrew/English: each cell handles its own direction automatically.
    • Figure captions: Hebrew text renders RTL, English terms in \\en{{}} render LTR.

FLOAT PLACEMENT — prevent overlapping content:
    • Figures: use \\begin{{figure}}[htbp] (NOT [H] which causes overlap in two-column).
    • Tables: use \\begin{{table}}[htbp] for consistency.
    • Wide figures (flowcharts, multi-panel): use \\begin{{figure*}}[htbp] with [width=\\textwidth].

COLUMN WIDTH — IEEE two-column is NARROW (~3.5 inches per column):
    • Tables: max 4 columns in single-column mode. For wider tables use \\begin{{table*}} (spans both columns).
    • Equations: keep them SHORT. If an equation has >5 terms, split with \\begin{{align}} + \\\\ line breaks.
    • Do NOT put long equations with many subscripts/superscripts in a single \\begin{{equation}} — they will overflow.

MATH IN CAPTIONS — CRITICAL (prevents PDF crash):
    ALL math symbols and Greek letters inside \\caption{{}} and \\section{{}} MUST be in math mode.
    Write: $2\\sigma$, $\\alpha$, $\\delta_{{k}}$, $\\hat{{x}}$
    NOT: 2-\\sigma, \\alpha, \\delta_k (these crash XeLaTeX outside math environments).
    Rule: if it has a backslash and is not \\en{{}} or \\label{{}} or \\ref{{}} — wrap it in $...$

PROTECTED (never overwrite):
    {latex_dir}/main.tex    {chapters_dir}/cover.tex

Use SafeFileWriterTool for EVERY file. COMPILER: XeLaTeX.
WRITE EACH FILE IMMEDIATELY after completing it — do not buffer all files before writing.
""".strip()


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
      ≥1800 words. Cover: motivation, problem statement, contributions overview, paper structure.
      Must have: ≥4 \\subsection{{}} blocks, ≥2 equations, ≥2 \\cite{{}} calls.

  FILE 3: {chapters_dir}/ch02_bio_basis.tex ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 2.
      ≥2400 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 4: {chapters_dir}/ch03_sensors.tex   ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 3.
      ≥2400 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 5: {chapters_dir}/ch04_slam.tex      ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 4.
      ≥2400 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 6: {chapters_dir}/ch05_fusion.tex    ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 5.
      ≥2400 words. ≥6 \\subsection{{}}, ≥5 equations, ≥1 figure, ≥1 table, ≥3 citations.

  FILE 7: {bib_path}
      Full BibTeX file. Collect ALL \\cite{{}} keys you used in the chapters above.
      MUST contain ≥14 topic-relevant BibTeX entries. Use real author/title/year from
      the research briefs and domain files. Do NOT fabricate citation metadata.

{rules}
""".strip(),
        expected_output=(
            "7 files written: abstract.tex, ch01_intro.tex, ch02–ch05.tex, references.bib. "
            "Each chapter uses Hebrew section title from paper_outline.md. "
            "≥1800w for ch01, ≥2400w for ch02–ch05, ≥5 equations, ≥1 figure (ch02–ch05). "
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
      ≥3000 words. The algorithm/methodology chapter — the longest and most detailed.
      Must have: ≥6 \\subsection{{}}, ≥6 equations (numbered), ≥1 lstlisting pseudocode block,
      ≥1 figure, ≥3 citations, complexity analysis table.

  FILE 2: {chapters_dir}/ch07_oursystem.tex  ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 7.
      ≥2400 words. The system design / implementation chapter.
      Must have: ≥5 \\subsection{{}}, ≥4 equations, ≥1 figure, ≥3 citations.

  FILE 3: {chapters_dir}/ch08_results.tex    ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 8.
      ≥3000 words. Simulation/experimental results — detailed quantitative analysis.
      Must have: ≥6 \\subsection{{}}, ≥4 equations, ≥2 figures from manifest, ≥2 results tables,
      ≥3 citations. Quantitative data with numerical values.

  FILE 4: {chapters_dir}/ch09_conclusion.tex ← EXACT filename, do NOT change
      Use the Hebrew section title from paper_outline.md for chapter 9.
      ≥1400 words for conclusion. After the conclusion section, add:
          \\appendix
          \\section{{רשימת סמלים ומשתנים}}
          booktabs table: Symbol | Definition | Units (≥15 rows).

{rules}
""".strip(),
        expected_output=(
            "4 files written: ch06_algorithm.tex (≥3000w), ch07_oursystem.tex (≥2400w), "
            "ch08_results.tex (≥3000w), ch09_conclusion.tex (≥1400w + appendix). "
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


def create_task_review(editor: Agent, context: list[Task]) -> Task:
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
    """
    Targeted fix task. The agent reads the quality report and the existing
    chapter files, then patches ONLY the sections listed in failed_sections.
    """
    sections_str = ", ".join(failed_sections)

    # Build path instructions so the agent knows WHERE to read AND write.
    paths_note = ""
    if run_folder is not None:
        chapters_dir = run_folder / "latex" / "chapters"
        bib_path     = run_folder / "latex" / "references.bib"
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
REMEDIATION TASK. Fix specific quality failures from the quality report.

STEP 1 — Read the quality report to understand what failed:
    FileReaderTool("{quality_report_path}")

STEP 2 — Read ONLY the chapter files that have issues (see failed sections below).
    Do NOT try to read directories — only read specific .tex files.

STEP 3 — Fix the failing chapters. Common fixes:
    • words too low: expand existing subsections with more detail, add 400+ Hebrew words per chapter
    • citations missing: add \\cite{{}} references and ensure keys exist in references.bib
    • equations missing: add numbered \\begin{{equation}}...\\end{{equation}} blocks
    • em dashes: replace every — (U+2014) with a colon (:) or comma (,)

STEP 4 — Write each fixed file back using SafeFileWriterTool.
    Rewrite the ENTIRE file content (not just the changed parts).

Failed sections to fix: [{sections_str}]
Do NOT modify chapters that passed — only fix the ones with issues.
{paths_note}
""",
        expected_output=f"Fixed chapter file(s) addressing failures in: {sections_str}. Confirmation: 'REMEDIATION COMPLETE'.",
        agent=agent,
        output_file=output_file,
    )


_DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "vision_ai": (
        "Visual SLAM, monocular/stereo depth estimation, semantic segmentation, "
        "optical flow, neural feature descriptors, vision transformers, edge inference"
    ),
    "physics": (
        "Matched filter theory, LFM/FM sonar signal design, acoustic wave propagation, "
        "Doppler physics, cochlear mechanics, range-Doppler ambiguity, beamforming"
    ),
    "algorithms": (
        "EKF/UKF/particle filters, factor graph SLAM (g2o/GTSAM/iSAM2), "
        "covariance intersection, loop closure, CRLB, computational complexity of SLAM"
    ),
    "aerospace": (
        "UAV 6-DOF flight dynamics, IMU strapdown/INS, GPS-denied navigation, "
        "AUV/submarine sonar, DVL, multi-path acoustics, submarine↔cave navigation parallel"
    ),
    "biology": (
        "Bat echolocation (CF-FM sonar, acoustic fovea, DSC mechanism), "
        "neural computation for spatial mapping, bio-inspired algorithm design, "
        "dolphin biosonar, lateral line sensing"
    ),
}


def create_all_tasks(
    director,
    researcher,
    dom_vision_ai,
    dom_physics,
    dom_algorithms,
    dom_aerospace,
    dom_biology,
    visualizer,
    hebrew_writer,
    author,
    topic,
    run_folder: Path | None = None,
    fast_mode: bool = False,
) -> list[Task]:
    """
    Full pipeline (fast_mode=False, 11 tasks):
      outline → research
        → domain_vision_ai → domain_physics → domain_algorithms
        → domain_aerospace → domain_biology
        → figures → hebrew_prose
        → latex_part1 → latex_part2

    Fast pipeline (fast_mode=True, 6 tasks — skips domain experts):
      outline → research → figures → hebrew_prose → latex_part1 → latex_part2
    """
    t_outline  = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    if fast_mode:
        # Skip all 5 domain expert tasks — use only outline + research as context
        domain_tasks = []
        hebrew_context = [t_research]
    else:
        t_dom_vision_ai   = create_task_domain_expert(dom_vision_ai,   "vision_ai",   _DOMAIN_DESCRIPTIONS["vision_ai"],   [t_research])
        t_dom_physics     = create_task_domain_expert(dom_physics,     "physics",     _DOMAIN_DESCRIPTIONS["physics"],     [t_research])
        t_dom_algorithms  = create_task_domain_expert(dom_algorithms,  "algorithms",  _DOMAIN_DESCRIPTIONS["algorithms"],  [t_research])
        t_dom_aerospace   = create_task_domain_expert(dom_aerospace,   "aerospace",   _DOMAIN_DESCRIPTIONS["aerospace"],   [t_research])
        t_dom_biology     = create_task_domain_expert(dom_biology,     "biology",     _DOMAIN_DESCRIPTIONS["biology"],     [t_research])

        domain_tasks   = [t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology]
        hebrew_context = [t_research] + domain_tasks

    t_figures  = create_task_figures(visualizer, [t_research], run_folder=run_folder)
    t_hebrew   = create_task_hebrew_prose(hebrew_writer, hebrew_context)
    t_latex1   = create_task_latex_part1(author, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex2   = create_task_latex_part2(author, [t_hebrew, t_figures], run_folder=run_folder)

    return [
        t_outline, t_research,
        *domain_tasks,
        t_figures, t_hebrew, t_latex1, t_latex2,
    ]


# ---------------------------------------------------------------------------
# Smoke pipeline (2 tasks, ~35 LLM calls, ~3–8 minutes)
# ---------------------------------------------------------------------------

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
