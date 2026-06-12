"""
src/runner/sanitize_final.py
============================
Sanitizer fixes 21-23, 20, 12b: author-name macros, \\ensuremath flattening,
stray-brace removal, truncated-file repair, and bare-math wrapping.
Bodies moved verbatim from main.py's _sanitize_tex_files (150-line rule).
Fix order is preserved exactly: 21, 22, 23, 20, 12b.
"""
from __future__ import annotations

import re

from src.runner.tex_math import _wrap_bare_math_in_text

# Fix 21 allow-list: \CapitalizedWord commands that are real LaTeX, not author names.
_SAFE_CMDS = {
    # Greek letters (uppercase)
    'Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta',
    'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Pi', 'Rho', 'Sigma',
    'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega',
    # LaTeX meta commands
    'LaTeX', 'TeX', 'BibTeX', 'XeLaTeX',
    # Document structure
    'Chapter', 'Section', 'Subsection', 'Paragraph', 'Part',
    # Common formatting
    'Large', 'Huge', 'LARGE', 'HUGE', 'Centering',
    # IEEE / math
    'Re', 'Im',
}


def apply_final_fixes(text: str) -> str:
    """
    Apply the final-pass sanitizer fixes (21, 22, 23, 20, 12b) to a chapter's
    .tex *text* and return the repaired text. Wraps author-name macros in
    \\en{}, flattens \\ensuremath{...} to $...$, drops stray closing braces,
    appends closing braces for truncated files, and wraps remaining bare math
    symbols in $...$.
    """
    # Fix 21: Convert \AuthorName patterns to \en{AuthorName}.
    # LLM agents write \Au, \Thorp, \Ketten etc. as undefined control sequences
    # (treating author names as commands). This causes "Undefined control sequence"
    # fatal errors. Convert \CapitalizedWord to \en{CapitalizedWord} when NOT
    # followed by { and NOT a known LaTeX command.
    def _fix_author_cmd(m):
        """Convert a matched \\CapitalizedWord control sequence to \\en{Word},
        unless the word is a known-safe LaTeX command (in _SAFE_CMDS), in which
        case the original match is returned unchanged."""
        word = m.group(1)
        if word in _SAFE_CMDS:
            return m.group(0)
        return r'\en{' + word + '}'
    text = re.sub(r'\\([A-Z][a-z]+(?:[A-Z][a-z]*)*)(?!\{|[a-z])', _fix_author_cmd, text)

    # Fix 22: Replace \ensuremath{content} with $content$ (sans inner $).
    # LLM agents write \ensuremath{$\theta$} (nested math mode) which crashes.
    # \ensuremath is equivalent to $...$ outside math mode.
    # Use brace counting to handle nested {} (regex can't do this).
    _ENSUREMATH = r'\ensuremath{'
    while _ENSUREMATH in text:
        idx = text.index(_ENSUREMATH)
        start = idx + len(_ENSUREMATH)
        depth, end = 1, start
        while end < len(text) and depth > 0:
            if text[end] == '{':
                depth += 1
            elif text[end] == '}':
                depth -= 1
            end += 1
        inner = text[start:end - 1].replace('$', '')
        text = text[:idx] + '$' + inner + '$' + text[end:]

    # Fix 23: Remove stray } that have no matching {.
    # Agents produce excess } after abbreviations (RMSE}, INS/DVL}, etc.).
    # Walk the text tracking brace depth; drop any } that would make depth < 0.
    _parts = []
    _depth = 0
    for _ch in text:
        if _ch == '{':
            _depth += 1
            _parts.append(_ch)
        elif _ch == '}':
            if _depth > 0:
                _depth -= 1
                _parts.append(_ch)
            # else: stray } — skip it
        else:
            _parts.append(_ch)
    text = ''.join(_parts)

    # Fix 20: Repair truncated files with unbalanced braces.
    # When agents hit the output token limit, the file ends mid-\section{}
    # or mid-\subsection{}, leaving unclosed braces. This causes "File ended
    # while scanning use of \@xdblarg" fatal errors. Count net braces and
    # append closing braces if needed.
    open_braces = text.count('{') - text.count('}')
    if open_braces > 0:
        text = text.rstrip() + '\n' + ('}' * open_braces) + '\n'

    # Fix 12b: Wrap bare math symbols anywhere in body text with $...$.
    # Agents often write \alpha, \sigma etc. without $...$ outside math
    # environments, causing "Missing $ inserted" errors.
    # Uses _wrap_bare_math_in_text() which protects existing math regions
    # first, wraps bare symbols, then restores.
    text = _wrap_bare_math_in_text(text)

    return text
