"""
src/tasks/tasks_latex_rules.py — shared LaTeX writing rules.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING


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
