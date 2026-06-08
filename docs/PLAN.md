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

## Phase 3: Run Archiving (COMPLETE)

Each run is automatically archived to its own folder:

```
outputs/runs/{topic-slug}-{YYYY-MM-DD}/
outputs/runs/{topic-slug}-{YYYY-MM-DD}-v2/   ← duplicate dates versioned
```

Contents:
```
figures/         ← PNG figures for direct access
outputs/         ← paper_outline.md, research_briefs.md, hebrew_prose.md,
                    figures_manifest.md, quality_report.md, token_report.md
latex/           ← full LaTeX source snapshot (no build artifacts)
paper.pdf        ← compiled PDF (if successful)
run_manifest.txt ← human-readable file index
```

- [x] `create_run_folder(topic)` — slug + date-stamp, -v2/-v3 for duplicates
- [x] `archive_run()` — copies figures, outputs, LaTeX snapshot, PDF
- [x] `--no-archive` flag for smoke tests
- [x] `outputs/runs/` excluded from git

## Phase 4: Bug Fixes Applied (COMPLETE)

Root-cause fixes applied after first real run (score=18):

- [x] `references.bib` overwrite — changed `create_task_latex` `output_file` from `"latex/references.bib"` to `"outputs/latex_status.md"` so CrewAI's auto-write mechanism doesn't destroy the file; added explicit SafeFileWriterTool instruction in task description
- [x] `\textenglish` hyperref crash — changed `\newcommand{\en}` to use `\texorpdfstring{\textenglish{#1}}{#1}` in `latex/main.tex`
- [x] PDF duplication — `compile_pdf()` no longer copies to `outputs/NavigatorCrew_paper.pdf`; returns `latex/main.pdf` path directly for the archive
- [x] Stale outputs cleared — `outputs/runs/` old folder and loose `.md`/`.pdf` files deleted

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
