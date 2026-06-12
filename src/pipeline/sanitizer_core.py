"""
sanitizer_core.py
=================
Content-level LaTeX fixes (Fixes 12a through 26) extracted from _sanitize_tex_files.

These handle math-mode issues, undefined commands, algorithm environments,
brace balancing, and other content-level problems that agents introduce.
"""

import re

# Safe LaTeX commands that should NOT be treated as author names (Fix 21)
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


def _apply_content_fixes_impl(text: str) -> str:
    """Apply content-level LaTeX fixes (Fixes 12a through 26)."""

    # Fix 12a: Unwrap \en{} from math mode
    text = re.sub(r'\$\\en\{([^}]*)\}\$', r'\\en{\1}', text)
    text = re.sub(r'\\\(\\en\{([^}]*)\}\\\)', r'\\en{\1}', text)

    # Fix 12a2: Remove \begin{english}/\end{english} wrappers around tables
    text = re.sub(r'\\begin\{english\}\s*\n(\\begin\{table)', r'\1', text)
    text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{english\}', r'\1', text)
    text = re.sub(r'\\begin\{LTR\}\s*\n(\\begin\{table)', r'\1', text)
    text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{LTR\}', r'\1', text)

    # Fix 12a3: Unwrap \en{text} -> text when it appears right before a closing }
    text = re.sub(r'\\en\{([^}]*)\}(\s*\})', r'\1\2', text)

    # Fix 12c: Replace undefined \tabref, \figref, \secref -> \ref
    text = re.sub(r'\\tabref\{', r'\\ref{', text)
    text = re.sub(r'\\figref\{', r'\\ref{', text)
    text = re.sub(r'\\secref\{', r'\\ref{', text)

    # Fix 13: Replace algorithm/algorithmic environments with lstlisting
    text = re.sub(
        r'\\begin\{algorithm\}(\[[^\]]*\])?',
        r'\\begin{english}\n\\begin{lstlisting}[language=Python]',
        text,
    )
    text = re.sub(r'\\end\{algorithm\}', r'\\end{lstlisting}\n\\end{english}', text)
    text = re.sub(r'\\begin\{algorithmic\}(\[[^\]]*\])?', '', text)
    text = re.sub(r'\\end\{algorithmic\}', '', text)
    for cmd in [r'\\Require', r'\\Ensure', r'\\State', r'\\If', r'\\EndIf',
                r'\\For', r'\\EndFor', r'\\While', r'\\EndWhile', r'\\Return',
                r'\\Function', r'\\EndFunction', r'\\Procedure', r'\\EndProcedure']:
        text = re.sub(cmd + r'\b', '', text)

    # Fix 14: Fix literal \\n sequences in tabular rows
    text = re.sub(r'\\\\n(\\[a-zA-Z])', r'\\\\\n\1', text)
    text = re.sub(r'\\\\n\s*$', r'\\\\', text, flags=re.MULTILINE)

    # Fix 15: Remove backslash before Hebrew characters
    text = re.sub(r'\\([\u0590-\u05FF])', r'\1', text)

    # Fix 16: Escape underscores inside \en{...} blocks
    def _escape_underscores_in_en(m: re.Match) -> str:
        return r'\en{' + m.group(1).replace('_', r'\_') + '}'
    text = re.sub(r'\\en\{([^}]*_[^}]*)\}', _escape_underscores_in_en, text)

    # Fix 25: Extract math superscripts/subscripts from \en{} blocks
    def _fix_math_in_en(m: re.Match) -> str:
        content = m.group(1)
        caret = re.search(r'\^(\{[^}]*\}|\d+)', content)
        if not caret:
            return m.group(0)
        before = content[:caret.start()]
        math_part = caret.group(0)
        after = content[caret.end():]
        result = r'\en{' + before + '}'
        result += '$' + math_part + '$'
        if after:
            result += r'\en{' + after + '}'
        return result
    text = re.sub(r'\\en\{([^}]*\^[^}]*)\}', _fix_math_in_en, text)

    # Fix 26: Wrap bare math expressions in $...$
    text = re.sub(
        r'(?<!\$)(?<!\\)'
        r'([A-Za-z]\w*'
        r'\([^)]*[_^][^)]*\))',
        r'$\1$',
        text,
    )

    # Fix 17: Replace \degree (undefined) with Unicode degree
    text = text.replace("\\°", "\u00b0")

    # Fix 18: Replace \textquoteright with /
    text = text.replace("\\textquoteright", "/")
    text = text.replace("\\textquoteleft", "/")

    # Fix 19: Convert single-row bmatrix to \left[...\right]
    def _fix_row_bmatrix(m):
        inner = m.group(1).strip()
        inner = inner.replace(" & ", r",\; ")
        return r"\left[" + inner + r"\right]"
    text = re.sub(
        r"\\begin\{bmatrix\}\s*([^\n]*?)\s*\\end\{bmatrix\}",
        _fix_row_bmatrix,
        text,
    )

    # Fix 21: Convert \AuthorName patterns to \en{AuthorName}
    def _fix_author_cmd(m):
        word = m.group(1)
        if word in _SAFE_CMDS:
            return m.group(0)
        return r'\en{' + word + '}'
    text = re.sub(r'\\([A-Z][a-z]+(?:[A-Z][a-z]*)*)(?!\{|[a-z])', _fix_author_cmd, text)

    # Fix 22: Replace \ensuremath{content} with $content$
    ensuremath_tag = r'\ensuremath{'
    while ensuremath_tag in text:
        idx = text.index(ensuremath_tag)
        start = idx + len(ensuremath_tag)
        depth, end = 1, start
        while end < len(text) and depth > 0:
            if text[end] == '{':
                depth += 1
            elif text[end] == '}':
                depth -= 1
            end += 1
        inner = text[start:end - 1].replace('$', '')
        text = text[:idx] + '$' + inner + '$' + text[end:]

    # Fix 23: Remove stray } that have no matching {
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
        else:
            _parts.append(_ch)
    text = ''.join(_parts)

    # Fix 20: Repair truncated files with unbalanced braces
    open_braces = text.count('{') - text.count('}')
    if open_braces > 0:
        text = text.rstrip() + '\n' + ('}' * open_braces) + '\n'

    return text
