"""
src/runner/sanitize_content.py
==============================
Sanitizer fixes 12a-19: \\en{} block repairs, algorithm-environment conversion,
tabular newline repair, Hebrew escape removal, math extraction.
Bodies moved verbatim from main.py's _sanitize_tex_files (150-line rule).
Fix order is preserved exactly: 12a, 12a2, 12a3, 12c, 13, 14, 15, 16, 25, 26, 17, 18, 19.
"""
from __future__ import annotations

import re


def apply_content_fixes(text: str) -> str:
    # Fix 12a: Unwrap \en{} from math mode — $\en{Word}$ → \en{Word}
    # Also handles \(\en{Word}\) syntax. Polyglossia \en{} does language-group
    # switching that breaks inside math mode.
    text = re.sub(r'\$\\en\{([^}]*)\}\$', r'\\en{\1}', text)
    text = re.sub(r'\\\(\\en\{([^}]*)\}\\\)', r'\\en{\1}', text)

    # Fix 12a2: Remove \begin{english}/\end{english} wrappers around tables.
    # The polyglossia english environment triggers font redefinition loops.
    # Tables work fine in Hebrew mode as long as % is escaped (Fix 11b).
    text = re.sub(r'\\begin\{english\}\s*\n(\\begin\{table)', r'\1', text)
    text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{english\}', r'\1', text)
    # Also remove \begin{LTR}/\end{LTR} wrappers (from previous sanitizer versions)
    text = re.sub(r'\\begin\{LTR\}\s*\n(\\begin\{table)', r'\1', text)
    text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{LTR\}', r'\1', text)

    # Fix 12a3: Unwrap \en{text} → text when it appears right before a closing }
    # This prevents bidi direction-switch corruption at group boundaries
    # (e.g., \caption{... \en{CNN}} → \caption{... CNN})
    text = re.sub(r'\\en\{([^}]*)\}(\s*\})', r'\1\2', text)

    # Fix 12c: Replace undefined \tabref{...} → \ref{...} and \figref{...} → \ref{...}.
    # LLM agents invent these macros but they're not defined in the IEEEtran template.
    # The undefined command causes cascading errors (Missing $, Extra }, Missing \endgroup).
    text = re.sub(r'\\tabref\{', r'\\ref{', text)
    text = re.sub(r'\\figref\{', r'\\ref{', text)
    text = re.sub(r'\\secref\{', r'\\ref{', text)

    # Fix 13: Replace \begin{algorithm}/\begin{algorithmic} with lstlisting.
    # The algorithm/algorithmic environments require packages not in our template.
    # Convert to lstlisting wrapped in english environment (which IS available).
    text = re.sub(
        r'\\begin\{algorithm\}(\[[^\]]*\])?',
        r'\\begin{english}\n\\begin{lstlisting}[language=Python]',
        text,
    )
    text = re.sub(r'\\end\{algorithm\}', r'\\end{lstlisting}\n\\end{english}', text)
    text = re.sub(r'\\begin\{algorithmic\}(\[[^\]]*\])?', '', text)
    text = re.sub(r'\\end\{algorithmic\}', '', text)
    # Remove \Require, \Ensure, \State, \If, \EndIf, \For, \EndFor, \While, \EndWhile, \Return
    # These are algorithmic package commands — convert to plain text pseudocode
    for cmd in [r'\\Require', r'\\Ensure', r'\\State', r'\\If', r'\\EndIf',
                r'\\For', r'\\EndFor', r'\\While', r'\\EndWhile', r'\\Return',
                r'\\Function', r'\\EndFunction', r'\\Procedure', r'\\EndProcedure']:
        text = re.sub(cmd + r'\b', '', text)

    # Fix 14: Fix literal \\n sequences in tabular rows.
    # LLM agents sometimes write \\n (Python-style newline) instead of
    # \\ + actual newline inside tabular environments. The literal 'n'
    # character after \\ breaks \midrule/\hline placement, causing
    # "Misplaced \noalign" errors and potential xelatex infinite loops.
    # Replace \\n followed by a LaTeX command with \\ + real newline.
    text = re.sub(r'\\\\n(\\[a-zA-Z])', r'\\\\\n\1', text)
    # Also fix \\n at end of line (should just be \\)
    text = re.sub(r'\\\\n\s*$', r'\\\\', text, flags=re.MULTILINE)

    # Fix 15: Remove backslash before Hebrew characters.
    # LLM agents sometimes write \ש, \מ etc. (backslash + Hebrew letter)
    # which LaTeX interprets as undefined control sequences.
    # Hebrew Unicode range: ֐-׿ (Hebrew block).
    text = re.sub(r'\\([֐-׿])', r'\1', text)

    # Fix 16: Escape underscores inside \en{...} blocks.
    # LLM agents write \en{sonar_driver} but _ is a math-mode subscript
    # operator that causes "Missing $ inserted" cascading errors.
    # Replace _ with \_ only inside \en{...} content.
    def _escape_underscores_in_en(m: re.Match) -> str:
        return r'\en{' + m.group(1).replace('_', r'\_') + '}'
    text = re.sub(r'\\en\{([^}]*_[^}]*)\}', _escape_underscores_in_en, text)

    # Fix 25: Extract math superscripts/subscripts from \en{} blocks.
    # LLM writes \en{m/s^2} or \en{R^2} but ^ is a math-mode operator
    # that crashes in text mode. Split: \en{m/s^2} → \en{m/s}$^2$
    # Handles ^N (single digit) and ^{...} (braced group).
    def _fix_math_in_en(m: re.Match) -> str:
        content = m.group(1)
        # Split at first ^ that's followed by a digit or {
        caret = re.search(r'\^(\{[^}]*\}|\d+)', content)
        if not caret:
            return m.group(0)
        before = content[:caret.start()]
        math_part = caret.group(0)  # e.g. ^2 or ^{2}
        after = content[caret.end():]
        result = r'\en{' + before + '}'
        result += '$' + math_part + '$'
        if after:
            result += r'\en{' + after + '}'
        return result
    text = re.sub(r'\\en\{([^}]*\^[^}]*)\}', _fix_math_in_en, text)

    # Fix 26: Wrap bare math expressions in $...$. LLMs sometimes write
    # inline math like p(z_t^s | x_t, m) directly in Hebrew prose without
    # dollar signs. Detect sequences with _ or ^ outside of math mode and
    # wrap them. Pattern: word-char followed by _ or ^ with sub/superscript,
    # possibly with parentheses and pipes — common probability notation.
    text = re.sub(
        r'(?<!\$)(?<!\\)'           # not already in math or escaped
        r'([A-Za-z]\w*'             # starts with a letter+word chars (e.g. "p")
        r'\([^)]*[_^][^)]*\))',     # parenthesized group containing _ or ^
        r'$\1$',
        text,
    )

    # Fix 17: Replace \° (undefined control sequence) with Unicode °.
    # LLM agents write 5\° for "5 degrees" but \° is not a valid LaTeX
    # command. XeLaTeX handles the Unicode ° glyph natively via fontspec.
    text = text.replace("\\°", "°")

    # Fix 18: Replace \textquoteright with / (forward slash).
    # LLM writes "מ\textquoterightש" for "m/s" — \textquoteright is
    # undefined in this XeLaTeX bidi setup and crashes compilation.
    text = text.replace("\\textquoteright", "/")
    text = text.replace("\\textquoteleft", "/")

    # Fix 19: Convert single-row \begin{bmatrix}...\end{bmatrix} to
    # \left[...\right] notation. bidi package conflicts with bmatrix's
    # alignment tabs (&) causing "Extra alignment tab" fatal errors.
    # Only affects row vectors (single line between begin/end).
    def _fix_row_bmatrix(m):
        inner = m.group(1).strip()
        # Replace & with ,\; for comma-separated vector notation
        inner = inner.replace(" & ", r",\; ")
        return r"\left[" + inner + r"\right]"
    text = re.sub(
        r"\\begin\{bmatrix\}\s*([^\n]*?)\s*\\end\{bmatrix\}",
        _fix_row_bmatrix,
        text,
    )

    return text
