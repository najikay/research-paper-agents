"""
src/runner/
===========
Run-orchestration package: run-folder lifecycle, chapter validation, fallback
figures, LaTeX sanitization, PDF compilation, and run finalization.

This package was extracted from the monolithic main.py to satisfy the
150-line-per-file rule. main.py re-exports these names for backward
compatibility (src/graph/nodes.py and the test suite import from `main`).
"""
from src.runner.run_folder import (
    _STAGING_DIR,
    _topic_slug,
    create_run_folder,
    _save_run_folder,
    _load_run_folder,
    setup_run_latex,
)
from src.runner.chapters import (
    EXPECTED_CHAPTERS,
    validate_and_fix_chapters,
    _diversify_stub_figures,
    _deduplicate_cross_chapter_figures,
)
from src.runner.figures import (
    _CHAPTER_FIGURE_STYLE,
    _generate_fallback_figures,
    _infer_style_from_name,
    _render_fallback_figure,
)
from src.runner.sanitize import _sanitize_tex_files
from src.runner.compile import compile_pdf
from src.runner.finalize import finalize_run
from src.runner.dryrun import run_dry_run

__all__ = [
    "_STAGING_DIR", "_topic_slug", "create_run_folder",
    "_save_run_folder", "_load_run_folder", "setup_run_latex",
    "EXPECTED_CHAPTERS", "validate_and_fix_chapters",
    "_diversify_stub_figures", "_deduplicate_cross_chapter_figures",
    "_CHAPTER_FIGURE_STYLE", "_generate_fallback_figures",
    "_infer_style_from_name", "_render_fallback_figure",
    "_sanitize_tex_files", "compile_pdf", "finalize_run", "run_dry_run",
]
