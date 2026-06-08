# NavigatorCrew — Implementation Plan (v5.0)

## Architecture Summary

```
main.py  →  LangGraph pipeline  →  CrewAI 5-agent crew  →  XeLaTeX PDF
```

**CrewAI pipeline** (sequential):
```
outline → research (EN) → figures → hebrew_prose → latex_format
```

**LangGraph state machine** wraps CrewAI:
1. `run_main_pipeline` — runs 5-agent CrewAI crew sequentially
2. `run_quality_gate` — programmatic LaTeX checker (no LLM, no loop risk)
3. `run_remediation` — targeted fix crew (max 2 cycles)
4. `→ END` — PDF compilation via `xelatex → bibtex → xelatex × 2`

**Key design principle — language separation:**
Research is done entirely in English (Serper/ArXiv queries in English).
A dedicated HebrewAcademicWriter converts English briefs to Hebrew prose,
preserving technical English terms by judgment (not a hardcoded list).
LaTeXAuthor is a pure formatter — it formats pre-written prose, not a translator.

---

## Phase 1: Architecture (COMPLETE)

- [x] Sequential CrewAI process (`Process.sequential`)
- [x] Model tiering in `src/config.py` (DeepSeek V3 primary, Anthropic fallback)
- [x] Task-level checkpointing via `output_file`
- [x] LangGraph state machine with feedback loop (max 2 remediation cycles)
- [x] PDF auto-compilation in `main.py`
- [x] DeepSeek V3 integration (OpenAI-compatible, ~$0.07/run)
- [x] CrewAI v1.14.6 `strict=True` bug patched in venv

## Phase 2: Quality & Content (COMPLETE)

- [x] HebrewAcademicWriter agent added (language separation)
  - Research stays English throughout (Serper/ArXiv queries in English)
  - Dedicated agent converts briefs → Hebrew academic prose
  - Preserves English technical terms by judgment, not hardcoded list
  - LaTeXAuthor simplified to pure formatter

- [x] Programmatic quality gate (replaces looping LLM reviewer)
  - Checks: equation count, figure count, subsection count, word estimate
  - Checks: required BibTeX keys, no placeholders, no em dashes, no `\begin{center}`
- [x] `cover.tex` protected from agent overwrite (XeLaTeX crash fix)
- [x] Required BibTeX keys baked into agent prompts (14 keys)
- [x] Em dash prohibition in LaTeX author goal
- [x] 25–30 page target in all task descriptions
- [x] Token budget documented in `docs/BUDGET.md`

## Phase 3: Run Archiving (COMPLETE)

Each run is automatically archived to its own folder:

```
outputs/runs/{topic-slug}-{YYYY-MM-DD}/
outputs/runs/{topic-slug}-{YYYY-MM-DD}-v2/   ← if same date already exists
```

Contents of each run folder:
```
outputs/    ← paper_outline.md, research_briefs.md, hebrew_prose.md,
              figures_manifest.md, quality_report.md, token_report.md
latex/      ← full LaTeX source snapshot (no build artifacts)
paper.pdf   ← compiled PDF (if compilation succeeded)
run_manifest.txt  ← human-readable index of archived files
```

- [x] `create_run_folder(topic)` in main.py — slug from topic, date-stamped, v2/v3 for duplicates
- [x] `archive_run(run_folder, pdf_path)` — copies outputs + LaTeX snapshot + PDF
- [x] `--no-archive` flag to skip archiving in smoke tests
- [x] `outputs/runs/` excluded from git (gitignore)

## Phase 4: Current Run Targets

- [ ] Paper reaches 25–30 pages in PDF output
- [ ] All chapters pass programmatic quality gate (score ≥ 75)
- [ ] `references.bib` contains all 14 required keys
- [ ] No LaTeX compilation errors (xelatex exits 0)
- [ ] Push clean version to GitHub

## Phase 4: Future Improvements (Backlog)

- [ ] Add ArXiv search tool to researcher for real citations
- [ ] Add a post-processing hook that auto-restores references.bib
  if the agent generates wrong keys
- [ ] Soft fact-check: verify numeric claims (34% improvement, etc.)
  against simulation data in outputs/
- [ ] Consider a separate `CitationFixer` agent that runs after LaTeXAuthor
  to verify and patch references.bib
- [ ] Token-budget enforcement: abort run if projected cost exceeds threshold
