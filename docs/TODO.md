# NavigatorCrew — TODO

## Done ✅

### Pipeline & Architecture
- [x] 10-agent CrewAI sequential crew, 11-task pipeline
- [x] LangGraph state machine (main pipeline → quality gate → remediation → END)
- [x] Programmatic quality gate (replaces infinite-loop LLM reviewer)
- [x] `--resume` flag: task-level checkpointing via `output_file`
- [x] `--no-pdf`, `--no-archive` flags
- [x] Run-folder architecture: each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `run_folder` passed through LangGraph state → `build_crew()` → all task descriptions
- [x] `setup_run_latex()`, `compile_pdf()` (5 xelatex passes), `finalize_run()`

### Agents
- [x] HebrewAcademicWriter (language separation: English research → Hebrew prose)
- [x] LaTeXAuthor as pure formatter (no translation)
- [x] 5 PhD-level domain expert agents:
  - VisionAIExpert, PhysicsExpert, AlgorithmsExpert, AerospaceMarineExpert, BiologyExpert
- [x] DOMAIN SKIP mechanism — experts skip irrelevant topics without padding
- [x] All 10 agents wired with full tool sets in crew.py v5.2
- [x] All agents use DeepSeek V3

### LaTeX / Compilation
- [x] LaTeX task split into Part 1 (abstract+ch01/02/03/04/05+bib) and Part 2 (ch06/07/08/09+appendix)
- [x] `latex_author` max_iter 25→40; `hebrew_writer` max_iter 20→35
- [x] PLAN step in each latex task (agent outlines before writing)
- [x] "WRITE EACH FILE IMMEDIATELY" instruction prevents output buffering
- [x] Hebrew prose target: 800–1200 words/chapter; ch06/ch08 ≥ 1400 words
- [x] LaTeX minimums: 1000 words, 5 subsections, 4 equations per chapter
- [x] Figure WIDTH rules: `figure*`+`\textwidth` for wide figs; min 11pt font
- [x] Label uniqueness: chapter-prefix convention `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose
- [x] Appendix (symbols+variables table) in ch09 — organic page count addition
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] PROTECTED_FILES: cover, main, config.py only (ch01/ch04 removed — now dynamic)
- [x] `references.bib` overwrite bug fixed
- [x] `\textenglish` hyperref crash fixed via `\texorpdfstring`
- [x] Stale `main.out` crash fixed: build artifacts deleted before every compile
- [x] Math operators in `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] `\usepackage{algorithm}` removed from main.tex — use lstlisting for pseudocode
- [x] Quality gate: figure existence check (catches hallucinated filenames)
- [x] Quality gate: `REQUIRED_CITE_KEYS` → `MIN_BIB_ENTRIES=10` (topic-agnostic count)
- [x] Missing figure penalty capped at -20 (prevents cascading single-component failure)
- [x] 5th XeLaTeX pass added (resolves rerunfilecheck warnings)
- [x] ch01_intro.tex and ch04_slam.tex are now fully dynamic (agent-written)
  - Deleted from `latex/chapters/` template
  - Added to Part-1 FILES TO WRITE in create_task_latex_part1
  - Added to AGENT_CHAPTERS in quality gate (10 chapters total)
  - Removed from PROTECTED_FILES and _STATIC exclusion set
- [x] VisualizationEngineer `_GOAL` made topic-agnostic: figure specs moved to task description
- [x] create_task_figures: reads paper_outline.md first; generates topic-appropriate figures

### Quality Gate Thresholds
- [x] Equations ≥ 3 per chapter (raised from 2)
- [x] Word count ≥ 600 per chapter (raised from 300)
- [x] Subsections ≥ 3, figures ≥ 1, citations ≥ 2

### Fixes
- [x] Remediation researcher missing FileReaderTool (Repaired JSON spam loop)
- [x] PythonCodeExecutorTool figures_dir: now writes to `{run_folder}/latex/figures/`
- [x] FileReaderTool leading-slash path fix
- [x] Duplicate latex/ folder eliminated — run folder is single source of truth

### Tests
- [x] 134 tests across 11 files — all passing
- [x] test_tasks: updated for 11-task pipeline, part1/part2 fixtures, dynamic ch01/ch04
- [x] test_quality_gate: updated thresholds (≥3 equations, ≥600 words, MIN_BIB_ENTRIES)
- [x] test_latex_sources: REQUIRED_CITE_KEYS → count check; ch01/ch04 no longer static
- [x] test_config: ch01/ch04 must NOT be in PROTECTED_FILES
- [x] test_run_archive: updated to test `finalize_run`
- [x] test_tools_code_executor: fixed to use `PythonCodeExecutorTool(figures_dir=...)`

### Speed Modes
- [x] `--fast` mode: 5 agents, 6 tasks (skip domain experts), ~20–40 min
- [x] `--smoke` mode: 2 agents, 2 tasks (outline + latex-all), ~3–8 min
  - `create_task_latex_smoke`: single task writing all 11 files, max_iter=55
  - `create_smoke_tasks`: returns [t_outline, t_latex]
  - `smoke_mode` field added to LangGraph `PipelineState`
  - `run_main_pipeline` passes `smoke_mode` to `build_crew`
- [x] `--dry-run` mode: zero LLM calls (~5–30 sec)
  - `src/stubs.py`: pure-Python chapter/PNG generators, all quality-gate-passing
  - `write_stub_chapters(run_folder, topic)`: writes 10 chapters + references.bib + fig_stub.png
  - `main.py --dry-run` bypasses LangGraph; calls stubs → quality gate → PDF compile directly
- [x] All three speed modes wired in `main.py`, `src/crew.py`, `src/graph/nodes.py`

### Docs
- [x] README reflects v5.2 architecture (10 agents, 11 tasks)
- [x] PRD, PLAN, TODO updated to v5.3

---

## Active Targets 🎯

- [ ] Paper reaches 25–30 pages (split-task + 7-file Part-1 fix pending verification via trial run)
- [ ] All chapters pass quality gate (citations, equations, figures in ch07/ch09)
- [ ] Multiply-defined labels eliminated at runtime
- [ ] LaTeX compilation warning-free (undefined references, font substitution)
- [ ] Trial run with new dynamic ch01/ch04 to verify quality gate PASS

---

## Backlog

- [ ] ArXiv tool for researcher (real paper citations instead of fabricated ones)
- [ ] Post-run `references.bib` key validator
- [ ] Token budget enforcement (abort if cost projected > threshold)
- [ ] Investigate paper similarity across runs (temperature=0.3 → consider 0.5)
- [ ] Add `\begin{algorithm}` package (`algorithmicx`) to `main.tex` preamble so ch06 pseudocode compiles
