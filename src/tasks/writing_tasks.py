"""
src/tasks/writing_tasks.py
===========================
Hebrew prose task and shared LaTeX rules used by all LaTeX task factories.
"""

from __future__ import annotations

from crewai import Agent, Task

_STAGING = "outputs/current"


def create_task_hebrew_prose(writer: Agent, context: list[Task]) -> Task:
    """Create the Hebrew academic prose writing task."""
    return Task(
        description=f"""
Read all research and domain-expert materials, then write polished Hebrew academic
prose for ALL chapters (CH01–CH09). Save prose to {_STAGING}/hebrew_prose.md.

STEP 1 — READ ALL INPUTS (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")         <- chapter structure, titles, equations
    FileReaderTool("{_STAGING}/research_briefs.md")       <- primary technical input
    FileReaderTool("{_STAGING}/domain_vision_ai.md")      <- Vision-AI expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_physics.md")        <- Physics expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_algorithms.md")     <- Algorithms expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_aerospace.md")      <- Aerospace/Marine expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_biology.md")        <- Biology expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_signal_processing.md") <- Signal processing expert
    FileReaderTool("{_STAGING}/domain_control_systems.md")   <- Control systems expert
    FileReaderTool("{_STAGING}/domain_ml.md")                <- ML expert
    Files that begin with "DOMAIN SKIP:" have no relevant content — skip them.

STEP 2 — Write Hebrew prose for ALL nine chapters. You MUST write in THREE separate
    batches because a single call will be truncated by the output token limit.

    BATCH 1 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part1.md:
        ## CH01: <title>   (>=1200 Hebrew words, 3+ subsections)
        ## CH02: <title>   (>=1500 Hebrew words, 4+ subsections)
        ## CH03: <title>   (>=1500 Hebrew words, 4+ subsections)
        After writing, confirm: "BATCH 1 WRITTEN — 3 chapters."

    BATCH 2 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part2.md:
        ## CH04: <title>   (>=1500 Hebrew words, 4+ subsections)
        ## CH05: <title>   (>=1500 Hebrew words, 4+ subsections)
        ## CH06: <title>   (>=1800 Hebrew words, 5+ subsections — this is the core algorithm chapter)
        After writing, confirm: "BATCH 2 WRITTEN — 3 chapters."

    BATCH 3 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part3.md:
        ## CH07: <title>   (>=1500 Hebrew words, 4+ subsections)
        ## CH08: <title>   (>=1800 Hebrew words, 5+ subsections — this is the results chapter)
        ## CH09: <title>   (>=900 Hebrew words, 3+ subsections)
        After writing, confirm: "BATCH 3 WRITTEN — 3 chapters."

    STEP 2b — Read back all 3 batch files, then combine into the FINAL file:
        FileReaderTool("{_STAGING}/hebrew_prose_part1.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part2.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part3.md")
        Then call SafeFileWriterTool to write {_STAGING}/hebrew_prose.md with ALL 9 chapters.

    CRITICAL: Do NOT write all 9 chapters in a single SafeFileWriterTool call.
    You MUST write 3 separate batch files first, then combine them.

    Per-chapter content:
        * Section marker: ## CH01: <Hebrew title from outline>
        * 3+ subsections marked: ### <Hebrew subsection title>
        * Inline markers for equations: [EQUATION: description]
        * Inline markers for figures: [FIGURE: fig_filename.png]
        * Inline markers for tables: [TABLE: description]
        * Citation markers: [CITE: AuthorYear]

    EM DASH PROHIBITION (ABSOLUTE RULE — violating this breaks the PDF):
        The character — (U+2014) is COMPLETELY FORBIDDEN anywhere in the output.
        Use colon (:) or comma (,) instead. Check every sentence.

    Language rules:
        * Prose in Hebrew. Technical acronyms stay in English: SLAM, EKF, LiDAR, UAV, IMU.
        * Do NOT write LaTeX commands — only prose text with inline markers.

STEP 3 — After writing, output a short confirmation: 'HEBREW PROSE COMPLETE'.
    Do NOT output the full prose in your final response — just the confirmation.
    The prose is already saved to the file by SafeFileWriterTool.
""".strip(),
        expected_output=(
            f"Hebrew prose written in 3 batches (part1/part2/part3) then combined into "
            f"{_STAGING}/hebrew_prose.md. >=1200-1800 words per chapter. Zero em dash "
            f"characters. Confirmation: 'HEBREW PROSE COMPLETE'."
        ),
        agent=writer,
        context=context,
        output_file=f"{_STAGING}/hebrew_prose_status.md",
    )


def latex_shared_rules(chapters_dir: str, bib_path: str, latex_dir: str) -> str:
    """Return the shared LaTeX writing rules injected into all latex task descriptions."""
    return f"""
CONTENT DEPTH — targeting 25–30 printed pages total:
    * ch01: >=2500 Hebrew words, >=4 subsections, >=2 equations
    * ch02–ch05: >=3200 Hebrew words each, >=6 subsections, >=5 equations, >=1 figure, >=1 table
    * ch06 (algorithm): >=4000 Hebrew words, >=6 subsections, >=6 equations, >=1 lstlisting, >=1 figure
    * ch07 (system): >=3200 Hebrew words, >=5 subsections, >=4 equations, >=1 figure
    * ch08 (results): >=4000 Hebrew words, >=6 subsections, >=4 equations, >=2 figures, >=1 table
    * ch09 (conclusion): >=2000 Hebrew words, >=3 subsections
    IMPORTANT: Write ALL chapters — do NOT skip any. Each chapter MUST be written to its own file.

FIGURE WIDTH AND PLACEMENT RULES:
    * Default for simple plots: \\begin{{figure}}[htbp] with [width=0.98\\columnwidth]
    * WIDE figures MUST use: \\begin{{figure*}}[htbp] with [width=\\textwidth]
      Use figure* for: architecture diagrams, pipeline flowcharts, multi-panel figures,
      wide spectrograms, comparison bar charts, system block diagrams, and any figure
      with a landscape/wide aspect ratio. In real IEEE papers these ALWAYS span both columns.
    * NEVER use [H] for float placement — it causes overlapping in two-column IEEE.
    * NEVER use width smaller than 0.9\\columnwidth.
    * Aim for at least 40% of figures to use figure* — this improves readability.

LABEL UNIQUENESS — every \\label{{}} must be globally unique:
    * Prefix with chapter ID: \\label{{fig:ch02_name}}, \\label{{eq:ch03_name}}, \\label{{tab:ch05_name}}
    * NEVER reuse a label name from another chapter.

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
    \\begin{{lstlisting}}[language=Python, caption={{\\texthebrew{{...}}}}]
    ... pseudocode here (always LTR English) ...
    \\end{{lstlisting}}
    \\end{{english}}
    The \\begin{{algorithm}} environment is NOT available. Use lstlisting for all pseudocode.
    lstlisting captions with Hebrew: wrap the Hebrew text in \\texthebrew{{}}.

RTL / LTR DIRECTION — CRITICAL for correct rendering:
    * The document is RTL (Hebrew). All code, algorithms, and pseudocode are LTR (English).
    * NEVER use \\textemdash or \\textendash in Hebrew text. Use colon (:) or comma (,).
    * Tables with mixed Hebrew/English: each cell handles its own direction automatically.
    * Figure captions: Hebrew text renders RTL, English terms in \\en{{}} render LTR.

FLOAT PLACEMENT — prevent overlapping content:
    * Figures: use \\begin{{figure}}[htbp] (NOT [H] which causes overlap in two-column).
    * Tables: use \\begin{{table}}[htbp] for consistency.
    * Wide figures (flowcharts, multi-panel): use \\begin{{figure*}}[htbp] with [width=\\textwidth].

COLUMN WIDTH — IEEE two-column is NARROW (~3.5 inches per column):
    * Tables: max 4 columns in single-column mode. For wider tables use \\begin{{table*}}.
    * Equations: keep them SHORT. Split long equations with \\begin{{align}} + \\\\ line breaks.
    * Do NOT put long equations with many subscripts/superscripts in a single \\begin{{equation}}.

MATH IN CAPTIONS — CRITICAL (prevents PDF crash):
    ALL math symbols and Greek letters inside \\caption{{}} and \\section{{}} MUST be in math mode.
    Write: $2\\sigma$, $\\alpha$, $\\delta_{{k}}$, $\\hat{{x}}$
    NOT: 2-\\sigma, \\alpha, \\delta_k (these crash XeLaTeX outside math environments).

PROTECTED (never overwrite):
    {latex_dir}/main.tex    {chapters_dir}/cover.tex

Use SafeFileWriterTool for EVERY file. COMPILER: XeLaTeX.
WRITE EACH FILE IMMEDIATELY after completing it — do not buffer all files before writing.
""".strip()
