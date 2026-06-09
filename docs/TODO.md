# NavigatorCrew — TODO

## Done ✅

### Pipeline & Architecture
- [x] 10-agent CrewAI sequential crew, 11-task pipeline
- [x] LangGraph state machine (main pipeline → quality gate → remediation → END)
- [x] Programmatic quality gate with per-chapter thresholds (relaxed for abstract/ch01/ch09)
- [x] `--resume`, `--no-pdf`, `--no-archive` flags
- [x] Run-folder architecture: each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `run_folder` passed through LangGraph state → `build_crew()` → all task descriptions
- [x] `setup_run_latex()`, `compile_pdf()` (5 xelatex passes), `finalize_run()`

### Speed Modes
- [x] `--fast` mode: 5 agents, 6 tasks (skip domain experts), ~20–40 min
- [x] `--smoke` mode: 2 agents, 2 tasks (outline + latex-all), max_iter=35, ~10–20 min
  - `create_task_latex_smoke` + `create_smoke_tasks` in `src/tasks/`
  - `smoke_mode` field in LangGraph `PipelineState` passed through to `build_crew`
- [x] `--dry-run` mode: zero LLM calls (~5–30 sec)
  - `src/stubs.py`: pure-Python chapter/PNG generators, all quality-gate-passing
  - Bypasses LangGraph; calls stubs → quality gate → compile_pdf directly
  - **Proven working**: score 100/100, PDF 0.1 MB, opens correctly

### Agents
- [x] HebrewAcademicWriter (language separation: English research → Hebrew prose)
- [x] LaTeXAuthor — writes Hebrew LaTeX; falls back to prose from research_briefs if hebrew_prose.md missing
- [x] 5 PhD-level domain expert agents: VisionAIExpert, PhysicsExpert, AlgorithmsExpert, AerospaceMarineExpert, BiologyExpert
- [x] DOMAIN SKIP mechanism — experts skip irrelevant topics without padding
- [x] All 10 agents wired in crew.py; all use DeepSeek V3
- [x] max_iter: latex_author=55, hebrew_writer=40, data_visualizer=22

### LaTeX / Compilation
- [x] `main.tex`: all chapter `\input` calls wrapped in `\IfFileExists` — no crash on missing files
- [x] `compile_pdf()`: auto-stubs missing `\includegraphics` files with `fig_stub.png` before xelatex
- [x] `fig_stub.png` pre-seeded into every run folder at startup
- [x] LaTeX task split: Part 1 (abstract+ch01–ch05+bib, 7 files) and Part 2 (ch06–ch09, 4 files)
- [x] Hebrew prose target: 800–1200 words/chapter; ch06/ch08 ≥ 1400 words
- [x] Figure WIDTH rules: `figure*`+`\textwidth` for wide figs; min 11pt font
- [x] Label uniqueness: chapter-prefix convention `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] PROTECTED_FILES: cover.tex, main.tex, config.py only
- [x] `references.bib` overwrite bug fixed (output_file → latex_status.md)
- [x] `figures_manifest.md` overwrite bug fixed (output_file → figures_status.md)
- [x] `\textenglish` hyperref crash fixed via `\texorpdfstring`
- [x] Stale `main.out` crash fixed: build artifacts deleted before every compile
- [x] Math operators in `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] `\usepackage{algorithm}` removed — use lstlisting for pseudocode
- [x] Quality gate: figure existence check with -20 cap; MIN_BIB_ENTRIES=10 (topic-agnostic)
- [x] 5th XeLaTeX pass (resolves rerunfilecheck warnings)
- [x] ch01 and ch04 fully dynamic (agent-written); only cover.tex is static
- [x] VisualizationEngineer `_GOAL` topic-agnostic; figure specs in task description
- [x] LaTeXAuthor `_GOAL`: removed hardcoded bat-drone BibTeX keys; bibliography consistency rule added
- [x] Hardcoded bat-drone figure names removed from `_latex_shared_rules`
- [x] Smoke task description rewritten: reads outline once, writes files immediately

### Tests
- [x] 134 tests across 11 files — all passing
- [x] Covers: agents, tasks, quality gate, config, tools, run archive, latex sources

---

## Active Targets 🎯

- [ ] Smoke run PDF > 0 bytes and openable (compile_pdf stub fix added — pending next run)
- [ ] Full/fast run reaching 25–30 pages
- [ ] LaTeX compilation with zero `!` fatal errors
- [ ] Multiply-defined label warnings eliminated

---

## Backlog

- [ ] ArXiv tool for researcher (real paper citations)
- [ ] Post-run `references.bib` key validator
- [ ] Token budget enforcement (abort if projected cost > threshold)
- [ ] Investigate paper similarity across runs (temperature=0.3 → consider 0.5)
