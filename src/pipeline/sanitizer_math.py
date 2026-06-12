"""
sanitizer_math.py
=================
Bare-math-symbol wrapper helpers used by the LaTeX sanitizer (Fix 12b).

Wraps Greek letters and common math symbols in $...$ when they appear
outside math mode in Hebrew prose.
"""

import re

# Greek letters + common math symbols that agents write bare in Hebrew prose
_BARE_MATH_NAMES = [
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'varepsilon',
    'sigma', 'theta', 'lambda', 'mu', 'omega', 'phi', 'varphi',
    'psi', 'tau', 'eta', 'rho', 'nu', 'xi', 'kappa', 'zeta', 'chi', 'pi',
    'Delta', 'Sigma', 'Omega', 'Phi', 'Psi', 'Gamma', 'Theta', 'Lambda', 'Pi',
    'infty', 'nabla', 'partial', 'pm', 'times', 'cdot', 'approx', 'neq',
    'leq', 'geq', 'equiv', 'subset', 'supset', 'forall', 'exists',
    'rightarrow', 'leftarrow', 'Rightarrow', 'Leftarrow',
]

# Regex: match \<symbol> NOT followed by more letters (avoid partial match on e.g. \alphabeta)
_BARE_MATH_RE = re.compile(
    r'(\\(?:' + '|'.join(_BARE_MATH_NAMES) + r'))(?![a-zA-Z])'
)

# Math environment names (for tracking nesting depth)
_MATH_ENV_NAMES = {
    'equation', 'equation*', 'align', 'align*', 'gather', 'gather*',
    'multline', 'multline*', 'eqnarray', 'eqnarray*', 'math',
    'displaymath', 'flalign', 'flalign*', 'split',
}


def _wrap_bare_math_in_text(text: str) -> str:
    """
    Wrap bare Greek letters and math symbols in $...$ when they appear outside
    math mode.  Protects existing math environments and inline $...$ first,
    then wraps remaining bare commands, then restores protected regions.
    """
    placeholders: list[str] = []

    def _save(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f'\x00MATH{len(placeholders) - 1}\x00'

    protected = text

    # 1. Protect math environments (multi-line, order matters: * variants first)
    for env in ['equation*', 'equation', 'align*', 'align', 'gather*', 'gather',
                'multline*', 'multline', 'eqnarray*', 'eqnarray', 'displaymath',
                'math', 'flalign*', 'flalign', 'split']:
        pat = r'\\begin\{' + re.escape(env) + r'\}.*?\\end\{' + re.escape(env) + r'\}'
        protected = re.sub(pat, _save, protected, flags=re.DOTALL)

    # 2. Protect display math \[...\]
    protected = re.sub(r'\\\[.*?\\\]', _save, protected, flags=re.DOTALL)

    # 3. Protect inline math $...$ (single-line, non-greedy)
    protected = re.sub(r'(?<!\\)\$(?!\$)(.+?)(?<!\\)\$', _save, protected)

    # 4. Protect $$...$$ display math
    protected = re.sub(r'\$\$.*?\$\$', _save, protected, flags=re.DOTALL)

    # 5. Wrap bare math commands (e.g. \alpha -> $\alpha$)
    protected = _BARE_MATH_RE.sub(r'$\1$', protected)

    # 6. Merge adjacent $...$$...$  ->  $... ...$  (avoid ugly $$)
    protected = re.sub(r'\$\$', ' ', protected)

    # 7. Restore placeholders (reverse order for safety)
    for i in range(len(placeholders) - 1, -1, -1):
        protected = protected.replace(f'\x00MATH{i}\x00', placeholders[i])

    return protected
