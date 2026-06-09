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
- **Split LaTeX task**: Part 1 (abstract+ch02/03/05+bib) and Part 2 (ch06/07/08/09+appendix), each with its own 40-iter budget — prevents agent from being cut off mid-paper

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
  - Checks: required BibTeX keys, no placeholders, no em dashes, no `\begin{center}`
- [x] PROTECTED_FILES system (basename + relative path matching)
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}`
- [x] Required BibTeX keys (14) baked into agent prompts
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
- [x] Quality gate static file exclusion — ch01_intro, ch04_slam, cover excluded from em dash / center checks
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
  - Part 1: abstract + ch02 + ch03 + ch05 + references.bib
  - Part 2: ch06 + ch07 + ch08 + ch09 + appendix (symbols table)
  - Each task has max_iter=40 independently — no longer cut off mid-paper
- [x] PLAN step added to each latex task — agent outlines before writing
- [x] `latex_author` max_iter: 25 → 40; `hebrew_writer` max_iter: 20 → 35
- [x] Figure size rules: wide figures use `figure*` + `\textwidth`; min 11pt font
- [x] Label uniqueness enforced: chapter-prefixed `\label{fig:ch02_name}`
- [x] `\en{}` wrapping requirement for all inline English in Hebrew prose
- [x] Appendix (symbols+variables table) added to ch09 — organic page count boost
- [x] ch01_intro.tex and ch04_slam.tex restored to latex/ template

## Phase 7: Pending

- [ ] Full run reaching 25–30 pages in PDF
- [ ] All chapters pass quality gate (score ≥ 75) without issues logged
- [ ] No LaTeX compilation errors (xelatex exits 0)
- [ ] Multiply-defined label warnings eliminated at runtime

## Backlog

- [ ] ArXiv search for real citations in researcher
- [ ] Post-run `references.bib` key validator
- [ ] Token-budget enforcement: abort if projected cost exceeds threshold
- [ ] Investigate paper similarity across runs (temperature currently 0.3)
