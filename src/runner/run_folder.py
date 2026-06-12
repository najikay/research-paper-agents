"""
src/runner/run_folder.py
========================
Run-folder lifecycle: slug naming, creation, state persistence, and the
LaTeX template copy. Code moved verbatim from main.py (150-line rule).

PROJECT_ROOT is read dynamically from src.config so tests can monkeypatch it.
"""
from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from src import config
from src.config import logger

# Temporary staging for agent .md reports during a run.
# Moved to run_folder/outputs/ at the end; staging is then deleted.
_STAGING_DIR = "outputs/current"


def _run_state_file() -> Path:
    """File that saves the current run folder path so --resume can find it."""
    return config.PROJECT_ROOT / "outputs" / "current_run_folder.txt"


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
    runs_root = config.PROJECT_ROOT / "outputs" / "runs"
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
    state = _run_state_file()
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(str(run_folder), encoding="utf-8")


def _load_run_folder() -> Path | None:
    state = _run_state_file()
    if state.exists():
        p = Path(state.read_text(encoding="utf-8").strip())
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
    template = config.PROJECT_ROOT / "latex"
    run_latex = run_folder / "latex"
    shutil.copytree(
        template, run_latex,
        ignore=shutil.ignore_patterns(
            "*.aux", "*.log", "*.out", "*.bbl", "*.blg",
            "*.toc", "*.fls", "*.fdb_latexmk", "*.synctex.gz", "*.pdf",
        ),
    )
    # Replace cover page placeholders with the actual topic title.
    if topic:
        cover = run_latex / "chapters" / "cover.tex"
        if cover.is_file():
            text = cover.read_text(encoding="utf-8")
            # English title: use the topic as-is
            text = text.replace("{{TOPIC_ENGLISH}}", topic)
            # Hebrew placeholder: keep the English topic in \en{} if no
            # Hebrew translation is available (agents write the real Hebrew
            # title in ch01_intro.tex's \section{}).
            hebrew_fallback = r"\en{" + topic + "}"
            text = text.replace("{{TOPIC_HEBREW}}", hebrew_fallback)
            cover.write_text(text, encoding="utf-8")
    logger.info(f"[RunFolder] LaTeX template → {run_latex}")
