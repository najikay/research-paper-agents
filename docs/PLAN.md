# NavigatorCrew — Implementation Plan (v5.2)

## Architecture Summary

```
main.py  →  LangGraph pipeline  →  CrewAI 10-agent crew (11 tasks)  →  XeLaTeX PDF  →  run archive
```

**CrewAI pipeline** (sequential, 11 tasks):
```
outline → research → [5×domain experts] → figures → hebrew_prose → latex_part1 → latex_part2
```

**LangGraph state machine** wraps CrewAI:
1. `run_main_pipeline` — runs 10-agent CrewAI crew (11 tasks) sequentially
2. `run_quality_gate` — programmatic LaTeX checker (no LLM, no loop risk)
3. `run_remediation` — targeted fix crew (max 2 cycles)
4. `→ END` — PDF compilation (xelatex→bibtex→xelatex×3), then run archive

**Key design principles:**
- **Language separation**: Research in English → HebrewAcademicWriter → LaTeXAuthor (pure formatter)
- **Domain experts**: 5 PhD specialists enrich any chapter in their field; write "DOMAIN SKIP:" otherwise
- **Split LaTeX task**: Part 1 (abstract+ch01/02/03/04/05+bib) and Part 2 (ch06/07/08/09+appendix), each with its own 40-iter budget — prevents agent from being cut off mid-paper
- **Fully dynamic content**: Only `cover.tex` is static; all 9 chapters are agent-written; figures adapt to topic via `paper_outline.md`

---

## Phase 1: Architecture (COMPLETE)

- [x] Sequential CrewAI process (`Process.sequential`)
- [x] DeepSeek V3 primary provider (OpenAI-compatible, ~$0.07/run)
- [x] Task-level checkpointing via `output_file`
- [x] LangGraph state machine with feedback loop (max 2 remediation cycles)
- [x] PDF auto-compilation in `main.py` (xelatex → bibtex → xelatex × 3 = 5 passes)
- [x] CrewAI v1.14.6 `strict=True` bug patched in venv

## Phase 2: Quality & Content (COMPLETE)

- [x] HebrewAcademicWriter agent (language separation principle)
- [x] Programmatic quality gate (replaces looping LLM reviewer)
  - Checks: equation count ≥3, figure count ≥1, subsection count ≥3, word estimate ≥600
  - Checks: `references.bib` entry count ≥10 (topic-agnostic), no placeholders, no em dashes, no `\begin{center}`
  - Missing figure penalty capped at -20 total (prevents single-component cascade failure)
- [x] PROTECTED_FILES system (basename + relative path matching)
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] Em dash prohibition in LaTeXAuthor tasks
- [x] 25–30 page target in all task descriptions
- [x] Token budget documented in `docs/BUDGET.md`

## Phase 3: Run-Folder Architecture (COMPLETE)

- [x] Each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `run_folder` passed through LangGraph state → `build_crew()` → all task descriptions
- [x] `PythonCodeExecutorTool(figures_dir=run_folder/latex/figures/)` — figures saved to run folder
- [x] `setup_run_latex(run_folder)` — copies template before pipeline
- [x] `compile_pdf(run_folder)` — compiles in run folder, deletes stale build artifacts
- [x] `finalize_run(run_folder)` — moves staging .md files, writes manifest with figure listing
- [x] `outputs/runs/` excluded from git

## Phase 4: Bug Fixes (COMPLETE)

- [x] `references.bib` overwrite fixed — latex task `output_file` → `latex_status.md`; agent writes bib via SafeFileWriterTool
- [x] `\textenglish` hyperref crash fixed — `\newcommand{\en}` uses `\texorpdfstring`
- [x] Stale `main.out` crash fixed — build artifacts deleted before every xelatex run
- [x] `FileReaderTool` leading-slash fix
- [x] Math operators added to `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] Figure existence check in quality gate
- [x] Remediation researcher missing FileReaderTool fixed (was causing Repaired JSON spam)
- [x] Quality gate static file exclusion — only `cover.tex` excluded from em dash / center checks
- [x] `\usepackage{algorithm}` removed from `main.tex` — use `lstlisting` for pseudocode
- [x] 5th XeLaTeX pass added — resolves `rerunfilecheck` cross-reference warnings

## Phase 5: Domain Expert Agents (COMPLETE)

- [x] 5 new PhD-level domain expert agents added:
  - `VisionAIExpert` (Dr. Yael Ben-Cohen) — visual SLAM, depth estimation, ViT, edge inference
  - `PhysicsExpert` (Dr. Aaron Levi) — matched filter, LFM sonar, Doppler, beamforming
  - `AlgorithmsExpert` (Dr. Miriam Shapiro) — EKF/UKF/particle filters, factor graph SLAM, CRLB
  - `AerospaceMarineExpert` (Dr. Ethan Ben-David) — UAV dynamics, INS, AUV/submarine sonar, DVL
  - `BiologyExpert` (Dr. Noa Tal) — bat CF-FM sonar, acoustic fovea, DSC, hippocampal maps
- [x] DOMAIN SKIP mechanism — experts write "DOMAIN SKIP: [reason]" if topic irrelevant
- [x] All 10 agents wired with correct tool sets in crew.py
- [x] `create_task_domain_expert()` factory for all 5 experts
- [x] HebrewAcademicWriter and LaTeXAuthor updated to read and integrate all domain files

## Phase 6: Page Count & Quality Fixes (COMPLETE)

- [x] Hebrew prose target raised: 150–250 words/chapter → 800–1200 words/chapter
- [x] LaTeX task minimums raised: 600 → 1000 words, 2 → 4 equations, 3 → 5 subsections
- [x] ch06/ch08 floor raised to 1400 words (algorithm + results are longest chapters)
- [x] LaTeX task split into Part 1 and Part 2:
  - Part 1: abstract + ch01 + ch02 + ch03 + ch04 + ch05 + references.bib (7 files)
  - Part 2: ch06 + ch07 + ch08 + ch09 + appendix (symbols table) (4 files)
  - Each task has max_iter=40 independently — no longer cut off mid-paper
- [x] PLAN step added to each latex task — agent outlines before writing
- [x] "WRITE EACH FILE IMMEDIATELY" rule added — prevents output buffering
- [x] `latex_author` max_iter: 25 → 40; `hebrew_writer` max_iter: 20 → 35
- [x] `data_visualizer` max_iter: 12 → 22 (9 figures + manifest requires ≥12 tool calls)
- [x] Figure size rules: wide figures use `figure*` + `\textwidth`; min 11pt font
- [x] Label uniqueness enforced: chapter-prefixed `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose
- [x] Appendix (symbols+variables table) added to ch09 — organic page count boost

## Phase 7: Fully Dynamic Architecture (COMPLETE)

- [x] `ch01_intro.tex` and `ch04_slam.tex` are now fully agent-written (dynamic)
  - Deleted from `latex/chapters/` template — `cover.tex` is now the only static file
  - Added to Part-1 FILES TO WRITE in `create_task_latex_part1` (7 files total)
  - Added to `AGENT_CHAPTERS` in quality gate (10 chapters total: abstract + ch01–ch09)
  - Removed from `PROTECTED_FILES` and `_STATIC` exclusion set in quality gate
- [x] `VisualizationEngineer._GOAL` made topic-agnostic — figure specs moved to task description
- [x] `create_task_figures` reads `paper_outline.md` first — generates topic-appropriate figures
- [x] `create_task_hebrew_prose` covers CH01–CH09 (was CH02–CH09)
- [x] `references.bib` citation requirement: hardcoded 14 keys → "≥14 topic-relevant entries"
- [x] 134 tests passing across 11 test files

## Phase 8: Three-Speed Pipeline (COMPLETE)

- [x] `--fast` mode: 5 agents, 6 tasks (skip domain experts), ~20–40 min
  - `fast_mode` state field passed through LangGraph → `build_crew`
- [x] `--smoke` mode: 2 agents, 2 tasks (outline + latex-all), ~3–8 min
  - `create_task_latex_smoke` + `create_smoke_tasks` added to `src/tasks/`
  - `author.max_iter = 55` in smoke mode to write all 11 files in one pass
  - `smoke_mode` added to `PipelineState` and passed to `build_crew`
- [x] `--dry-run` mode: zero LLM calls (~5–30 sec)
  - `src/stubs.py`: generates quality-gate-passing chapter stubs + 1×1 PNG + BibTeX
  - Bypasses LangGraph entirely — calls `write_stub_chapters` → `run_quality_gate` → `compile_pdf`
  - Used to verify PDF compilation pipeline independently of LLM correctness
- [x] All 134 tests pass after three-speed implementation

## Phase 9: Pending

- [ ] Full run reaching 25–30 pages in PDF (trial run with new 7-file Part-1 pending)
- [ ] All chapters pass quality gate (score ≥ 75) without issues logged
- [ ] No LaTeX compilation errors (xelatex exits 0)
- [ ] Multiply-defined label warnings eliminated at runtime

## Backlog

- [ ] ArXiv search for real citations in researcher
- [ ] Post-run `references.bib` key validator
- [ ] Token-budget enforcement: abort if projected cost exceeds threshold
- [ ] Investigate paper similarity across runs (temperature currently 0.3)
