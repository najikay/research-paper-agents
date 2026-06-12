"""
src/graph/nodes_quality.py
===========================
Quality gate scoring: structural checks on generated LaTeX chapters.
"""

from __future__ import annotations

import re
from pathlib import Path

QUALITY_THRESHOLD = 90
MAX_REMEDIATIONS = 4
MIN_BIB_ENTRIES = 10

AGENT_CHAPTERS = [
    "abstract.tex",
    "ch01_intro.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]

_CHAPTER_MIN_REQS: dict[str, dict] = {
    "abstract.tex":        {"eq": 0, "fig": 0, "sub": 0, "cite": 0, "words": 80},
    "ch01_intro.tex":      {"eq": 1, "fig": 0, "sub": 3, "cite": 2, "words": 1400},
    "ch06_algorithm.tex":  {"eq": 3, "fig": 1, "sub": 5, "cite": 3, "words": 1800},
    "ch07_oursystem.tex":  {"eq": 2, "fig": 1, "sub": 4, "cite": 2, "words": 1600},
    "ch08_results.tex":    {"eq": 2, "fig": 1, "sub": 5, "cite": 3, "words": 1800},
    "ch09_conclusion.tex": {"eq": 0, "fig": 0, "sub": 2, "cite": 1, "words": 700},
}
_DEFAULT_MIN_REQS: dict = {"eq": 2, "fig": 1, "sub": 3, "cite": 2, "words": 1400}


def _score_chapters(chapters_dir: Path) -> tuple[int, list[str], list[str]]:
    """Check structural elements per chapter. Returns (penalty, issues, failed)."""
    penalty = 0
    issues: list[str] = []
    failed: list[str] = []

    missing_files = []
    for fname in AGENT_CHAPTERS:
        fpath = chapters_dir / fname
        if not fpath.exists() or fpath.stat().st_size < 200:
            missing_files.append(fname)
            penalty += 8
    if missing_files:
        issues.append(f"Missing or empty chapter files: {missing_files}")
        failed.extend(["introduction", "methodology", "algorithms"])

    for fname in AGENT_CHAPTERS:
        fpath = chapters_dir / fname
        if not fpath.exists():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")
        reqs = _CHAPTER_MIN_REQS.get(fname, _DEFAULT_MIN_REQS)
        eq_count = len(re.findall(r"\\begin\{equation\}", text))
        fig_count = len(re.findall(r"\\includegraphics", text))
        sub_count = len(re.findall(r"\\subsection\{", text))
        cite_count = len(re.findall(r"\\cite\{", text))
        word_est = len(text.split())

        ch_issues = []
        if eq_count < reqs["eq"]:
            ch_issues.append(f"equations={eq_count}<{reqs['eq']}")
            penalty += 3
        if fig_count < reqs["fig"]:
            ch_issues.append(f"figures={fig_count}<{reqs['fig']}")
            penalty += 3
        if sub_count < reqs["sub"]:
            ch_issues.append(f"subsections={sub_count}<{reqs['sub']}")
            penalty += 2
        if cite_count < reqs["cite"]:
            ch_issues.append(f"citations={cite_count}<{reqs['cite']}")
            penalty += 2
        if word_est < reqs["words"]:
            ch_issues.append(f"words≈{word_est}<{reqs['words']}")
            penalty += 4
            failed.append("methodology")
        if ch_issues:
            issues.append(f"{fname}: " + ", ".join(ch_issues))

    return penalty, issues, failed


def _score_bib_and_figures(
    run_folder: Path, chapters_dir: Path, bib_path: Path,
) -> tuple[int, list[str], list[str]]:
    """Check references.bib and figure refs. Returns (penalty, issues, failed)."""
    penalty = 0
    issues: list[str] = []
    failed: list[str] = []

    if bib_path.exists():
        bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
        entry_count = len(re.findall(r"@\w+\{", bib_text))
        if entry_count < MIN_BIB_ENTRIES:
            issues.append(f"references.bib has only {entry_count} entries (need ≥{MIN_BIB_ENTRIES})")
            penalty += max(0, (MIN_BIB_ENTRIES - entry_count) * 2)
            failed.append("references")
    else:
        issues.append("references.bib does not exist")
        penalty += 20
        failed.append("references")

    figures_dir = run_folder / "latex" / "figures"
    missing_fig_penalty = 0
    for fpath in chapters_dir.glob("*.tex"):
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text):
            if not (figures_dir / fig_ref).exists():
                issues.append(f"{fpath.name}: missing figure file 'figures/{fig_ref}'")
                failed.append("figures")
                if missing_fig_penalty < 20:
                    missing_fig_penalty += 2
    penalty += missing_fig_penalty

    static_files = {"cover.tex"}
    agent_tex = [f for f in chapters_dir.glob("*.tex") if f.name not in static_files]
    placeholder_files, emdash_files, center_files = [], [], []
    for fpath in agent_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if "PLACEHOLDER" in text or r"\fbox{\parbox" in text:
            placeholder_files.append(fpath.name)
        clean = re.sub(r"\\en\{[^}]*\}", "", text)
        if "\u2014" in clean:
            emdash_files.append(fpath.name)
        if r"\begin{center}" in text:
            center_files.append(fpath.name)

    if placeholder_files:
        issues.append(f"Placeholder boxes found in: {placeholder_files}")
        penalty += 5
        failed.append("figures")
    if emdash_files:
        issues.append(f"Em dashes in Hebrew prose: {emdash_files}")
        penalty += 2
    if center_files:
        issues.append(f"\\begin{{center}} at document level (bidi crash risk): {center_files}")
        penalty += 10
        failed.append("methodology")

    return penalty, issues, failed
