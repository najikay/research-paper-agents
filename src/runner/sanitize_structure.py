"""
src/runner/sanitize_structure.py
================================
Sanitizer fixes 1-11b: document structure, dashes, code-block wrapping,
float placement, wide-figure upgrade, table fitting, and % escaping.
Bodies moved verbatim from main.py's _sanitize_tex_files (150-line rule).
Fix order is preserved exactly: 1-10, 24, 11, 11b.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.runner.tex_math import _upgrade_wide_figures


def apply_structure_fixes(text: str, tex_name: str, figures_dir: Path) -> str:
    """
    Apply structural sanitizer fixes (1-11b, plus 24) to a chapter's .tex
    *text* and return the repaired text. *tex_name* selects file-specific
    handling (e.g. stripping \\begin{abstract} from abstract.tex) and
    *figures_dir* is used to probe image dimensions for the wide-figure
    upgrade. Removes preamble/document commands, normalizes dashes, wraps code
    blocks for LTR rendering, relaxes float placement, fits wide tables, and
    escapes bare percent signs.
    """
    # Fix 1: Remove \begin{abstract} inside abstract.tex
    # (main.tex already wraps it in \begin{abstract}...\end{abstract})
    if tex_name == "abstract.tex":
        text = text.replace(r"\begin{abstract}", "")
        text = text.replace(r"\end{abstract}", "")

    # Fix 2: Remove \begin{document} / \end{document} inside chapter files
    text = text.replace(r"\begin{document}", "")
    text = text.replace(r"\end{document}", "")

    # Fix 3: Remove \documentclass inside chapter files
    text = re.sub(r"\\documentclass(\[[^\]]*\])?\{[^}]+\}", "", text)

    # Fix 4: Remove \usepackage inside chapter files (preamble commands in chapter body)
    text = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]+\}", "", text)

    # Fix 5: Replace \begin{center}...\end{center} with \centering
    # (causes bidi crash at document level)
    text = text.replace(r"\begin{center}", r"{\centering")
    text = text.replace(r"\end{center}", "}")

    # Fix 6: Remove stray \maketitle
    text = text.replace(r"\maketitle", "")

    # Fix 7: Replace em dashes (U+2014) with colons in Hebrew prose
    # Only outside \en{} blocks — em dashes crash bidi rendering
    text = text.replace("—", ":")
    # Also replace en dashes (U+2013) which are similarly problematic
    text = text.replace("–", "-")

    # Fix 8: Remove \textemdash from section/subsection titles (RTL crash risk)
    text = text.replace(r"\textemdash", ":")
    text = text.replace(r"\textendash", "-")

    # Fix 9: Wrap lstlisting in \begin{english}...\end{english} for LTR
    # This forces the bidi package to render code blocks left-to-right.
    # Only add if not already wrapped.
    text = re.sub(
        r'(?<!\\begin\{english\}\n)\\begin\{lstlisting\}',
        r'\\begin{english}\n\\begin{lstlisting}',
        text,
    )
    text = re.sub(
        r'\\end\{lstlisting\}(?!\n\\end\{english\})',
        r'\\end{lstlisting}\n\\end{english}',
        text,
    )

    # Fix 10: Replace aggressive [H] float spec with [htbp] for better layout
    # [H] forces exact placement and causes overlapping in two-column IEEE.
    text = re.sub(
        r'\\begin\{figure\}\[H\]',
        r'\\begin{figure}[htbp]',
        text,
    )
    text = re.sub(
        r'\\begin\{figure\*\}\[H\]',
        r'\\begin{figure*}[htbp]',
        text,
    )
    text = re.sub(
        r'\\begin\{table\}\[H\]',
        r'\\begin{table}[htbp]',
        text,
    )
    text = re.sub(
        r'\\begin\{table\*\}\[H\]',
        r'\\begin{table*}[htbp]',
        text,
    )

    # Fix 24: Upgrade single-column figures to figure* for wide images.
    # Must run after Fix 10 ([H] → [htbp]) so figure blocks have consistent placement.
    if figures_dir.is_dir():
        text = _upgrade_wide_figures(text, figures_dir)

    # Fix 11: Wrap tabular environments in \adjustbox to prevent column overflow.
    # Tables with many columns overflow IEEE single-column width.
    # \adjustbox{max width=\columnwidth} shrinks them to fit.
    # Skip if already wrapped.
    if r'\begin{tabular}' in text and r'\adjustbox' not in text:
        text = text.replace(
            r'\begin{tabular}',
            r'\adjustbox{max width=\columnwidth}{%' + '\n' + r'\begin{tabular}',
        )
        text = text.replace(
            r'\end{tabular}',
            r'\end{tabular}%' + '\n' + '}',
        )

    # Fix 11b: Escape bare % in running text (LLM writes "96%" or "(%)").
    # LaTeX treats % as comment-start, eating the rest of the line. This
    # destroys table alignment, silently drops body text, and causes "runaway
    # argument" crashes inside \caption{} or \section{} commands.
    # Escape % preceded by any char that is NOT: \, {, }, or whitespace.
    # This preserves: line comments (% at line start), whitespace suppression
    # ({%  }% at end of line), and already-escaped \%.
    text = re.sub(r'([^\\{}\s])%', r'\1\\%', text)

    return text
