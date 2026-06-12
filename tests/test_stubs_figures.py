"""
tests/test_stubs_figures.py
===========================
Coverage for:
  * src/stubs.py                    — dry-run stub chapter generator + helpers
  * src/runner/figure_styles_a.py   — fallback matplotlib figure renderers (A)
  * src/runner/figure_styles_c.py   — fallback matplotlib figure renderers (C)

All tests are deterministic, offline, and fast. matplotlib is forced onto the
headless Agg backend BEFORE the figure modules are imported so no display is
ever required.
"""

from __future__ import annotations

# --- Force headless matplotlib backend BEFORE importing the figure modules ---
import matplotlib

matplotlib.use("Agg")

from pathlib import Path  # noqa: E402

from src import stubs  # noqa: E402

# ---------------------------------------------------------------------------
# src/stubs.py
# ---------------------------------------------------------------------------


def test_stub_png_is_valid_png_bytes() -> None:
    """_stub_png() returns PNG bytes with the correct 8-byte signature and IEND."""
    data = stubs._stub_png()
    assert isinstance(data, bytes)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IHDR" in data
    assert b"IDAT" in data
    assert data.rstrip().endswith(b"IEND\xae\x42\x60\x82") or b"IEND" in data
    assert len(data) > 8


def test_words_returns_n_space_joined_words() -> None:
    """_words(n) returns exactly n filler tokens drawn from the Hebrew pool."""
    out = stubs._words(120)
    tokens = out.split()
    assert len(tokens) == 120
    assert all(t for t in tokens)
    # words come from the _FILL pool
    pool = set(stubs._FILL.split())
    assert set(tokens).issubset(pool)
    # small counts work too
    assert len(stubs._words(5).split()) == 5
    assert stubs._words(0) == ""


def test_references_bib_contains_every_key() -> None:
    """_references_bib() emits one @misc entry per key in _BIB_KEYS."""
    bib = stubs._references_bib()
    assert isinstance(bib, str)
    assert bib.count("@misc{") == len(stubs._BIB_KEYS)
    for key in stubs._BIB_KEYS:
        assert f"@misc{{{key}," in bib
    assert "dry-run stub" in bib
    # satisfies MIN_BIB_ENTRIES=10
    assert len(stubs._BIB_KEYS) >= 10


def test_abstract_stub_has_language_switch_and_words() -> None:
    """_abstract_stub() begins with a Hebrew language switch then 120 filler words."""
    abstract = stubs._abstract_stub()
    assert abstract.startswith(r"\selectlanguage{hebrew}")
    # 120 filler words follow the language switch on the next line
    body = abstract.split("\n", 1)[1]
    assert len(body.split()) >= 120


def test_chapter_stub_structure() -> None:
    """_chapter_stub() builds a section with the requested subsections,
    equations, figures, and citations."""
    tex = stubs._chapter_stub(
        section="מבחן",
        ch_id="chXX",
        n_sub=3,
        n_eq=2,
        n_fig=1,
        n_cite=2,
        n_words=650,
    )
    assert r"\selectlanguage{hebrew}" in tex
    assert r"\section{מבחן}" in tex
    assert r"\label{sec:chXX}" in tex
    assert tex.count(r"\subsection{") == 3
    # only the first n_eq subsections carry equations
    assert tex.count(r"\begin{equation}") == 2
    assert tex.count(r"\begin{figure}[H]") == 1
    assert tex.count(r"\includegraphics") == 1
    assert "figures/fig_stub.png" in tex
    assert tex.count(r"\cite{") == 2
    # citation keys are drawn from the bib key list
    assert any(f"\\cite{{{stubs._BIB_KEYS[k]}}}" in tex for k in range(2))


def test_chapter_stub_zero_optional_blocks() -> None:
    """_chapter_stub() with no subsections/equations/figures/citations still
    produces a valid section body (covers the loop-skipping branches)."""
    tex = stubs._chapter_stub(
        section="ריק",
        ch_id="ch00",
        n_sub=0,
        n_eq=0,
        n_fig=0,
        n_cite=0,
        n_words=120,
    )
    assert r"\section{ריק}" in tex
    assert r"\begin{equation}" not in tex
    assert r"\begin{figure}[H]" not in tex
    assert tex.count(r"\subsection{") == 0
    assert tex.rstrip().endswith(".")  # the \en{See} . line


def test_write_stub_chapters_creates_all_files(tmp_path: Path) -> None:
    """write_stub_chapters() writes 10 chapter files + references.bib + PNG
    under run_folder/latex/, all with expected LaTeX markers."""
    stubs.write_stub_chapters(tmp_path, topic="bio-inspired navigation")

    latex = tmp_path / "latex"
    chapters = latex / "chapters"
    figures = latex / "figures"
    bib = latex / "references.bib"

    # Directory structure
    assert chapters.is_dir()
    assert figures.is_dir()

    # Stub PNG
    png = figures / "fig_stub.png"
    assert png.is_file()
    png_bytes = png.read_bytes()
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png_bytes) > 8

    # references.bib
    assert bib.is_file()
    bib_text = bib.read_text(encoding="utf-8")
    assert bib_text.count("@misc{") == len(stubs._BIB_KEYS)

    # All 10 chapter files exist
    expected = list(stubs._CHAPTERS.keys())
    assert len(expected) == 10
    for fname in expected:
        fpath = chapters / fname
        assert fpath.is_file(), f"missing {fname}"
        content = fpath.read_text(encoding="utf-8")
        assert r"\selectlanguage{hebrew}" in content

    # The abstract uses the abstract stub (no \section heading)
    abstract = (chapters / "abstract.tex").read_text(encoding="utf-8")
    assert r"\section{" not in abstract

    # A normal chapter uses the full chapter stub (has a \section)
    intro = (chapters / "ch01_intro.tex").read_text(encoding="utf-8")
    assert r"\section{" in intro
    assert r"\begin{equation}" in intro


# ---------------------------------------------------------------------------
# src/runner/figure_styles_a.py  and  figure_styles_c.py
# ---------------------------------------------------------------------------


