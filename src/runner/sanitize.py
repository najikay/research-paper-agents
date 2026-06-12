"""
src/runner/sanitize.py
======================
Driver for the 25-fix LaTeX sanitizer. The fix implementations live in
sanitize_structure.py (fixes 1-11b), sanitize_content.py (fixes 12a-19),
and sanitize_final.py (fixes 21-23, 20, 12b) — split per the 150-line rule.
Fix application order is identical to the original main.py implementation.
"""
from __future__ import annotations

from pathlib import Path

from src.config import logger
from src.runner.sanitize_content import apply_content_fixes
from src.runner.sanitize_final import apply_final_fixes
from src.runner.sanitize_structure import apply_structure_fixes


def _sanitize_tex_files(chapters_dir: Path) -> None:
    """
    Fix common LaTeX errors that agents introduce, preventing compilation failures.
    """
    figures_dir = chapters_dir.parent / "figures"
    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        original = text

        text = apply_structure_fixes(text, tex_file.name, figures_dir)
        text = apply_content_fixes(text)
        text = apply_final_fixes(text)

        if text != original:
            tex_file.write_text(text, encoding="utf-8")
            logger.info(f"[Sanitize] Fixed LaTeX issues in {tex_file.name}")
