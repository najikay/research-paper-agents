"""
sanitizer.py
============
Main LaTeX sanitizer entry point: _sanitize_tex_files.

Fixes common LaTeX errors that agents introduce, preventing compilation failures.
The heavy fix logic is split across _apply_structural_fixes (this file) and
_apply_content_fixes (sanitizer_core.py) to stay within file-size limits.
"""

import re
from pathlib import Path

from src.config import logger
from src.pipeline.sanitizer_figures import _upgrade_wide_figures
from src.pipeline.sanitizer_math import _wrap_bare_math_in_text


def _apply_structural_fixes(text: str, tex_file_name: str) -> str:
    """Apply structural/environment fixes (Fixes 1-11b)."""

    # Fix 1: Remove \begin{abstract} inside abstract.tex
    if tex_file_name == "abstract.tex":
        text = text.replace(r"\begin{abstract}", "")
        text = text.replace(r"\end{abstract}", "")

    # Fix 2: Remove \begin{document} / \end{document} inside chapter files
    text = text.replace(r"\begin{document}", "")
    text = text.replace(r"\end{document}", "")

    # Fix 3: Remove \documentclass inside chapter files
    text = re.sub(r"\\documentclass(\[[^\]]*\])?\{[^}]+\}", "", text)

    # Fix 4: Remove \usepackage inside chapter files
    text = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]+\}", "", text)

    # Fix 5: Replace \begin{center}...\end{center} with \centering
    text = text.replace(r"\begin{center}", r"{\centering")
    text = text.replace(r"\end{center}", "}")

    # Fix 6: Remove stray \maketitle
    text = text.replace(r"\maketitle", "")

    # Fix 7: Replace em dashes (U+2014) with colons in Hebrew prose
    text = text.replace("\u2014", ":")
    text = text.replace("\u2013", "-")

    # Fix 8: Remove \textemdash from section/subsection titles
    text = text.replace(r"\textemdash", ":")
    text = text.replace(r"\textendash", "-")

    # Fix 9: Wrap lstlisting in \begin{english}...\end{english} for LTR
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

    # Fix 10: Replace aggressive [H] float spec with [htbp]
    text = re.sub(r'\\begin\{figure\}\[H\]', r'\\begin{figure}[htbp]', text)
    text = re.sub(r'\\begin\{figure\*\}\[H\]', r'\\begin{figure*}[htbp]', text)
    text = re.sub(r'\\begin\{table\}\[H\]', r'\\begin{table}[htbp]', text)
    text = re.sub(r'\\begin\{table\*\}\[H\]', r'\\begin{table*}[htbp]', text)

    # Fix 11: Wrap tabular environments in \adjustbox to prevent column overflow.
    if r'\begin{tabular}' in text and r'\adjustbox' not in text:
        text = text.replace(
            r'\begin{tabular}',
            r'\adjustbox{max width=\columnwidth}{%' + '\n' + r'\begin{tabular}',
        )
        text = text.replace(
            r'\end{tabular}',
            r'\end{tabular}%' + '\n' + '}',
        )

    # Fix 11b: Escape bare % in running text
    text = re.sub(r'([^\\{}\s])%', r'\1\\%', text)

    return text


def _apply_content_fixes(text: str) -> str:
    """Apply content-level fixes (Fixes 12a-26)."""
    from src.pipeline.sanitizer_core import _apply_content_fixes_impl
    return _apply_content_fixes_impl(text)


def _sanitize_tex_files(chapters_dir: Path) -> None:
    """
    Fix common LaTeX errors that agents introduce, preventing compilation failures.
    """
    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        original = text

        # Stage 1: structural/environment fixes
        text = _apply_structural_fixes(text, tex_file.name)

        # Fix 24: Upgrade single-column figures to figure* for wide images.
        figures_dir = chapters_dir.parent / "figures"
        if figures_dir.is_dir():
            text = _upgrade_wide_figures(text, figures_dir)

        # Stage 2: content-level fixes (12a-26)
        text = _apply_content_fixes(text)

        # Fix 12b: Wrap bare math symbols anywhere in body text with $...$
        text = _wrap_bare_math_in_text(text)

        if text != original:
            tex_file.write_text(text, encoding="utf-8")
            logger.info(f"[Sanitize] Fixed LaTeX issues in {tex_file.name}")
