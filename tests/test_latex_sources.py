"""
tests/test_latex_sources.py
============================
Static validation of the actual LaTeX source files on disk.
These are integration / regression tests — they do not run the compiler,
but they assert invariants that prevent known XeLaTeX/bidi crashes and
structural regressions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import PROJECT_ROOT

LATEX_DIR    = PROJECT_ROOT / "latex"
CHAPTERS_DIR = LATEX_DIR / "chapters"
COVER_TEX    = CHAPTERS_DIR / "cover.tex"
MAIN_TEX     = LATEX_DIR / "main.tex"
REFS_BIB     = LATEX_DIR / "references.bib"

# Minimum number of BibTeX entries required in the template references.bib.
# The actual paper BibTeX is written by the agent; this just validates the template.
_MIN_BIB_ENTRIES = 10


def _strip_comments(tex: str) -> str:
    """Return only the non-comment lines of a .tex file (lines not starting with %)."""
    lines = [ln for ln in tex.splitlines() if not ln.lstrip().startswith("%")]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# cover.tex
# ---------------------------------------------------------------------------

def test_cover_tex_exists():
    """latex/chapters/cover.tex must exist on disk."""
    assert COVER_TEX.exists(), f"cover.tex not found at {COVER_TEX}"


def test_cover_tex_no_backslash_bracket():
    r"""cover.tex must NOT contain \\[ in code (triggers \@ifnextchar crash in bidi mode)."""
    code = _strip_comments(COVER_TEX.read_text(encoding="utf-8"))
    assert "\\[" not in code, (
        r"cover.tex contains \\[ which causes bidi/XeLaTeX \@ifnextchar crash"
    )


def test_cover_tex_uses_titlepage():
    r"""cover.tex must use \begin{titlepage} (not \begin{center} at top level)."""
    content = COVER_TEX.read_text(encoding="utf-8")
    assert r"\begin{titlepage}" in content


def test_cover_tex_no_begin_center_at_top_level():
    r"""cover.tex code must NOT contain \begin{center} (bidi crash risk at document level)."""
    code = _strip_comments(COVER_TEX.read_text(encoding="utf-8"))
    assert r"\begin{center}" not in code, (
        r"cover.tex contains \begin{center} which crashes XeLaTeX in bidi mode"
    )


# ---------------------------------------------------------------------------
# main.tex
# ---------------------------------------------------------------------------

def test_main_tex_exists():
    """latex/main.tex must exist on disk."""
    assert MAIN_TEX.exists(), f"main.tex not found at {MAIN_TEX}"


def test_main_tex_inputs_ch_naming():
    r"""main.tex must use \input{chapters/ch...} naming convention."""
    content = MAIN_TEX.read_text(encoding="utf-8")
    assert r"\input{chapters/ch" in content, (
        r"main.tex must contain \input{chapters/ch...} style includes"
    )


def test_main_tex_no_chapter_naming():
    r"""main.tex must NOT use the old \input{chapters/chapter...} naming."""
    content = MAIN_TEX.read_text(encoding="utf-8")
    assert r"\input{chapters/chapter" not in content, (
        r"main.tex uses deprecated \input{chapters/chapter...} naming"
    )


def test_main_tex_inputs_cover():
    r"""main.tex must include \input{chapters/cover}."""
    content = MAIN_TEX.read_text(encoding="utf-8")
    assert r"\input{chapters/cover" in content


def test_main_tex_bidi_last():
    r"""In main.tex, \usepackage{bidi} must appear AFTER \usepackage{polyglossia}."""
    # Strip comments so comment lines don't give false position readings
    code = _strip_comments(MAIN_TEX.read_text(encoding="utf-8"))
    pos_bidi        = code.find(r"\usepackage{bidi}")
    pos_polyglossia = code.find(r"\usepackage{polyglossia}")
    assert pos_bidi != -1,        r"\usepackage{bidi} not found in main.tex"
    assert pos_polyglossia != -1, r"\usepackage{polyglossia} not found in main.tex"
    assert pos_polyglossia < pos_bidi, (
        r"\usepackage{bidi} must be loaded AFTER \usepackage{polyglossia}"
    )


# ---------------------------------------------------------------------------
# references.bib
# ---------------------------------------------------------------------------

def test_references_bib_exists():
    """latex/references.bib must exist on disk."""
    assert REFS_BIB.exists(), f"references.bib not found at {REFS_BIB}"


def test_references_bib_has_minimum_entries():
    """references.bib template must have at least 10 BibTeX entries."""
    import re
    bib_text     = REFS_BIB.read_text(encoding="utf-8", errors="replace")
    entry_count  = len(re.findall(r"@\w+\{", bib_text))
    assert entry_count >= _MIN_BIB_ENTRIES, (
        f"references.bib has only {entry_count} entries; need ≥{_MIN_BIB_ENTRIES}"
    )


# ---------------------------------------------------------------------------
# Template chapters check
# ---------------------------------------------------------------------------

def test_only_cover_is_static():
    """Only cover.tex must exist in latex/chapters/ — ch01/ch04 are now agent-written."""
    existing = sorted(f.name for f in CHAPTERS_DIR.glob("*.tex"))
    assert existing == ["cover.tex"], (
        f"Expected only cover.tex in latex/chapters/; found: {existing}. "
        "ch01_intro.tex and ch04_slam.tex are now fully agent-written (dynamic)."
    )


# ---------------------------------------------------------------------------
# Stale naming check
# ---------------------------------------------------------------------------

def test_no_stale_chapter_naming():
    """No files matching latex/chapters/chapter*.tex must exist (old naming convention)."""
    stale = list(CHAPTERS_DIR.glob("chapter*.tex"))
    assert stale == [], (
        f"Stale chapter files found using old 'chapter*.tex' naming: "
        + ", ".join(f.name for f in stale)
    )
