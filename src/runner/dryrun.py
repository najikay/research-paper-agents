"""
src/runner/dryrun.py
====================
--dry-run handler: write pre-canned stub chapters, run the quality gate, and
compile — zero LLM calls. Code moved verbatim from main.py's main() dry-run
branch (150-line rule).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from src.config import logger
from src.runner.compile import compile_pdf
from src.runner.finalize import finalize_run


def run_dry_run(args, run_folder: Path) -> None:
    """Execute the full dry-run flow and print the summary banner."""
    from src.graph.nodes import run_quality_gate
    from src.graph.state import PipelineState
    from src.stubs import write_stub_chapters

    write_stub_chapters(run_folder, args.topic)

    _stub_state: PipelineState = {
        "topic":             args.topic,
        "run_folder":        str(run_folder),
        "remediation_count": 0,
        "failed_sections":   [],
        "quality_verdict":   "PENDING",
        "quality_score":     0,
        "fast_mode":         False,
        "smoke_mode":        False,
    }
    gate_result = run_quality_gate(_stub_state)
    final_state = {**_stub_state, **gate_result}
    logger.info(f"[DryRun] Quality gate: score={final_state['quality_score']} verdict={final_state['quality_verdict']}")

    pdf_path = None
    if not args.no_pdf:
        pdf_path = compile_pdf(run_folder)

    finalize_run(run_folder)
    if args.no_archive:
        shutil.rmtree(run_folder, ignore_errors=True)
        run_folder = None

    print("\n" + "=" * 52)
    print("  NAVIGATORCREW — DRY-RUN COMPLETE")
    print("=" * 52)
    print(f"  Quality Score    : {final_state['quality_score']}/100")
    print(f"  Verdict          : {final_state['quality_verdict']}")
    if pdf_path:
        print(f"  PDF              : {pdf_path}")
    if run_folder:
        print(f"  Run Folder       : {run_folder}")
    print("=" * 52)
