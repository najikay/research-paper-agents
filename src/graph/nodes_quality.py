"""
src/graph/nodes_quality.py
===========================
Quality gate scoring: structural checks on generated LaTeX chapters.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.config import logger
from src.graph.nodes_quality_report import score_bib_and_figures, write_quality_report
from src.graph.state import PipelineState

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


def run_quality_gate(state: PipelineState) -> dict:
    """Programmatic quality check of generated LaTeX files."""
    logger.info("[Graph] NODE: run_quality_gate (programmatic)")
    run_folder = Path(state["run_folder"])

    from main import (
        _deduplicate_cross_chapter_figures,
        _diversify_stub_figures,
        _generate_fallback_figures,
        _sanitize_tex_files,
        validate_and_fix_chapters,
    )
    validate_and_fix_chapters(run_folder)
    _diversify_stub_figures(run_folder)
    _deduplicate_cross_chapter_figures(run_folder)
    _generate_fallback_figures(run_folder)
    _sanitize_tex_files(run_folder / "latex" / "chapters")

    chapters_dir = run_folder / "latex" / "chapters"
    bib_path = run_folder / "latex" / "references.bib"

    ch_penalty, ch_issues, ch_failed = _score_chapters(chapters_dir)
    bf_penalty, bf_issues, bf_failed = score_bib_and_figures(
        run_folder, chapters_dir, bib_path, MIN_BIB_ENTRIES,
    )

    issues = ch_issues + bf_issues
    failed_sections = sorted(set(ch_failed + bf_failed))
    score = max(0, min(100, 100 - ch_penalty - bf_penalty))
    verdict = "PASS" if score >= QUALITY_THRESHOLD else "FAIL"

    write_quality_report(
        score, verdict, QUALITY_THRESHOLD, failed_sections, issues,
        _CHAPTER_MIN_REQS, _DEFAULT_MIN_REQS, MIN_BIB_ENTRIES,
    )

    return {
        "quality_verdict": verdict,
        "quality_score": score,
        "failed_sections": failed_sections,
    }
