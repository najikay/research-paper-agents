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
        # NO output_file — the agent writes via SafeFileWriterTool.
        # CrewAI's output_file would OVERWRITE the 18 KB outline with a 400-byte summary.
    )


def create_task_research(researcher: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Produce 8 detailed technical research briefs based on {_STAGING}/paper_outline.md.
Each brief must provide enough material for a 3–4 page chapter (600+ words of content).

STEP 1 — Read the outline:
    FileReaderTool("{_STAGING}/paper_outline.md")

STEP 2 — Research each sub-domain using web search:
    Use SerperDevSearchTool and ArxivSearchTool to find real papers, methods, and data.

STEP 3 — For each sub-domain produce:
  • 2–3 paragraph technical summary (Hebrew-language prose ready to paste)
  • All relevant equations with full variable definitions
  • Algorithm descriptions (pseudocode if applicable)
  • 3–5 specific BibTeX citations with author, title, year
  • Figure descriptions (what to plot and why)
  • A comparison table (at least 3 alternatives compared on 3+ criteria)

STEP 4 — Save ALL briefs using SafeFileWriterTool to {_STAGING}/research_briefs.md.
    IMPORTANT: Your response text is NOT saved to any file automatically.
    You MUST call SafeFileWriterTool to write the complete research content.
    The file must contain all 8 briefs (total ≥4800 words).
""".strip(),
        expected_output=f"8 structured research briefs in {_STAGING}/research_briefs.md, each providing ≥600 words of technical content. Confirmation: 'RESEARCH COMPLETE'.",
        agent=researcher,
        context=context,
        # NO output_file — the agent writes via SafeFileWriterTool.
        # CrewAI's output_file would OVERWRITE the real research content with a summary.
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

    Design notes (v7 — file-read + anti-loop architecture):
      • File reading: domain experts now READ paper_outline.md and
        research_briefs.md explicitly via FileReaderTool. CrewAI context
        only passes the agent's response text (short confirmation), not
        the 15-32 KB file content. Explicit reads ensure domain experts
        have full context to produce high-quality contributions.
      • No escape hatch: the DOMAIN SKIP option is removed. Every domain
        expert MUST contribute content. The topic is broad enough for all.
      • Measurable output: the task requires a specific minimum (3 equations,
        5 references, 500+ words). Agents cannot shortcut to "COMPLETE."
      • No output_file: CrewAI's output_file parameter OVERWRITES the file
        that SafeFileWriterTool wrote with the agent's short final response.
        We intentionally omit it so the real 20 KB content is preserved.
    """
    return Task(
        description=f"""
You are a PhD-level domain specialist. You MUST contribute technical depth
to the academic paper being written.

Your domain expertise: {domain_description}

STEP 0 — Read the paper outline and research briefs to understand the topic:
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/research_briefs.md")
    Then use web search (SerperDevSearchTool, ArxivSearchTool) to find domain-specific content.

YOUR MANDATORY OUTPUT — produce ALL of the following:

1. TECHNICAL ANALYSIS (500+ words):
   State-of-the-art methods, dominant approaches, and known failure modes
   from YOUR domain that are relevant to the paper topic. Be specific:
   name methods, cite years, give quantitative performance numbers.

2. EQUATIONS (minimum 3, LaTeX-ready):
   Each as: \\begin{{equation}} ... \\label{{eq:domain_{domain_key}_N}} \\end{{equation}}
   Include variable definitions after each equation.
   Only equations from YOUR domain — not already in the research briefs.

3. ALGORITHMS OR METHODS (minimum 2):
   Pseudocode or step-by-step descriptions of key algorithms from your field.

4. BIBTEX REFERENCES (minimum 5):
   Full BibTeX entries: @article{{Key, author=..., title=..., journal=..., year=..., doi=...}}
   Only real, verifiable references. No fabricated citations.

5. INTEGRATION NOTES (200+ words):
   How your domain contributions connect to the paper's overall system.

Write your complete contribution using SafeFileWriterTool to:
    {_STAGING}/domain_{domain_key}.md

IMPORTANT: You MUST produce all 5 sections. Do not skip any section.
Do not write "DOMAIN SKIP" or "DOMAIN EXPERT COMPLETE" without content.
Your output will be validated — empty or trivial responses will be flagged.
""".strip(),
        expected_output=(
            f"Complete domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"containing: technical analysis (500+ words), 3+ LaTeX equations, "
            f"2+ algorithms, 5+ BibTeX references, and integration notes."
        ),
        agent=expert,
        context=context,
        # NO output_file here — CrewAI's output_file overwrites what SafeFileWriterTool
        # wrote (20 KB content → 2 KB summary). The real content lives in the file
        # written by the agent via SafeFileWriterTool during task execution.
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
    FileReaderTool("{_STAGING}/domain_signal_processing.md") ← Signal processing expert
    FileReaderTool("{_STAGING}/domain_control_systems.md")   ← Control systems expert
    FileReaderTool("{_STAGING}/domain_ml.md")                ← ML expert
    Files that begin with "DOMAIN SKIP:" have no relevant content — skip them.

STEP 2 — Write Hebrew prose for ALL nine chapters. You MUST write in THREE separate
    batches because a single call will be truncated by the output token limit.

    BATCH 1 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part1.md:
        ## CH01: <title>   (≥1200 Hebrew words, 3+ subsections)
        ## CH02: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH03: <title>   (≥1500 Hebrew words, 4+ subsections)
        After writing, confirm: "BATCH 1 WRITTEN — 3 chapters."

    BATCH 2 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part2.md:
        ## CH04: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH05: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH06: <title>   (≥1800 Hebrew words, 5+ subsections — this is the core algorithm chapter)
        After writing, confirm: "BATCH 2 WRITTEN — 3 chapters."

    BATCH 3 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part3.md:
        ## CH07: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH08: <title>   (≥1800 Hebrew words, 5+ subsections — this is the results chapter)
        ## CH09: <title>   (≥900 Hebrew words, 3+ subsections)
        After writing, confirm: "BATCH 3 WRITTEN — 3 chapters."

    STEP 2b — Read back all 3 batch files, then combine into the FINAL file:
        FileReaderTool("{_STAGING}/hebrew_prose_part1.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part2.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part3.md")
        Then call SafeFileWriterTool to write {_STAGING}/hebrew_prose.md with ALL 9 chapters.

    CRITICAL: Do NOT write all 9 chapters in a single SafeFileWriterTool call.
    You MUST write 3 separate batch files first, then combine them.

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
            f"Hebrew prose written in 3 batches (part1/part2/part3) then combined into {_STAGING}/hebrew_prose.md. "
            f"≥1200-1800 words per chapter. Zero em dash characters. Confirmation: 'HEBREW PROSE COMPLETE'."
        ),
        agent=writer,
        context=context,
        output_file=f"{_STAGING}/hebrew_prose_status.md",
    )


def _latex_shared_rules(chapters_dir: str, bib_path: str, latex_dir: str) -> str:
    """Shared LaTeX writing rules injected into both latex task descriptions."""
    return f"""
CONTENT DEPTH — targeting 25–30 printed pages total:
    • ch01: ≥2500 Hebrew words, ≥4 subsections, ≥2 equations
    • ch02–ch05: ≥3200 Hebrew words each, ≥6 subsections, ≥5 equations, ≥1 figure, ≥1 table
    • ch06 (algorithm): ≥4000 Hebrew words, ≥6 subsections, ≥6 equations, ≥1 lstlisting, ≥1 figure
    • ch07 (system): ≥3200 Hebrew words, ≥5 subsections, ≥4 equations, ≥1 figure
    • ch08 (results): ≥4000 Hebrew words, ≥6 subsections, ≥4 equations, ≥2 figures, ≥1 table
    • ch09 (conclusion): ≥2000 Hebrew words, ≥3 subsections
    IMPORTANT: Write ALL chapters — do NOT skip any. Each chapter MUST be written to its own file.

FIGURE WIDTH AND PLACEMENT RULES:
    • Default for simple plots: \\begin{{figure}}[htbp] with [width=0.98\\columnwidth]
    • WIDE figures MUST use: \\begin{{figure*}}[htbp] with [width=\\textwidth]
      Use figure* for: architecture diagrams, pipeline flowcharts, multi-panel figures,
      wide spectrograms, comparison bar charts, system block diagrams, and any figure
      with a landscape/wide aspect ratio. In real IEEE papers these ALWAYS span both columns.
    • NEVER use [H] for float placement — it causes overlapping in two-column IEEE.
    • NEVER use width smaller than 0.9\\columnwidth.
    • Aim for at least 40\\% of figures to use figure* — this improves readability.

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

def create_research_tasks(
    director, researcher,
    domain_experts: dict[str, Agent],
    topic: str,
) -> list[Task]:
    """
    Create tasks for the research phase crew:
    outline → research → 8 domain expert tasks (all in parallel context from research).
    """
    t_outline = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    domain_tasks = []
    for key, expert in domain_experts.items():
        desc = _DOMAIN_DESCRIPTIONS.get(key, key)
        t = create_task_domain_expert(expert, key, desc, [t_outline, t_research])
        domain_tasks.append(t)

    return [t_outline, t_research] + domain_tasks


def create_writing_tasks(
    visualizer, hebrew_writer,
    author_a, author_b, author_c,
    run_folder: Path | None = None,
) -> list[Task]:
    """
    Create tasks for the writing phase crew:
    figures → hebrew_prose → latex_a → latex_b → latex_c
    """
    t_figures = create_task_figures(visualizer, [], run_folder=run_folder)
    t_hebrew = create_task_hebrew_prose(hebrew_writer, [t_figures])
    t_latex_a = create_task_latex_a(author_a, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_b = create_task_latex_b(author_b, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_c = create_task_latex_c(author_c, [t_hebrew, t_figures], run_folder=run_folder)
    return [t_figures, t_hebrew, t_latex_a, t_latex_b, t_latex_c]


def create_task_fix_domain(
    fixer: Agent,
    domain_key: str,
    topic: str,
    outline_content: str,
) -> Task:
    """
    Task for the Research Fixer agent to produce content for a failed domain expert.
    The topic and outline are embedded directly in the task description (no file reads needed).
    """
    desc = _DOMAIN_DESCRIPTIONS.get(domain_key, domain_key)
    return Task(
        description=f"""
You are a Research Fixer. A domain expert failed to produce usable content.
Your job: produce the missing domain contribution yourself.

PAPER TOPIC: {topic}

PAPER OUTLINE:
{outline_content}

DOMAIN TO COVER: {desc}

Write a complete domain contribution with:
1. Technical analysis (500+ words) of state-of-the-art from this domain
2. At least 3 LaTeX-ready equations with variable definitions
3. At least 2 algorithm/method descriptions
4. At least 5 BibTeX references (real, verifiable)
5. Integration notes on how this domain connects to the paper

CRITICAL — use SafeFileWriterTool to write your output to EXACTLY this path:
    {_STAGING}/domain_{domain_key}.md
Do NOT change this filename. Do NOT use a different name.

You have web search tools (SerperDevSearchTool, ArxivSearchTool) — use them
to find real papers and data. Do NOT fabricate citations.
""".strip(),
        expected_output=(
            f"Domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"with technical analysis, equations, algorithms, references, and integration notes."
        ),
        agent=fixer,
        # No output_file — agent writes via SafeFileWriterTool, don't overwrite.
    )


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
REMEDIATION TASK. Expand and fix chapters that failed the quality gate.

STEP 1 — Read the quality report AND the references.bib:
    FileReaderTool("{quality_report_path}")
    FileReaderTool("{bib_path}")  ← you need the \\cite{{}} keys for adding citations

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
    • "words≈N<M": add at least (M - N + 200) words of Hebrew academic prose
    • "citations=N<M": add \\cite{{}} calls using keys from references.bib
    • "equations=N<M": add numbered equations with \\label{{eq:chNN_...}}
    • "subsections=N<M": add new \\subsection{{}} blocks with 200+ words each
    • "em dashes": replace every — (U+2014) with colon (:) or comma (,)

    EM DASH RULE: character — is FORBIDDEN. Use colon (:) or comma (,).
    INLINE ENGLISH: every English word in Hebrew prose MUST be in \\en{{}}.

STEP 4 — After fixing ALL chapters, confirm: 'REMEDIATION COMPLETE'.

Failed sections to fix: [{sections_str}]
Do NOT modify chapters that passed — only fix the ones listed above.
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
    "signal_processing": (
        "Chirp/FM pulse design, matched filtering, beamforming (delay-and-sum, MVDR), "
        "time-of-flight estimation, Doppler shift processing, spectral analysis for bio-sonar, "
        "sonar equation, adaptive filtering (LMS, RLS)"
    ),
    "control_systems": (
        "Quadrotor dynamics and equations of motion, PID/LQR controller design, "
        "path planning (RRT*, A*, D*), trajectory optimization, obstacle avoidance, "
        "state estimation for control, real-time control on embedded platforms"
    ),
    "ml": (
        "Multi-modal sensor fusion networks (cross-attention, gating), "
        "1D-CNN for sonar signal encoding, reinforcement learning for navigation (PPO, SAC, GAE), "
        "training pipelines, loss functions, data augmentation for sensor data"
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
