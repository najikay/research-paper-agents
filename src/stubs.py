"""
src/stubs.py
============
Stub chapter generator for --dry-run mode.

Writes minimal-but-quality-gate-passing XeLaTeX to all chapter files without
any LLM calls. Used exclusively to validate the PDF compilation pipeline:
  • Does the file structure work?
  • Does xelatex compile the Hebrew/bidi document without crashing?
  • Does the PDF open?

Nothing here touches an LLM. A full dry-run completes in under 30 seconds.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from src.config import logger


# ---------------------------------------------------------------------------
# Minimal 1×1 white PNG (referenced by every chapter's figure stub)
# ---------------------------------------------------------------------------

def _stub_png() -> bytes:
    """Build a valid 1×1 white RGB PNG entirely in memory."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"                                          # signature
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))  # 1×1, 8-bit RGB
        + chunk(b"IDAT", zlib.compress(b"\x00\xFF\xFF\xFF"))            # white pixel
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Hebrew filler text (valid Unicode — not meaningful, just hits word counts)
# ---------------------------------------------------------------------------

_FILL = (
    "מחקר מערכת אלגוריתם ניתוח תוצאות שיטה מודל פתרון חישן נתון "
    "עיבוד מדידה הערכה ביצוע ניסוי בדיקה תוצאה מסקנה מבנה ארכיטקטורה "
    "תכנון יישום פיתוח הדמיה מיפוי ניווט מיקום זיהוי סיווג אומדן "
    "גישה מסגרת כלי תהליך שלב מרכיב רכיב מודול מנגנון ביצועים שיפור "
)


def _words(n: int) -> str:
    pool = (_FILL.split() * ((n // 40) + 2))
    return " ".join(pool[:n])


# ---------------------------------------------------------------------------
# BibTeX stub (≥14 entries — satisfies MIN_BIB_ENTRIES=10 quality check)
# ---------------------------------------------------------------------------

_BIB_KEYS = [
    "Thrun2005", "Kalman1960", "Grisetti2010", "MurArtal2015",
    "Julier1997", "Griffin1958", "Simmons1979", "Schnitzler1968",
    "Schuller1974", "Rihaczek1969", "CrewAIDocs", "AnthropicClaude",
    "LeCun2015", "Vaswani2017",
]


def _references_bib() -> str:
    entries = []
    for key in _BIB_KEYS:
        entries.append(
            f"@misc{{{key},\n"
            f"  author = {{Author, A.}},\n"
            f"  title  = {{Stub: {key}}},\n"
            f"  year   = {{2024}},\n"
            f"  note   = {{dry-run stub}}\n"
            f"}}"
        )
    return "\n\n".join(entries) + "\n"


# ---------------------------------------------------------------------------
# Abstract stub (no section heading — inserted inside \begin{abstract})
# ---------------------------------------------------------------------------

def _abstract_stub() -> str:
    return r"\selectlanguage{hebrew}" + "\n" + _words(120) + "\n"


# ---------------------------------------------------------------------------
# Generic chapter stub
# ---------------------------------------------------------------------------

def _chapter_stub(
    section: str,
    ch_id: str,
    n_sub: int,
    n_eq: int,
    n_fig: int,
    n_cite: int,
    n_words: int,
) -> str:
    words_per_block = max(80, n_words // (n_sub + 1))
    lines = [
        r"\selectlanguage{hebrew}",
        f"\\section{{{section}}}",
        f"\\label{{sec:{ch_id}}}",
        "",
        _words(words_per_block),
        "",
    ]

    for i in range(1, n_sub + 1):
        lines += [
            f"\\subsection{{{section} {i}}}",
            f"\\label{{sub:{ch_id}_{i}}}",
            _words(words_per_block),
            "",
        ]
        if i <= n_eq:
            lines += [
                r"\begin{equation}",
                f"    x_{{k+{i}}} = A_{{k}} x_k + B u_{{k}} + w_{{{i}}}",
                f"    \\label{{eq:{ch_id}_{i}}}",
                r"\end{equation}",
                _words(15),
                "",
            ]

    for j in range(1, n_fig + 1):
        lines += [
            r"\begin{figure}[H]",
            r"    \centering",
            f"    \\includegraphics[width=0.9\\columnwidth]{{figures/fig_stub.png}}",
            f"    \\caption{{\\en{{Stub figure {j} — {ch_id}}}}}",
            f"    \\label{{fig:{ch_id}_{j}}}",
            r"\end{figure}",
            "",
        ]

    cite_str = "".join(
        f"\\cite{{{_BIB_KEYS[k % len(_BIB_KEYS)]}}}"
        for k in range(n_cite)
    )
    lines.append(f"\\en{{See}} {cite_str}.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Chapter manifest (satisfies every quality-gate threshold)
# ---------------------------------------------------------------------------
#
#  Quality-gate minimums (from _CHAPTER_MIN_REQS in nodes.py):
#    abstract:  words≥50
#    ch01:      eq≥1, sub≥2, cite≥2, words≥400
#    ch02–ch08: eq≥3, sub≥3, fig≥1, cite≥2, words≥600
#    ch09:      sub≥2, cite≥1, words≥300

_CHAPTERS: dict[str, dict] = {
    "abstract.tex":        dict(section="תקציר",         ch_id="abstract", n_sub=0, n_eq=0, n_fig=0, n_cite=0, n_words=120),
    "ch01_intro.tex":      dict(section="מבוא",           ch_id="ch01",     n_sub=2, n_eq=1, n_fig=0, n_cite=2, n_words=450),
    "ch02_bio_basis.tex":  dict(section="בסיס",           ch_id="ch02",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch03_sensors.tex":    dict(section="חישנים",         ch_id="ch03",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch04_slam.tex":       dict(section="אלגוריתמים",     ch_id="ch04",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch05_fusion.tex":     dict(section="היתוך",          ch_id="ch05",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch06_algorithm.tex":  dict(section="אלגוריתם",       ch_id="ch06",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch07_oursystem.tex":  dict(section="מערכת",          ch_id="ch07",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch08_results.tex":    dict(section="תוצאות",         ch_id="ch08",     n_sub=3, n_eq=3, n_fig=1, n_cite=2, n_words=650),
    "ch09_conclusion.tex": dict(section="סיכום",          ch_id="ch09",     n_sub=2, n_eq=0, n_fig=0, n_cite=1, n_words=350),
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def write_stub_chapters(run_folder: Path, topic: str) -> None:  # noqa: ARG001
    """
    Write minimal valid XeLaTeX stubs to run_folder/latex/.
    Creates 10 chapter files + references.bib + a 1×1 PNG for figure refs.
    All files satisfy every quality-gate threshold. No LLM calls made.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    figures_dir  = run_folder / "latex" / "figures"
    bib_path     = run_folder / "latex" / "references.bib"

    chapters_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Stub figure (1×1 white PNG — satisfies figure-existence check)
    (figures_dir / "fig_stub.png").write_bytes(_stub_png())

    # Write chapters
    for fname, kwargs in _CHAPTERS.items():
        fpath = chapters_dir / fname
        if fname == "abstract.tex":
            content = _abstract_stub()
        else:
            content = _chapter_stub(**kwargs)
        fpath.write_text(content, encoding="utf-8")

    # Write BibTeX
    bib_path.write_text(_references_bib(), encoding="utf-8")

    logger.info(
        f"[DryRun] Stubs written: {len(_CHAPTERS)} chapters + "
        f"references.bib + fig_stub.png → {run_folder.name}"
    )
