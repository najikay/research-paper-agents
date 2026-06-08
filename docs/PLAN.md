# NavigatorCrew — Implementation Plan (v5.1)

## Architecture Summary

```
main.py  →  LangGraph pipeline  →  CrewAI 5-agent crew  →  XeLaTeX PDF  →  run archive
```

**CrewAI pipeline** (sequential):
```
outline → research (EN) → figures → hebrew_prose → latex_format
```

**LangGraph state machine** wraps CrewAI:
1. `run_main_pipeline` — runs 5-agent CrewAI crew sequentially
2. `run_quality_gate` — programmatic LaTeX checker (no LLM, no loop risk)
3. `run_remediation` — targeted fix crew (max 2 cycles)
4. `→ END` — PDF compilation via `xelatex → bibtex → xelatex × 2`, then run archive

**Key design principle — language separation:**
Research is done entirely in English (Serper/ArXiv queries in English).
A dedicated HebrewAcademicWriter converts English briefs to Hebrew prose,
preserving technical English terms by judgment (not a hardcoded list).
LaTeXAuthor is a pure formatter — it formats pre-written prose, not a translator.

---

## Phase 1: Architecture (COMPLETE)

- [x] Sequential CrewAI process (`Process.sequential`)
- [x] DeepSeek V3 primary provider (OpenAI-compatible, ~$0.07/run)
- [x] Task-level checkpointing via `output_file`
- [x] LangGraph state machine with feedback loop (max 2 remediation cycles)
- [x] PDF auto-compilation in `main.py` (xelatex → bibtex → xelatex × 2)
- [x] CrewAI v1.14.6 `strict=True` bug patched in venv

## Phase 2: Quality & Content (COMPLETE)

- [x] HebrewAcademicWriter agent added (language separation principle)
  - Research stays English throughout
  - Dedicated agent converts English briefs → Hebrew academic prose
  - Preserves English technical terms by judgment, not hardcoded list
  - LaTeXAuthor simplified to pure formatter
- [x] Programmatic quality gate (replaces looping LLM reviewer)
  - Checks: equation count, figure count, subsection count, word estimate
  - Checks: required BibTeX keys, no placeholders, no em dashes, no `\begin{center}`
- [x] PROTECTED_FILES system blocks agent writes to critical files
  - `cover.tex`, `main.tex`, `ch01_intro.tex`, `ch04_slam.tex`, `src/config.py`
  - Protection check covers both basenames and PROJECT_ROOT-relative paths
- [x] `cover.tex` bidi crash fixed: replaced all `\\[length]` with `\vspace{}`
- [x] `main.tex` restored authoritatively (ch0X_ naming, cover+abstract included)
- [x] Required BibTeX keys (14) baked into agent prompts
- [x] Em dash prohibition enforced in LaTeXAuthor goal
- [x] 25–30 page target in all task descriptions
- [x] Token budget documented in `docs/BUDGET.md`

## Phase 3: Run-Folder Architecture (COMPLETE)

Each run is self-contained in its own folder. Project-root `latex/` is a **read-only template** — agents never touch it.

```
outputs/runs/{topic-slug}-{YYYY-MM-DD}/       ← run folder (single source of truth)
outputs/runs/{topic-slug}-{YYYY-MM-DD}-v2/   ← duplicate dates versioned
```

Run folder layout:
```
latex/
  chapters/   ← template static files + agent-written .tex files
  figures/    ← agent-generated PNGs (written during pipeline)
  references.bib
  main.tex, IEEEtran.cls/bst
outputs/       ← agent .md reports (moved from staging on completion)
paper.pdf      ← compiled PDF (copied from latex/main.pdf)
run_manifest.txt ← file index listing figures and outputs
```

Key functions in `main.py`:
- `setup_run_latex(run_folder)` — copies template into run folder before graph starts
- `compile_pdf(run_folder)` — xelatex → bibtex → xelatex×2 inside `run_folder/latex/`; deletes stale build artifacts first
- `finalize_run(run_folder)` — moves staging .md files to `run_folder/outputs/`, writes manifest

`run_folder` is passed via LangGraph state → `build_crew()` → `create_all_tasks()` so every task description references absolute paths inside `run_folder/latex/`.

- [x] `create_run_folder(topic)` — slug + date-stamp, -v2/-v3 for duplicates
- [x] `setup_run_latex(run_folder)` — template copy before pipeline runs
- [x] `finalize_run(run_folder)` — staging cleanup + manifest with figure listing
- [x] `--no-archive` flag for smoke tests
- [x] `outputs/runs/` excluded from git; agent-generated chapters/figures also excluded

## Phase 4: Bug Fixes Applied (COMPLETE)

- [x] `references.bib` overwrite — `output_file` changed to `outputs/current/latex_status.md`; agent instructed to write bib via SafeFileWriterTool with absolute path
- [x] `\textenglish` hyperref crash — `\newcommand{\en}` uses `\texorpdfstring`
- [x] Stale `main.out` crash — build artifacts deleted before every xelatex compile
- [x] `FileReaderTool` leading-slash fix — LLM-passed `/outputs/X.md` stripped to relative path
- [x] Math operators added to `main.tex`: `\rect`, `\sinc`, `\sgn`, `\diag`, `\tr`
- [x] Figure existence check in quality gate — catches hallucinated figure names
- [x] PROTECTED_FILES basename matching — protection works in both project-root and run-folder paths

## Phase 5: Pending

- [ ] Full run that reaches 25–30 pages in PDF
- [ ] All chapters pass quality gate (score ≥ 75)
- [ ] No LaTeX compilation errors (xelatex exits 0)
- [ ] Push clean version to GitHub

## Backlog

- [ ] ArXiv search for real citations in researcher
- [ ] Post-run `references.bib` key validator (belt-and-suspenders)
- [ ] Token-budget enforcement: abort if projected cost exceeds threshold
- [ ] Evaluate domain-expert agents (physics, CS, AI engineering professors)
