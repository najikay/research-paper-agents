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
- [x] LaTeX task split into Part 1 (abstract+ch02/03/05+bib) and Part 2 (ch06/07/08/09+appendix)
- [x] `latex_author` max_iter 25→40; `hebrew_writer` max_iter 20→35
- [x] PLAN step in each latex task (agent outlines before writing)
- [x] Hebrew prose target: 800–1200 words/chapter; ch06/ch08 ≥ 1400 words
- [x] LaTeX minimums: 1000 words, 5 subsections, 4 equations per chapter
- [x] Figure WIDTH rules: `figure*`+`\textwidth` for wide figs; min 11pt font
- [x] Label uniqueness: chapter-prefix convention `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose
- [x] Appendix (symbols+variables table) in ch09 — organic page count addition
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] PROTECTED_FILES (basename + relative path): cover, main, ch01, ch04, config.py
- [x] `references.bib` overwrite bug fixed
- [x] `\textenglish` hyperref crash fixed via `\texorpdfstring`
- [x] Stale `main.out` crash fixed: build artifacts deleted before every compile
- [x] Math operators in `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] Quality gate: em dashes only checked in agent-written files (not ch01/ch04/cover)
- [x] Quality gate: figure existence check (catches hallucinated filenames)
- [x] 5th XeLaTeX pass added (resolves rerunfilecheck warnings)
- [x] ch01_intro.tex and ch04_slam.tex restored to latex/ template

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
- [x] 132 tests across 11 files — all passing
- [x] test_tasks: updated for 11-task pipeline, part1/part2 fixtures
- [x] test_quality_gate: updated thresholds (≥3 equations, ≥600 words)
- [x] test_run_archive: updated to test `finalize_run`
- [x] test_tools_code_executor: fixed to use `PythonCodeExecutorTool(figures_dir=...)`

### Docs
- [x] README reflects v5.2 architecture (10 agents, 11 tasks)
- [x] PRD, PLAN, TODO updated to v5.2

---

## Active Targets 🎯

- [ ] Paper reaches 25–30 pages (current: ~12 pages — split-task fix pending verification)
- [ ] All chapters pass quality gate issues (citations, equations, figures in ch07/ch09)
- [ ] Multiply-defined labels eliminated at runtime
- [ ] LaTeX compilation warning-free (undefined references, font substitution)

---

## Backlog

- [ ] ArXiv tool for researcher (real paper citations instead of fabricated ones)
- [ ] Post-run `references.bib` key validator
- [ ] Token budget enforcement (abort if cost projected > threshold)
- [ ] Investigate paper similarity across runs (temperature=0.3 → consider 0.5)
- [ ] Add `\begin{algorithm}` package (`algorithmicx`) to `main.tex` preamble so ch06 pseudocode compiles
