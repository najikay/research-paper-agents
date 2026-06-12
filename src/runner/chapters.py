"""
src/runner/chapters.py
======================
Chapter-file validation and figure-reference normalization.
Code moved verbatim from main.py (150-line rule).
"""
from __future__ import annotations

import re
from pathlib import Path

from src.config import logger

# Expected chapter filenames (must match main.tex \input{} calls)
EXPECTED_CHAPTERS = [
    "abstract.tex", "ch01_intro.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]


def validate_and_fix_chapters(run_folder: Path) -> None:
    """
    Detect agent-created chapter files with wrong names and rename them
    to match the expected filenames in main.tex.

    Problem: DeepSeek sometimes writes ch03_ultrasonic_sensor.tex instead of
    ch03_sensors.tex, or ch07_embedded.tex instead of ch07_oursystem.tex.
    These files are invisible to main.tex and wasted effort.

    Strategy:
      1. For each expected filename that is MISSING, look for any .tex file
         matching the same chapter prefix (ch03_*, ch07_*, etc.).
      2. If found and the expected file doesn't exist, rename it.
      3. If multiple candidates exist, pick the largest (most content).
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    existing = {f.name for f in chapters_dir.glob("*.tex")}
    protected = {"cover.tex"}

    for expected in EXPECTED_CHAPTERS:
        if expected in existing:
            continue  # already present

        # Extract chapter prefix: "ch03" from "ch03_sensors.tex"
        prefix = expected.split("_")[0]  # "ch03", "ch01", "abstract"
        if prefix == "abstract":
            continue  # abstract.tex has a unique name, no prefix variants

        # Find all non-expected files matching this prefix
        candidates = []
        for f in chapters_dir.glob(f"{prefix}_*.tex"):
            if f.name not in EXPECTED_CHAPTERS and f.name not in protected:
                candidates.append(f)

        if not candidates:
            continue

        # Pick the largest candidate (most content)
        best = max(candidates, key=lambda f: f.stat().st_size)
        target = chapters_dir / expected
        best.rename(target)
        logger.info(f"[Validate] Renamed {best.name} → {expected} (rescued wrong filename)")

    # Remove any remaining extra chapter files that don't match expected names
    # (they won't be included in the PDF anyway)
    final_files = {f.name for f in chapters_dir.glob("*.tex")}
    extras = final_files - set(EXPECTED_CHAPTERS) - protected
    if extras:
        logger.warning(f"[Validate] Extra chapter files (not in main.tex, ignored): {extras}")


def _diversify_stub_figures(run_folder: Path) -> None:
    """
    Replace shared fig_stub.png references with chapter-specific filenames.

    In smoke mode (and sometimes when the VisualizationEngineer fails), every
    chapter points to the same ``figures/fig_stub.png``.  This function rewrites
    each chapter's \\includegraphics to use a unique per-chapter filename so the
    fallback generator can create visually distinct figures for each chapter.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        if "fig_stub.png" not in text:
            continue
        # Extract chapter id from filename (e.g. "ch02" from "ch02_bio_basis.tex")
        ch_match = re.match(r"(ch\d+)", tex_file.name)
        if not ch_match:
            continue
        ch_id = ch_match.group(1)

        # Count how many stub refs this chapter has and assign unique names
        occurrence = [0]

        def _replace_stub(m: re.Match) -> str:
            occurrence[0] += 1
            suffix = f"_{occurrence[0]}" if occurrence[0] > 1 else ""
            return m.group(0).replace("fig_stub.png", f"fig_{ch_id}_auto{suffix}.png")

        new_text = re.sub(
            r'\\includegraphics(\[[^\]]*\])?\{figures/fig_stub\.png\}',
            _replace_stub,
            text,
        )
        if new_text != text:
            tex_file.write_text(new_text, encoding="utf-8")
            logger.info(f"[Diversify] {tex_file.name}: replaced fig_stub.png → chapter-specific names")


def _deduplicate_cross_chapter_figures(run_folder: Path) -> None:
    """
    When two different chapters reference the same figure file, rename the
    second occurrence to a chapter-specific name. The fallback figure generator
    will then create a distinct figure for it.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    # Collect all figure references: fig_name → list of chapter files
    fig_usage: dict[str, list[Path]] = {}
    for tex_file in sorted(chapters_dir.glob("ch*.tex")):
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
        ):
            if fig_ref == "fig_stub.png":
                continue
            fig_usage.setdefault(fig_ref, []).append(tex_file)

    # For figures used by multiple chapters, rename in all but the first chapter
    for fig_name, users in fig_usage.items():
        if len(users) <= 1:
            continue
        for tex_file in users[1:]:  # Skip the first (canonical) user
            ch_match = re.match(r"(ch\d+)", tex_file.name)
            ch_id = ch_match.group(1) if ch_match else "dup"
            base, ext = fig_name.rsplit(".", 1) if "." in fig_name else (fig_name, "png")
            new_name = f"{base}_{ch_id}.{ext}"
            text = tex_file.read_text(encoding="utf-8", errors="replace")
            new_text = text.replace(f"figures/{fig_name}", f"figures/{new_name}")
            if new_text != text:
                tex_file.write_text(new_text, encoding="utf-8")
                logger.info(f"[Dedup] {tex_file.name}: {fig_name} → {new_name}")
