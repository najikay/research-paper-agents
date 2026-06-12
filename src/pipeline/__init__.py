"""
src/pipeline — Extracted pipeline modules from main.py.

Submodules:
    run_manager         — slug helpers, create/save/load run folder, setup_run_latex, finalize_run
    latex_compiler      — compile_pdf, EXPECTED_CHAPTERS, validate_and_fix_chapters
    figures             — stub diversification, cross-chapter dedup, fallback generation
    figure_renderer     — _render_fallback_figure (matplotlib-based fallback figures)
    sanitizer           — _sanitize_tex_files main function
    sanitizer_math      — bare math symbol wrapping helpers
    sanitizer_figures   — PNG dimension reading and wide figure upgrade
"""
