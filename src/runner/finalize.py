"""
src/runner/finalize.py
======================
End-of-run archiving: move staging .md reports into the run folder and
write the run manifest. Code moved verbatim from main.py (150-line rule).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from src import config
from src.config import logger
from src.runner.run_folder import _STAGING_DIR


def finalize_run(run_folder: Path) -> None:
    """
    Move agent .md reports from staging (outputs/current/) into
    run_folder/outputs/ and clean up staging.
    """
    staging_src = config.PROJECT_ROOT / _STAGING_DIR
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
        "  chapters/  ← static + agent-written .tex files",
        f"  figures/   ← {len(figures)} agent-generated PNG(s)",
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
        f"{len(moved)} outputs → {run_folder}"
    )
