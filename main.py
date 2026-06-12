"""
main.py
=======
CLI Entry point for NavigatorCrew.
Architecture: LangGraph + CrewAI Sequential Pipeline v5.1.

The run-orchestration implementation lives in src/runner/ (extracted from this
file to satisfy the 150-line-per-file rule). This module is the thin CLI plus
backward-compatible re-exports — src/graph/nodes.py and the test suite import
these names from `main`.

Speed modes (slowest → fastest):
    (default)  Full split pipeline: research → validate → writing, ~60–120 min
    --fast     Skip domain experts: 5 agents, 6 tasks, ~20–40 min
    --smoke    Minimal: 2 agents, 2 tasks (outline + latex-all), ~3–8 min
    --dry-run  Zero LLM calls: write pre-canned stubs, compile PDF, ~5–30 sec
"""

import argparse
import shutil

from src import config as _config
from src.config import PROJECT_ROOT, logger  # noqa: F401  (re-export for tests)
from src.runner import (  # noqa: F401  (re-exports for nodes.py + tests)
    _CHAPTER_FIGURE_STYLE,
    _STAGING_DIR,
    EXPECTED_CHAPTERS,
    _deduplicate_cross_chapter_figures,
    _diversify_stub_figures,
    _generate_fallback_figures,
    _infer_style_from_name,
    _load_run_folder,
    _render_fallback_figure,
    _sanitize_tex_files,
    _save_run_folder,
    _topic_slug,
    compile_pdf,
    create_run_folder,
    finalize_run,
    run_dry_run,
    setup_run_latex,
    validate_and_fix_chapters,
)


def _parse_args() -> argparse.Namespace:
    _DEFAULT_TOPIC = "Bat-Inspired Drone Navigation via Bio-Mimetic Multi-Modal Sensor Fusion"
    parser = argparse.ArgumentParser(description="NavigatorCrew v5.1")
    parser.add_argument("--topic",      default=_DEFAULT_TOPIC)
    parser.add_argument("--resume",     action="store_true",
                        help="Resume from last checkpoint (reuses same run folder)")
    parser.add_argument("--no-pdf",     action="store_true",
                        help="Skip PDF compilation")
    parser.add_argument("--no-archive", action="store_true",
                        help="Delete run folder after completion (smoke tests only)")
    parser.add_argument("--fast", action="store_true",
                        help="Fast mode: skip domain expert agents (6-task pipeline, ~40%% faster)")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke mode: 2-task pipeline (outline + latex-all), ~3–8 min")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry-run: zero LLM calls — write stub chapters and compile PDF only (~5–30 sec)")
    return parser.parse_args()


def _prepare_run_folder(args):
    """Create (or restore) the run folder and seed staging + stub figure."""
    if args.resume:
        run_folder = _load_run_folder()
        if run_folder is None:
            logger.warning("[Resume] No saved run folder — creating new one")
            run_folder = create_run_folder(args.topic)
            setup_run_latex(run_folder, topic=args.topic)
        else:
            logger.info(f"[Resume] Reusing run folder: {run_folder}")
    else:
        run_folder = create_run_folder(args.topic)
        setup_run_latex(run_folder, topic=args.topic)

    _save_run_folder(run_folder)

    # Ensure staging directory exists for .md reports
    (_config.PROJECT_ROOT / _STAGING_DIR).mkdir(parents=True, exist_ok=True)

    # Pre-seed a fallback figure so xelatex never crashes on a missing \includegraphics.
    # The latex agent is instructed to use fig_stub.png if the real figure isn't ready.
    from src.stubs import _stub_png
    _figures_dir = run_folder / "latex" / "figures"
    _figures_dir.mkdir(parents=True, exist_ok=True)
    (_figures_dir / "fig_stub.png").write_bytes(_stub_png())
    return run_folder


def main():
    args = _parse_args()
    logger.info(f"Topic: {args.topic}")
    if args.fast:
        logger.info("Fast mode: domain expert agents DISABLED")
    if args.smoke:
        logger.info("Smoke mode: 2-task pipeline (outline + latex-all)")
    if args.dry_run:
        logger.info("Dry-run mode: zero LLM calls — writing pre-canned stubs")

    run_folder = _prepare_run_folder(args)

    if args.dry_run:
        run_dry_run(args, run_folder)
        return

    # Run LangGraph pipeline (lazy import keeps CLI startup fast and avoids cycles)
    from src.graph.navigator_graph import build_navigator_graph
    from src.graph.state import PipelineState

    # Use split pipeline (research → validate → writing) for full mode;
    # legacy single-crew pipeline for fast/smoke modes.
    use_split = not (args.fast or args.smoke)
    logger.info(f"Building NavigatorCrew LangGraph pipeline (split={use_split})...")
    graph = build_navigator_graph(split_mode=use_split)

    initial_state: PipelineState = {
        "topic":             args.topic,
        "run_folder":        str(run_folder),
        "remediation_count": 0,
        "failed_sections":   [],
        "quality_verdict":   "PENDING",
        "quality_score":     0,
        "fast_mode":         args.fast,
        "smoke_mode":        args.smoke,
        "research_fix_count": 0,
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise

    # Validate & fix chapter filenames, normalize figures, generate fallbacks
    validate_and_fix_chapters(run_folder)
    _diversify_stub_figures(run_folder)
    _deduplicate_cross_chapter_figures(run_folder)
    _generate_fallback_figures(run_folder)

    pdf_path = None
    if not args.no_pdf:
        pdf_path = compile_pdf(run_folder)

    finalize_run(run_folder)

    if args.no_archive:
        shutil.rmtree(run_folder, ignore_errors=True)
        run_folder = None

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
