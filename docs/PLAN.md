# NavigatorCrew — Implementation Plan

## Architecture Summary

```
main.py  →  LangGraph pipeline  →  CrewAI crews (split: research + writing)  →  XeLaTeX PDF  →  run archive
```

**Full pipeline (split mode, default):**
```
research_phase:   outline → research → [8x domain experts]
validate_research: programmatic check + fixer crew
writing_phase:    figures → hebrew_prose → latex_a + latex_b + latex_c
quality_gate:     programmatic checker → PASS/FAIL
remediation:      targeted fix crew (max 4 cycles)
```

**LangGraph state machine** (split_mode=True):
1. `run_research_phase` — 10 agents: director + researcher + 8 domain experts
2. `validate_and_fix_research` — checks output sizes, detects stuck agents, re-runs failures
3. `run_writing_phase` — 5 agents: visualizer + Hebrew writer + 3 LaTeX authors (A/B/C)
4. `run_quality_gate` — programmatic checker (no LLM); includes sanitizer + fallback figures
5. `run_remediation` — targeted fix crew (max 4 cycles)
6. `→ END` — PDF compilation (xelatex → bibtex → xelatex x 3), then run archive

**Key design principles:**
- **Split pipeline**: Research and writing run as separate CrewAI crews with validation between them
- **3 LaTeX writers**: A (abstract+ch01-ch03+bib), B (ch04-ch06), C (ch07-ch09) — parallel-safe
- **Resilient compilation**: `\IfFileExists` guards; 25-fix sanitizer; missing figures auto-stubbed
- **Topic-agnostic**: All agents derive content from the dynamic outline
- **8 domain experts**: PhD specialists enrich chapters in their field
- **Fully dynamic content**: Only `cover.tex` is static; all 10 content files are agent-written

---

## Phase 1: Architecture (COMPLETE)

- [x] Sequential CrewAI process (`Process.sequential`)
- [x] DeepSeek V3 primary provider (OpenAI-compatible, ~$0.22/run base)
- [x] Task-level checkpointing via `output_file`
- [x] LangGraph state machine with feedback loop (max 4 remediation cycles)
- [x] PDF auto-compilation in `main.py` (xelatex → bibtex → xelatex x 3 = 5 passes)

## Phase 2: Quality & Content (COMPLETE)

- [x] HebrewAcademicWriter agent (language separation principle)
- [x] Programmatic quality gate (replaces looping LLM reviewer)
- [x] PROTECTED_FILES system (basename + relative path matching)
- [x] `cover.tex` bidi crash fixed
- [x] Em dash prohibition + auto-sanitizer

## Phase 3: Run-Folder Architecture (COMPLETE)

- [x] Each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `run_folder` passed through LangGraph state
- [x] `setup_run_latex()`, `compile_pdf()`, `finalize_run()`

## Phase 4: LaTeX Sanitizer (COMPLETE)

- [x] 25 automatic fixes in `_sanitize_tex_files()`
- [x] Font fallback chain (hebrewfont, hebrewfonttt, hebrewfontsf, englishfont)
- [x] Math operators, lstlisting LTR wrapping, `\adjustbox` for tables

## Phase 5: Domain Expert Agents (COMPLETE)

- [x] 8 PhD-level domain experts: VisionAI, Physics, Algorithms, AerospaceMarine, Biology, SignalProcessing, ControlSystems, ML
- [x] DOMAIN SKIP mechanism for irrelevant topics
- [x] `create_task_domain_expert()` factory

## Phase 6: Split Pipeline Architecture (COMPLETE)

- [x] LangGraph split: `run_research_phase` → `validate_and_fix_research` → `run_writing_phase`
- [x] Research validation node: checks domain output sizes, detects stuck agents
- [x] Fixer crew re-runs failed domain expert tasks
- [x] 3 LaTeX writers (A/B/C) replace 2-part split

## Phase 7: Fully Dynamic Architecture (COMPLETE)

- [x] `ch01_intro.tex` and `ch04_slam.tex` fully agent-written (dynamic)
- [x] `cover.tex` is the only static chapter file
- [x] Topic-agnostic figure specs, BibTeX, and prompts

## Phase 8: Three-Speed Pipeline (COMPLETE)

- [x] `--fast` mode: 5 agents, 6 tasks, ~20-40 min
- [x] `--smoke` mode: 2 agents, 2 tasks, ~10-20 min
- [x] `--dry-run` mode: zero LLM calls, ~5-30 sec

## Phase 9: Content Depth & Word Targets (COMPLETE)

- [x] Hebrew writer: per-chapter word targets (1500-2500 words)
- [x] LaTeX author CONTENT DEPTH CONTRACT aligned with quality gate (2500-4000 words)
- [x] 3-split task targets aligned with shared rules (2500-4000 words)

## Phase 10: Sanitizer Hardening (COMPLETE)

- [x] Fix 20: Brace repair for truncated files (unclosed `{` from agent token limit)
- [x] Fix 21: Author-name commands (`\Au`, `\Thorp`) → `\en{Word}` (with Greek letter exclusions)
- [x] Fix 22: `\ensuremath{$\theta$}` nested math mode → `$\theta$` (brace-counting parser)
- [x] Fix 23: Stray `}` removal via brace-depth tracking (replaced dangerous regex)
- [x] Removed `-halt-on-error` from xelatex — PDFs compile fully past non-fatal errors

## Phase 11: Figure Sizing & Error Elimination (COMPLETE)

- [x] Fix 24: Auto-upgrade wide figures (`figure` → `figure*`) based on PNG aspect ratio > 1.8
- [x] Fix 25: Extract math superscripts from `\en{}` blocks (`\en{m/s^2}` → `\en{m/s}$^2$`)
- [x] LaTeX writer instructions updated: explicit `figure*` guidance for wide images
- [x] Result: 19 → 22 pages from figure sizing alone; 0 fatal LaTeX errors

## Phase 12: Quality Gate & Remediation Calibration (COMPLETE)

- [x] `QUALITY_THRESHOLD` raised 75 → 90 (remediation fires more often)
- [x] `MAX_REMEDIATIONS` raised 3 → 4
- [x] Thresholds calibrated to LLM output: default 1400, ch06/ch08 1800, ch07 1600
- [x] Remediation prompt improved: reads references.bib, targets 400+ words/chapter, processes ALL failures
- [x] Result: 23 pages, score 96/100, 3 remediation cycles

## Backlog

- [ ] Push page count to 25 pages consistently (currently 23)
- [ ] Push score to 100/100 consistently (currently 96)
- [ ] ArXiv search for real citations in researcher
- [ ] Post-run `references.bib` key validator
- [ ] Token-budget enforcement: abort if projected cost exceeds threshold
