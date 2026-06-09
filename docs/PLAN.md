# NavigatorCrew — Implementation Plan (v5.5)

## Architecture Summary

```
main.py  →  LangGraph pipeline  →  CrewAI crew (2/5/10 agents by mode)  →  XeLaTeX PDF  →  run archive
```

**Full pipeline** (sequential, 11 tasks):
```
outline → research → [5×domain experts] → figures → hebrew_prose → latex_part1 → latex_part2
```

**LangGraph state machine** wraps CrewAI:
1. `run_main_pipeline` — runs CrewAI crew (mode-dependent agent/task count)
2. `run_quality_gate` — programmatic LaTeX checker (no LLM, no loop risk)
3. `run_remediation` — targeted fix crew (max 2 cycles)
4. `→ END` — PDF compilation (xelatex→bibtex→xelatex×3 = 5 passes), then run archive

**Key design principles:**
- **Resilient compilation**: `\IfFileExists` guards in `main.tex`; missing figures auto-stubbed before xelatex
- **Resilient content**: LaTeXAuthor falls back to writing Hebrew prose from research_briefs if hebrew_prose.md is missing
- **Topic-agnostic**: All agents derive content from the dynamic outline; no hardcoded topic references
- **Domain experts**: 5 PhD specialists enrich any chapter in their field; write "DOMAIN SKIP:" otherwise
- **Fully dynamic content**: Only `cover.tex` is static; all 10 content files are agent-written

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
  - Per-chapter thresholds with relaxed values for abstract/ch01/ch09
  - `references.bib` entry count ≥10 (topic-agnostic)
  - Missing figure penalty capped at -20 total
- [x] PROTECTED_FILES system (basename + relative path matching)
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] Em dash prohibition in all tasks
- [x] 25–30 page target in all task descriptions

## Phase 3: Run-Folder Architecture (COMPLETE)

- [x] Each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `run_folder` passed through LangGraph state → `build_crew()` → all task descriptions
- [x] `PythonCodeExecutorTool(figures_dir=run_folder/latex/figures/)` — figures saved to run folder
- [x] `setup_run_latex(run_folder)` — copies template before pipeline
- [x] `compile_pdf(run_folder)` — compiles in run folder, deletes stale build artifacts
- [x] `finalize_run(run_folder)` — moves staging .md files, writes manifest

## Phase 4: Bug Fixes (COMPLETE)

- [x] `references.bib` overwrite fixed — latex task `output_file` → `latex_status.md`
- [x] `\textenglish` hyperref crash fixed — `\newcommand{\en}` uses `\texorpdfstring`
- [x] Stale `main.out` crash fixed — build artifacts deleted before every xelatex run
- [x] `FileReaderTool` leading-slash fix
- [x] Math operators added to `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] `\usepackage{algorithm}` removed from `main.tex` — use `lstlisting` for pseudocode
- [x] 5th XeLaTeX pass added — resolves `rerunfilecheck` cross-reference warnings

## Phase 5: Domain Expert Agents (COMPLETE)

- [x] 5 PhD-level domain expert agents: VisionAIExpert, PhysicsExpert, AlgorithmsExpert, AerospaceMarineExpert, BiologyExpert
- [x] DOMAIN SKIP mechanism — experts write "DOMAIN SKIP: [reason]" if topic irrelevant
- [x] `create_task_domain_expert()` factory for all 5 experts
- [x] HebrewAcademicWriter reads and integrates all domain files

## Phase 6: Page Count & Quality Fixes (COMPLETE)

- [x] Hebrew prose target: 800–1200 words/chapter; ch06/ch08 ≥ 1400 words
- [x] LaTeX task split into Part 1 (abstract+ch01–ch05+bib) and Part 2 (ch06–ch09)
- [x] `latex_author` max_iter: 25 → 55; `hebrew_writer` max_iter: 20 → 40
- [x] `data_visualizer` max_iter: 12 → 22
- [x] Figure size rules: wide figures use `figure*` + `\textwidth`; min 11pt font
- [x] Label uniqueness enforced: chapter-prefixed `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose

## Phase 7: Fully Dynamic Architecture (COMPLETE)

- [x] `ch01_intro.tex` and `ch04_slam.tex` are now fully agent-written (dynamic)
- [x] `cover.tex` is the only static chapter file
- [x] `VisualizationEngineer._GOAL` made topic-agnostic — figure specs from task description
- [x] `create_task_figures` reads `paper_outline.md` first; filenames are topic-appropriate
- [x] `references.bib` citation requirement: hardcoded keys → "≥14 topic-relevant entries"
- [x] 134 tests passing across 11 test files

## Phase 8: Three-Speed Pipeline (COMPLETE)

- [x] `--fast` mode: 5 agents, 6 tasks (skip domain experts), ~20–40 min
- [x] `--smoke` mode: 2 agents, 2 tasks (outline + latex-all), max_iter=35, ~10–20 min
- [x] `--dry-run` mode: zero LLM calls (~5–30 sec)
  - `src/stubs.py`: pure-Python chapter/PNG generators, all quality-gate-passing
  - Bypasses LangGraph entirely; proved PDF compilation pipeline works end-to-end

## Phase 9: Compilation Reliability (COMPLETE)

- [x] `main.tex`: all chapter `\input` calls wrapped in `\IfFileExists` — xelatex never crashes on a missing file
- [x] `compile_pdf()`: auto-stubs any missing `\includegraphics` file with `fig_stub.png` before xelatex runs
- [x] `fig_stub.png` pre-seeded into every run folder at startup — latex agent always has a valid fallback
- [x] `figures_manifest.md` output_file bug fixed: `output_file` → `figures_status.md` to prevent CrewAI from overwriting the manifest content
- [x] LaTeXAuthor `_GOAL`: removed stale hardcoded BibTeX keys; removed stale PROTECTED comments about ch01/ch04
- [x] LaTeXAuthor falls back to writing Hebrew prose from research_briefs if hebrew_prose.md is missing
- [x] Smoke task description rewritten to be minimal and write files immediately without reading non-existent files
- [x] Smoke run quality gate PASSED (76/100) — first successful quality gate pass with real agent content

## Phase 10: Pending

- [ ] Smoke run PDF > 0 bytes and openable (missing-figure stub fix in compile_pdf pending verification)
- [ ] Full/fast run reaching 25–30 pages
- [ ] LaTeX compilation with zero `!` fatal errors (only warnings acceptable)
- [ ] Multiply-defined label warnings eliminated

## Backlog

- [ ] ArXiv search for real citations in researcher
- [ ] Post-run `references.bib` key validator
- [ ] Token-budget enforcement: abort if projected cost exceeds threshold
- [ ] Investigate paper similarity across runs (temperature currently 0.3)
