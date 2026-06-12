"""
run_manager.py
==============
Run folder lifecycle: slug generation, creation, save/load state,
LaTeX template setup, and finalization (move staging reports).
"""

import re
import shutil
from datetime import date
from pathlib import Path

from src.config import PROJECT_ROOT, logger

# Temporary staging for agent .md reports during a run.
_STAGING_DIR = "outputs/current"

# File that saves the current run folder path so --resume can find it.
_RUN_STATE_FILE = PROJECT_ROOT / "outputs" / "current_run_folder.txt"


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


def setup_run_latex(run_folder: Path, topic: str = "") -> None:
    """
    Copy the latex template into this run's folder.

    The project-root latex/ contains only the static template files (main.tex,
    cover.tex, IEEEtran.cls/bst, seed references.bib). Agents write all
    generated chapters and figures directly into run_folder/latex/.

    If *topic* is provided, replaces {{TOPIC_ENGLISH}} and {{TOPIC_HEBREW}}
    placeholders in the cover page with the actual topic title.
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
    if topic:
        cover = run_latex / "chapters" / "cover.tex"
        if cover.is_file():
            text = cover.read_text(encoding="utf-8")
            text = text.replace("{{TOPIC_ENGLISH}}", topic)
            hebrew_fallback = r"\en{" + topic + "}"
            text = text.replace("{{TOPIC_HEBREW}}", hebrew_fallback)
            cover.write_text(text, encoding="utf-8")
    logger.info(f"[RunFolder] LaTeX template -> {run_latex}")


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

    figures_dir = run_folder / "latex" / "figures"
    figures = sorted(f.name for f in figures_dir.glob("*.png")) if figures_dir.exists() else []
    has_pdf = (run_folder / "paper.pdf").exists()

    lines = [
        "NavigatorCrew Run Archive",
        "=========================",
        f"Folder : {run_folder.name}",
        "",
        f"LaTeX source: {run_folder}/latex/",
        "  chapters/  <- static + agent-written .tex files",
        f"  figures/   <- {len(figures)} agent-generated PNG(s)",
    ]
    for fig in figures:
        lines.append(f"    {fig}")
    lines += [
        "  references.bib",
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
        f"{len(moved)} outputs -> {run_folder}"
    )
