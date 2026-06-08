# NavigatorCrew — TODO

## Done ✅

### Pipeline
- [x] 5-agent CrewAI sequential crew (Director → Researcher → Visualizer → HebrewWriter → LaTeXAuthor)
- [x] LangGraph state machine (main pipeline → quality gate → remediation → END)
- [x] Programmatic quality gate (replaces infinite-loop LLM reviewer)
- [x] `--resume` flag: task-level checkpointing via `output_file`
- [x] `--no-pdf` flag for content-only runs
- [x] `--no-archive` flag for smoke tests
- [x] Run-folder architecture: each run is self-contained in `outputs/runs/{slug}-{date}/`
  - `run_folder/latex/` — primary LaTeX source; agents write directly here
  - `run_folder/latex/figures/` — agent-generated PNGs
  - `run_folder/outputs/` — agent .md reports (moved from staging on completion)
  - `run_folder/paper.pdf` — compiled PDF
  - `run_folder/run_manifest.txt` — file index with figure listing
  - Project-root `latex/` is a read-only template; never touched during a run
- [x] `run_folder` passed through LangGraph state, crew, and all task descriptions
- [x] `finalize_run()` replaces old `archive_run()` — moves staging .md files, writes manifest
- [x] `setup_run_latex()` copies template into run folder before graph starts
- [x] Stale build artifacts (.aux, .out, .bbl, etc.) deleted before every xelatex compile

### Agents
- [x] HebrewAcademicWriter agent (language separation: English research → Hebrew prose)
- [x] LaTeXAuthor simplified to pure formatter (no translation)
- [x] Researcher forced to search in English (Serper/ArXiv queries)
- [x] All agents use DeepSeek V3

### LaTeX / Compilation
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}` throughout
- [x] `main.tex` restored: ch0X_ naming, cover.tex + abstract.tex included
- [x] PROTECTED_FILES blocks agent writes to cover.tex, main.tex, ch01, ch04, config.py
  - Basename matching added so protection works for both project-root and run-folder paths
- [x] SafeFileWriterTool checks both basename and relative path
- [x] Required 14 BibTeX keys baked into agent prompt and task description
- [x] Em dash prohibition in LaTeXAuthor goal
- [x] Package load order: fontspec → polyglossia → bidi (last)
- [x] `references.bib` overwrite bug fixed: latex task `output_file` → `outputs/current/latex_status.md`; agent instructed to write bib via SafeFileWriterTool
- [x] `\textenglish` hyperref crash fixed: `\newcommand{\en}` uses `\texorpdfstring`
- [x] Stale `main.out` crash fixed: build artifacts deleted before every compile
- [x] Math operators `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr` added to `main.tex` preamble
- [x] Quality gate figure existence check: catches agent inventing nonexistent figure names
- [x] Task description strengthened: agents told to use EXACT paths from figures_manifest.md

### Configuration
- [x] DeepSeek V3 as sole provider (Anthropic removed from .env.example)
- [x] Provider-aware `validate_config()` (only checks DEEPSEEK_API_KEY)
- [x] Agent-generated LaTeX files (ch02–ch09, abstract, figures/) excluded from git

### Tests
- [x] 132 tests across 11 files — all passing
- [x] test_quality_gate: `_make_state` includes `run_folder`
- [x] test_tasks: `create_task_figures` / `create_task_latex` fixtures pass `run_folder`
- [x] test_run_archive: updated to test `finalize_run` (replaces old `archive_run` tests)

### Docs
- [x] README reflects v5.1 architecture, 5-agent crew, run archive layout
- [x] PRD, PLAN, TODO updated to v6.0 (run-folder architecture)

## Next Run Targets 🎯

- [ ] Paper compiles without xelatex errors
- [ ] Paper reaches 25–30 pages
- [ ] Quality gate score ≥ 75
- [ ] references.bib has all 14 required keys
- [ ] All chapter .tex files pass structural checks (≥ 600 words, ≥ 4 subsections, ≥ 3 equations)
- [ ] Push to GitHub

## Backlog

- [ ] ArXiv tool for researcher (real citations)
- [ ] Post-run references.bib key validator (belt-and-suspenders guard)
- [ ] Token budget enforcement (abort if cost projected > threshold)
- [ ] Evaluate adding domain-expert agents (physics prof, CS prof, AI engineering prof)
