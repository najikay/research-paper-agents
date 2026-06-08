"""
main.py
=======
CLI Entry point for NavigatorCrew.
Architecture: LangGraph + CrewAI Sequential Pipeline v5.1.

Run-folder layout (everything for one run lives here):
    outputs/runs/{topic-slug}-{YYYY-MM-DD}/
        latex/          ← LaTeX workspace: template + agent-written chapters/figures
            chapters/   ← static protected .tex + agent-written .tex
            figures/    ← agent-generated PNGs
            references.bib
            main.tex, IEEEtran.cls/bst
        outputs/        ← agent .md reports (moved from staging on completion)
        paper.pdf       ← compiled PDF (copied here from latex/main.pdf)
        run_manifest.txt

The project-root latex/ directory is a READ-ONLY TEMPLATE — nothing writes to it
during a run. Agents write exclusively to {run_folder}/latex/.
"""

import argparse
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from src.config import logger, PROJECT_ROOT

# Temporary staging for agent .md reports during a run.
# Moved to run_folder/outputs/ at the end; staging is then deleted.
_STAGING_DIR = "outputs/current"

# File that saves the current run folder path so --resume can find it.
_RUN_STATE_FILE = PROJECT_ROOT / "outputs" / "current_run_folder.txt"


# ---------------------------------------------------------------------------
# Slug / run-folder helpers
# ---------------------------------------------------------------------------

def _topic_slug(topic: str) -> str:
    """Convert topic string to a safe directory slug (max 40 chars)."""
    slug = topic.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:40].rstrip("-")


def create_run_folder(topic: str) -> Path:
    """
    Create a uniquely-named run folder under outputs/runs/.

    Naming convention:
        outputs/runs/{topic-slug}-{YYYY-MM-DD}/
        outputs/runs/{topic-slug}-{YYYY-MM-DD}-v2/   (if date already exists)
    """
    runs_root = PROJECT_ROOT / "outputs" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    today     = date.today().strftime("%Y-%m-%d")
    slug      = _topic_slug(topic)
    base      = f"{slug}-{today}"
    candidate = runs_root / base
    version   = 2
    while candidate.exists():
        candidate = runs_root / f"{base}-v{version}"
        version  += 1

    candidate.mkdir(parents=True)
    logger.info(f"[RunFolder] Created: {candidate}")
    return candidate


def _save_run_folder(run_folder: Path) -> None:
    _RUN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _RUN_STATE_FILE.write_text(str(run_folder), encoding="utf-8")


def _load_run_folder() -> Path | None:
    if _RUN_STATE_FILE.exists():
        p = Path(_RUN_STATE_FILE.read_text(encoding="utf-8").strip())
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# LaTeX template → run folder
# ---------------------------------------------------------------------------

def setup_run_latex(run_folder: Path) -> None:
    """
    Copy the latex template into this run's folder.

    The project-root latex/ contains only static/protected files (main.tex,
    cover.tex, ch01_intro.tex, ch04_slam.tex, IEEEtran.cls/bst, seed
    references.bib). Agents then write their generated chapters and figures
    directly into run_folder/latex/.
    """
    template = PROJECT_ROOT / "latex"
    run_latex = run_folder / "latex"
    shutil.copytree(
        template, run_latex,
        ignore=shutil.ignore_patterns(
            "*.aux", "*.log", "*.out", "*.bbl", "*.blg",
            "*.toc", "*.fls", "*.fdb_latexmk", "*.synctex.gz", "*.pdf",
        ),
    )
    logger.info(f"[RunFolder] LaTeX template → {run_latex}")


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def compile_pdf(run_folder: Path) -> Path | None:
    """
    Run XeLaTeX → BibTeX → XeLaTeX → XeLaTeX inside run_folder/latex/.
    Returns path to run_folder/paper.pdf, or None on failure.
    """
    latex_dir = run_folder / "latex"
    pdf_src   = latex_dir / "main.pdf"
    pdf_dst   = run_folder / "paper.pdf"

    def run(cmd: list[str]) -> bool:
        result = subprocess.run(
            cmd, cwd=latex_dir,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.warning(f"[LaTeX] {cmd[0]} returned non-zero: {result.stdout[-500:]}")
        return result.returncode == 0

    # Delete stale build artifacts first.
    # main.out from a previous failed run contains truncated bookmark data that
    # causes xelatex to crash at \begin{document} ("! File ended while scanning
    # use of \@@BOOKMARK"), producing an unreadable PDF.
    _BUILD_EXTS = ("*.aux", "*.out", "*.bbl", "*.blg", "*.toc", "*.fls",
                   "*.fdb_latexmk", "*.synctex.gz", "*.bcf", "*.run.xml")
    for pattern in _BUILD_EXTS:
        for f in latex_dir.glob(pattern):
            f.unlink(missing_ok=True)

    logger.info("[LaTeX] Compiling PDF (xelatex → bibtex → xelatex × 2)...")
    run(["xelatex", "-interaction=nonstopmode", "main.tex"])
    run(["bibtex", "main"])
    run(["xelatex", "-interaction=nonstopmode", "main.tex"])
    run(["xelatex", "-interaction=nonstopmode", "main.tex"])

    if pdf_src.exists():
        shutil.copy2(pdf_src, pdf_dst)
        size_mb = pdf_src.stat().st_size / 1_048_576
        logger.success(f"[LaTeX] PDF compiled: {pdf_dst} ({size_mb:.1f} MB)")
        return pdf_dst
    else:
        logger.error(f"[LaTeX] PDF compilation failed — check {latex_dir}/main.log")
        return None


# ---------------------------------------------------------------------------
# Finalize run (move staging .md files into the run folder)
# ---------------------------------------------------------------------------

def finalize_run(run_folder: Path) -> None:
    """
    Move agent .md reports from staging (outputs/current/) into
    run_folder/outputs/ and clean up staging.
    """
    staging_src = PROJECT_ROOT / _STAGING_DIR
    run_outputs = run_folder / "outputs"
    run_outputs.mkdir(exist_ok=True)

    moved = []
    if staging_src.exists():
        for f in sorted(staging_src.glob("*.md")):
            shutil.move(str(f), run_outputs / f.name)
            moved.append(f.name)
        shutil.rmtree(staging_src, ignore_errors=True)

    # Write manifest
    figures_dir = run_folder / "latex" / "figures"
    figures = sorted(f.name for f in figures_dir.glob("*.png")) if figures_dir.exists() else []
    has_pdf = (run_folder / "paper.pdf").exists()

    lines = [
        "NavigatorCrew Run Archive",
        "=========================",
        f"Folder : {run_folder.name}",
        "",
        f"LaTeX source: {run_folder}/latex/",
        f"  chapters/  ← static + agent-written .tex files",
        f"  figures/   ← {len(figures)} agent-generated PNG(s)",
    ]
    for fig in figures:
        lines.append(f"    {fig}")
    lines += [
        f"  references.bib",
        "",
        f"Agent outputs ({len(moved)} files): {run_folder}/outputs/",
    ]
    for f in moved:
        lines.append(f"  {f}")
    lines += [
        "",
        f"PDF: {'paper.pdf' if has_pdf else 'NOT COMPILED (check latex/main.log)'}",
    ]
    (run_folder / "run_manifest.txt").write_text("\n".join(lines), encoding="utf-8")

    logger.info(
        f"[RunFolder] Finalized: {len(figures)} figures + "
        f"{len(moved)} outputs → {run_folder}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _DEFAULT_TOPIC = "Bat-Inspired Drone Navigation via Bio-Mimetic Multi-Modal Sensor Fusion"

    parser = argparse.ArgumentParser(description="NavigatorCrew v5.1")
    parser.add_argument("--topic",      default=_DEFAULT_TOPIC)
    parser.add_argument("--resume",     action="store_true",
                        help="Resume from last checkpoint (reuses same run folder)")
    parser.add_argument("--no-pdf",     action="store_true",
                        help="Skip PDF compilation")
    parser.add_argument("--no-archive", action="store_true",
                        help="Delete run folder after completion (smoke tests only)")
    args = parser.parse_args()

    logger.info(f"Topic: {args.topic}")

    # ------------------------------------------------------------------
    # Create (or restore) run folder BEFORE graph runs
    # ------------------------------------------------------------------
    if args.resume:
        run_folder = _load_run_folder()
        if run_folder is None:
            logger.warning("[Resume] No saved run folder — creating new one")
            run_folder = create_run_folder(args.topic)
            setup_run_latex(run_folder)
        else:
            logger.info(f"[Resume] Reusing run folder: {run_folder}")
    else:
        run_folder = create_run_folder(args.topic)
        setup_run_latex(run_folder)

    _save_run_folder(run_folder)

    # Ensure staging directory exists for .md reports
    (PROJECT_ROOT / _STAGING_DIR).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Run LangGraph pipeline
    # ------------------------------------------------------------------
    from src.graph.navigator_graph import build_navigator_graph
    from src.graph.state import PipelineState

    logger.info("Building NavigatorCrew LangGraph pipeline...")
    graph = build_navigator_graph()

    initial_state: PipelineState = {
        "topic":             args.topic,
        "run_folder":        str(run_folder),
        "remediation_count": 0,
        "failed_sections":   [],
        "quality_verdict":   "PENDING",
        "quality_score":     0,
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise

    # ------------------------------------------------------------------
    # PDF Compilation (from run_folder/latex/)
    # ------------------------------------------------------------------
    pdf_path = None
    if not args.no_pdf:
        pdf_path = compile_pdf(run_folder)

    # ------------------------------------------------------------------
    # Finalize: move staging .md files into the run folder
    # ------------------------------------------------------------------
    finalize_run(run_folder)

    if args.no_archive:
        shutil.rmtree(run_folder, ignore_errors=True)
        run_folder = None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  NAVIGATORCREW — EXECUTION COMPLETE")
    print("=" * 52)
    print(f"  Quality Score    : {final_state['quality_score']}/100")
    print(f"  Verdict          : {final_state['quality_verdict']}")
    print(f"  Remediation Runs : {final_state['remediation_count']}")
    if pdf_path:
        print(f"  PDF              : {pdf_path}")
    if run_folder:
        print(f"  Run Folder       : {run_folder}")
    print("=" * 52)


if __name__ == "__main__":
    main()
