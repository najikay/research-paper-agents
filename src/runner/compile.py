"""
src/runner/compile.py
=====================
XeLaTeX compilation pipeline. Code moved from main.py (150-line rule), with
two Windows-hardening changes: subprocess output is decoded as UTF-8 (the OS
default codepage, e.g. cp1255 on Hebrew locales, crashes on xelatex output),
and a timeout that returns failure instead of raising an uncaught exception.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from src.config import logger
from src.runner.sanitize import _sanitize_tex_files

# Seconds allowed per xelatex/bibtex pass. Large bilingual documents with many
# figures can exceed 3 minutes on slower machines; 600 s is a safe ceiling.
_PASS_TIMEOUT = 600


def compile_pdf(run_folder: Path) -> Path | None:
    """
    Run XeLaTeX → BibTeX → XeLaTeX × 3 inside run_folder/latex/.
    Returns path to run_folder/paper.pdf, or None on failure.
    """
    latex_dir = run_folder / "latex"
    pdf_src   = latex_dir / "main.pdf"
    pdf_dst   = run_folder / "paper.pdf"

    def run(cmd: list[str]) -> bool:
        """
        Run one compile command in latex_dir with UTF-8 decoding and a timeout.
        Returns True if the command exited 0; logs a warning and returns False
        on a non-zero exit or timeout.
        """
        try:
            result = subprocess.run(
                cmd, cwd=latex_dir,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=_PASS_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"[LaTeX] {cmd[0]} timed out after {_PASS_TIMEOUT}s")
            return False
        if result.returncode != 0:
            logger.warning(f"[LaTeX] {cmd[0]} returned non-zero: {(result.stdout or '')[-500:]}")
        return result.returncode == 0

    # Delete stale build artifacts first.
    _BUILD_EXTS = ("*.aux", "*.out", "*.bbl", "*.blg", "*.toc", "*.fls",
                   "*.fdb_latexmk", "*.synctex.gz", "*.bcf", "*.run.xml")
    for pattern in _BUILD_EXTS:
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

    logger.info("[LaTeX] Compiling PDF (xelatex → bibtex → xelatex × 3)...")
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

        # Log fatal errors from main.log for debugging
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
        logger.error(f"[LaTeX] PDF compilation failed — check {latex_dir}/main.log")
        # Log the actual errors
        log_file = latex_dir / "main.log"
        if log_file.exists():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
            fatal_errors = [line for line in log_text.splitlines() if line.startswith("!")]
            for err in fatal_errors[:10]:
                logger.error(f"  {err}")
        return None
