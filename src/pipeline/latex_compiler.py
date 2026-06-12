"""
latex_compiler.py
=================
PDF compilation (XeLaTeX + BibTeX) and chapter validation/rescue.

Handles:
  - EXPECTED_CHAPTERS list (matching main.tex \\input{} calls)
  - validate_and_fix_chapters: rename wrongly-named agent chapter files
  - compile_pdf: full XeLaTeX -> BibTeX -> XeLaTeX x3 pipeline
"""

import re
import shutil
import subprocess
from pathlib import Path

from src.config import logger
from src.pipeline.sanitizer import _sanitize_tex_files

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
            continue

        prefix = expected.split("_")[0]
        if prefix == "abstract":
            continue

        candidates = []
        for f in chapters_dir.glob(f"{prefix}_*.tex"):
            if f.name not in EXPECTED_CHAPTERS and f.name not in protected:
                candidates.append(f)

        if not candidates:
            continue

        best = max(candidates, key=lambda f: f.stat().st_size)
        target = chapters_dir / expected
        best.rename(target)
        logger.info(f"[Validate] Renamed {best.name} -> {expected} (rescued wrong filename)")

    final_files = {f.name for f in chapters_dir.glob("*.tex")}
    extras = final_files - set(EXPECTED_CHAPTERS) - protected
    if extras:
        logger.warning(f"[Validate] Extra chapter files (not in main.tex, ignored): {extras}")


def compile_pdf(run_folder: Path) -> Path | None:
    """
    Run XeLaTeX -> BibTeX -> XeLaTeX x 3 inside run_folder/latex/.
    Returns path to run_folder/paper.pdf, or None on failure.
    """
    latex_dir = run_folder / "latex"
    pdf_src   = latex_dir / "main.pdf"
    pdf_dst   = run_folder / "paper.pdf"

    def run(cmd: list[str]) -> bool:
        """Execute a LaTeX compiler command and return True on success."""
        result = subprocess.run(
            cmd, cwd=latex_dir,
            capture_output=True, text=True,
            timeout=180,
        )
        if result.returncode != 0:
            logger.warning(f"[LaTeX] {cmd[0]} returned non-zero: {result.stdout[-500:]}")
        return result.returncode == 0

    # Delete stale build artifacts first.
    build_exts = ("*.aux", "*.out", "*.bbl", "*.blg", "*.toc", "*.fls",
                  "*.fdb_latexmk", "*.synctex.gz", "*.bcf", "*.run.xml")
    for pattern in build_exts:
        for f in latex_dir.glob(pattern):
            f.unlink(missing_ok=True)

    # Sanitize chapter .tex files to fix common agent-introduced errors
    chapters_dir = latex_dir / "chapters"
    if chapters_dir.exists():
        _sanitize_tex_files(chapters_dir)

    # Stub out any missing figure files so xelatex never crashes on \includegraphics.
    figures_dir = latex_dir / "figures"
    stub_png = figures_dir / "fig_stub.png"
    if stub_png.exists():
        for tex_file in chapters_dir.glob("*.tex"):
            text = tex_file.read_text(encoding="utf-8", errors="replace")
            for fig_ref in re.findall(
                r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
            ):
                fig_path = figures_dir / fig_ref
                if not fig_path.exists():
                    shutil.copy2(stub_png, fig_path)
                    logger.debug(f"[LaTeX] Stubbed missing figure: {fig_ref}")

    logger.info("[LaTeX] Compiling PDF (xelatex -> bibtex -> xelatex x 3)...")
    _xe = ["xelatex", "-interaction=nonstopmode", "main.tex"]
    run(_xe)
    run(["bibtex", "main"])
    run(_xe)
    run(_xe)
    run(_xe)

    if pdf_src.exists() and pdf_src.stat().st_size > 1000:
        shutil.copy2(pdf_src, pdf_dst)
        size_mb = pdf_src.stat().st_size / 1_048_576
        logger.success(f"[LaTeX] PDF compiled: {pdf_dst} ({size_mb:.1f} MB)")

        log_file = latex_dir / "main.log"
        if log_file.exists():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
            fatal_errors = [line for line in log_text.splitlines() if line.startswith("!")]
            if fatal_errors:
                logger.warning(f"[LaTeX] {len(fatal_errors)} fatal error(s) in main.log (PDF may be incomplete):")
                for err in fatal_errors[:5]:
                    logger.warning(f"  {err}")

        return pdf_dst
    else:
        logger.error(f"[LaTeX] PDF compilation failed -- check {latex_dir}/main.log")
        log_file = latex_dir / "main.log"
        if log_file.exists():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
            fatal_errors = [line for line in log_text.splitlines() if line.startswith("!")]
            for err in fatal_errors[:10]:
                logger.error(f"  {err}")
        return None
