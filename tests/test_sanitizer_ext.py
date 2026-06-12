"""
tests/test_sanitizer_ext.py
============================
Extended tests for _apply_content_fixes_impl covering previously-uncovered branches.
"""

from __future__ import annotations

from src.pipeline.sanitizer_core import _apply_content_fixes_impl

# ---------------------------------------------------------------------------
# Fix 16: Escape underscores inside \en{} blocks  (line 73)
# ---------------------------------------------------------------------------

def test_escape_underscores_in_en_single():
    result = _apply_content_fixes_impl(r"\en{some_var}")
    assert r"\en{some\_var}" in result


def test_escape_underscores_in_en_multiple():
    result = _apply_content_fixes_impl(r"\en{a_b_c}")
    assert r"\en{a\_b\_c}" in result


def test_escape_underscores_in_en_no_underscore_unchanged():
    result = _apply_content_fixes_impl(r"\en{plain text}")
    assert r"\en{plain text}" in result


# ---------------------------------------------------------------------------
# Fix 25: Extract math superscripts from \en{} blocks  (lines 78-89)
# ---------------------------------------------------------------------------

def test_fix_math_in_en_with_trailing_text():
    """Digit exponent with trailing text: exercises the 'if after' branch (line 87-88)."""
    result = _apply_content_fixes_impl(r"\en{x^2 rest}")
    assert r"\en{x}" in result
    assert "$^2$" in result
    assert r"\en{ rest}" in result


def test_fix_math_in_en_digit_exponent():
    result = _apply_content_fixes_impl(r"\en{y^3}")
    assert r"\en{y}" in result
    assert "$^3$" in result


def test_fix_math_in_en_no_trailing():
    """Digit exponent with no trailing text: 'after' is empty, no extra \\en{} appended."""
    result = _apply_content_fixes_impl(r"\en{x^2}")
    assert r"\en{x}" in result
    assert "$^2$" in result
    count = result.count(r"\en{")
    assert count == 1


def test_fix_math_in_en_no_caret_unchanged():
    text = r"\en{no caret here}"
    result = _apply_content_fixes_impl(text)
    assert r"\en{no caret here}" in result


# ---------------------------------------------------------------------------
# Fix 19: Single-row bmatrix -> \left[...\right]  (lines 110-112)
# ---------------------------------------------------------------------------

def test_fix_row_bmatrix_basic():
    text = r"\begin{bmatrix}a & b\end{bmatrix}"
    result = _apply_content_fixes_impl(text)
    assert r"\left[" in result
    assert r"\right]" in result
    assert r",\; " in result
    assert r"\begin{bmatrix}" not in result


def test_fix_row_bmatrix_three_elements():
    text = r"\begin{bmatrix}x & y & z\end{bmatrix}"
    result = _apply_content_fixes_impl(text)
    assert r"\left[x,\; y,\; z\right]" in result


# ---------------------------------------------------------------------------
# Fix 21: Author commands -> \en{AuthorName}  (lines 121-124)
# ---------------------------------------------------------------------------

def test_fix_author_cmd_converted():
    text = r"\Thrun is a researcher"
    result = _apply_content_fixes_impl(text)
    assert r"\en{Thrun}" in result


def test_fix_author_cmd_camel_case():
    text = r"\DeepSeek model"
    result = _apply_content_fixes_impl(text)
    assert r"\en{DeepSeek}" in result


def test_fix_author_cmd_safe_cmd_unchanged():
    text = r"\Alpha is a Greek letter"
    result = _apply_content_fixes_impl(text)
    assert r"\Alpha" in result
    assert r"\en{Alpha}" not in result


def test_fix_author_cmd_latex_unchanged():
    text = r"\LaTeX is a typesetting system"
    result = _apply_content_fixes_impl(text)
    assert r"\en{LaTeX}" not in result


# ---------------------------------------------------------------------------
# Fix 22: \ensuremath{content} -> $content$  (lines 130-140)
# ---------------------------------------------------------------------------

def test_ensuremath_simple():
    text = r"\ensuremath{x+1}"
    result = _apply_content_fixes_impl(text)
    assert "$x+1$" in result
    assert r"\ensuremath" not in result


def test_ensuremath_nested_braces():
    text = r"\ensuremath{x^{2}}"
    result = _apply_content_fixes_impl(text)
    assert "$x^{2}$" in result
    assert r"\ensuremath" not in result


def test_ensuremath_strips_inner_dollars():
    text = r"\ensuremath{$y$}"
    result = _apply_content_fixes_impl(text)
    assert "y" in result
    assert r"\ensuremath" not in result


def test_ensuremath_multiple():
    text = r"A \ensuremath{a} and \ensuremath{b} end"
    result = _apply_content_fixes_impl(text)
    assert "$a$" in result
    assert "$b$" in result
    assert r"\ensuremath" not in result


# ---------------------------------------------------------------------------
# Fix 20: Unbalanced braces  (line 160)
# ---------------------------------------------------------------------------

def test_unbalanced_braces_adds_closing():
    text = r"\textbf{hello"
    result = _apply_content_fixes_impl(text)
    assert result.count("{") == result.count("}")


def test_unbalanced_braces_multiple():
    text = "a{b{c"
    result = _apply_content_fixes_impl(text)
    assert result.count("{") == result.count("}")


def test_balanced_braces_unchanged():
    text = r"\textbf{hello}"
    result = _apply_content_fixes_impl(text)
    assert result.count("{") == result.count("}")
    assert r"\textbf{hello}" in result
