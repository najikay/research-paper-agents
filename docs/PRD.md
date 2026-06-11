# Product Requirements Document — NavigatorCrew
**Version**: 13.0 | **Date**: 2026-06-11

---

## 1. Summary

NavigatorCrew is an autonomous multi-agent system that takes a research topic as input and produces a complete, compiled IEEE-formatted bilingual (Hebrew/English) academic paper. It is built on CrewAI v1.14+ (sequential process) wrapped in a LangGraph state machine with a programmatic quality gate, automatic run archiving, and a split research/writing pipeline.

---

## 2. Pipeline Architecture

```
main.py --topic "..." [--fast | --smoke | --dry-run]
  ├── --dry-run  → write_stub_chapters() → run_quality_gate() → compile_pdf()  (~5-30 sec, 0 LLM calls)
  └── LangGraph state machine
        ├── split_mode=True (default):
        │     run_research_phase     → CrewAI crew (10 agents: director + researcher + 8 domain experts)
        │     validate_and_fix_research → programmatic check + Fixer crew for failures
        │     run_writing_phase      → CrewAI crew (5 agents: visualizer + Hebrew writer + 3 LaTeX authors)
        │     run_quality_gate       → programmatic checker (no LLM)
        │     run_remediation        → targeted fix crew (max 3 cycles)
        │     END                    → XeLaTeX compile (5 passes) + run archive
        └── split_mode=False (--fast/--smoke):
              run_main_pipeline      → single CrewAI crew
              run_quality_gate → run_remediation → END
```

### Speed Modes

| Flag | Agents | Tasks | Est. Time | Use case |
|---|---|---|---|---|
| (none) | 13 | ~18 | 60-120 min | Production runs (split pipeline) |
| `--fast` | 5 | 6 | 20-40 min | Dev iteration, skip domain experts |
| `--smoke` | 2 | 2 | 10-20 min | Quick structural test, outline + latex |
| `--dry-run` | 0 | 0 | 5-30 sec | PDF compile pipeline verification only |

### Full Pipeline — Split Architecture (v6+)

**Phase 1: Research (10 agents, sequential CrewAI crew)**

| # | Agent | Input | Output |
|---|---|---|---|
| 1 | NavigationDirector | `--topic` | `paper_outline.md` |
| 2 | SLAMResearcher | outline | `research_briefs.md` |
| 3 | VisionAIExpert | briefs | `domain_vision_ai.md` |
| 4 | PhysicsExpert | briefs | `domain_physics.md` |
| 5 | AlgorithmsExpert | briefs | `domain_algorithms.md` |
| 6 | AerospaceMarineExpert | briefs | `domain_aerospace.md` |
| 7 | BiologyExpert | briefs | `domain_biology.md` |
| 8 | SignalProcessingExpert | briefs | `domain_signal_processing.md` |
| 9 | ControlSystemsExpert | briefs | `domain_control_systems.md` |
| 10 | MLExpert | briefs | `domain_ml.md` |

**Validation: Research Validator + Fixer**
- Programmatic check: each domain output must be >= 500 bytes and not stuck in a loop
- Fixer crew re-runs any failed domain expert tasks

**Phase 2: Writing (5 agents, sequential CrewAI crew)**

| # | Agent | Input | Output |
|---|---|---|---|
| 1 | VisualizationEngineer | outline + briefs | `latex/figures/*.png` + `figures_manifest.md` |
| 2 | HebrewAcademicWriter | briefs + all domain files | `hebrew_prose.md` |
| 3 | LaTeX Writer A | prose + outline | `abstract.tex`, `ch01-ch03.tex`, `references.bib` |
| 4 | LaTeX Writer B | prose + figures | `ch04-ch06.tex` |
| 5 | LaTeX Writer C | prose + figures | `ch07-ch09.tex` |

All staging paths are in `outputs/current/` and moved to `{run_folder}/outputs/` by `finalize_run()`.

### Quality Gate (programmatic, in LangGraph node)

Per-chapter minimums (v13 thresholds):

| Check | Default | abstract | ch01 | ch06/ch08 | ch07 | ch09 |
|---|---|---|---|---|---|---|
| Equations | >= 2 | 0 | 1 | 3 | 2 | 0 |
| Figures | >= 1 | 0 | 0 | 1 | 1 | 0 |
| Subsections | >= 3 | 0 | 3 | 5 | 4 | 2 |
| Citations | >= 2 | 0 | 2 | 3 | 2 | 1 |
| Words | >= 1400 | 80 | 1400 | 1800 | 1600 | 700 |

Additional checks:
- `references.bib` entry count >= 10
- Missing figure file penalty capped at -20 total
- No `\begin{center}` at document level, no em dashes, no placeholder `\fbox` boxes
- `\°` (undefined control sequence) auto-replaced with `°` by sanitizer

Score < 90 -> FAIL -> remediation crew (max 4 cycles) -> re-check.

---

## 3. Agents

| Agent | Model | Max Iter | Tools |
|---|---|---|---|
| NavigationDirector | DeepSeek V3 | 12 | FileReader, SafeFileWriter, Serper, ArXiv |
| SLAMResearcher | DeepSeek V3 | 18 | FileReader, Serper, ArXiv, WebScraper |
| VisionAIExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| PhysicsExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| AlgorithmsExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| AerospaceMarineExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| BiologyExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| SignalProcessingExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| ControlSystemsExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| MLExpert | DeepSeek V3 | 15 | FileReader, SafeFileWriter, Serper, ArXiv |
| VisualizationEngineer | DeepSeek V3 | 40 | CodeExecutor, SafeFileWriter, FileReader |
| HebrewAcademicWriter | DeepSeek V3 | 40 | FileReader, SafeFileWriter |
| LaTeXAuthor (x3) | DeepSeek V3 | 30 | SafeFileWriter, FileReader |

---

## 4. Content Strategy

Research is conducted entirely in English (Serper/ArXiv queries, research briefs, 8 domain expert outputs). HebrewAcademicWriter converts the English content into Hebrew academic prose with per-chapter word targets:
- ch01: >= 1500 words, ch02-ch05: >= 2000, ch06/ch08: >= 2500, ch07: >= 2000, ch09: >= 1200

LaTeX writers wrap the prose in XeLaTeX with per-chapter content depth targets:
- ch01: >= 2500 words, ch02-ch05: >= 3200, ch06/ch08: >= 4000, ch07: >= 3200, ch09: >= 2000

If `hebrew_prose.md` is missing, LaTeX writers fall back to writing Hebrew prose from `research_briefs.md`.

---

## 5. Protected Files

| File | Reason |
|---|---|
| `main.tex` | Controls chapter order and XeLaTeX preamble |
| `cover.tex` | `\vspace{}` fix for bidi crash; student name/date |
| `src/config.py` | Runtime configuration |
| `.env`, `.gitignore`, `requirements.txt` | Project hygiene |

All content chapters (abstract, ch01-ch09) are **agent-written**. `cover.tex` is the only static chapter.

---

## 6. Run-Folder Architecture

Each run is **self-contained** in `outputs/runs/{topic-slug}-{YYYY-MM-DD}/` (versioned with `-v2`, `-v3`).

```
outputs/runs/{slug}-{date}/
  latex/
    chapters/   <- cover.tex (static) + 10 agent-written .tex files (abstract + ch01-ch09)
    figures/    <- fig_stub.png (pre-seeded) + agent-generated PNGs
    references.bib
    main.tex, IEEEtran.cls/bst
  outputs/      <- agent .md reports (moved from outputs/current/ on completion)
  paper.pdf     <- compiled PDF
  run_manifest.txt
```

---

## 7. LaTeX Sanitizer (25 fixes)

`_sanitize_tex_files()` in `main.py` auto-fixes common agent errors before compilation:

1. Remove `\begin{abstract}` inside abstract.tex
2. Remove `\begin{document}` / `\end{document}` inside chapters
3. Remove `\documentclass` inside chapters
4. Remove `\usepackage` inside chapters
5. Replace `\begin{center}` with `\centering` (bidi crash prevention)
6. Remove stray `\maketitle`
7. Replace em dashes (U+2014) with colons
8. Remove `\textemdash` / `\textendash`
9. Wrap `lstlisting` in `\begin{english}` for LTR
10. Replace `[H]` float placement with `[htbp]`
11. Wrap `tabular` in `\adjustbox{max width=\columnwidth}`
11b. Escape bare `%` in running text (prevents comment-swallowing)
12a-c. Fix `\en{}` in math mode, remove english wrappers around tables, fix `\figref`/`\tabref`
13. Convert `algorithm`/`algorithmic` environments to `lstlisting`
14. Fix literal `\\n` sequences in tabular rows
15. Remove backslash before Hebrew characters
16. Escape underscores inside `\en{}`
17. Replace `\°` with Unicode `°` (XeLaTeX handles natively)
20. Repair truncated files with unbalanced braces (agent token-limit truncation)
21. Author-name commands (`\Au`, `\Thorp`) → `\en{Word}` (with Greek letter exclusions)
22. `\ensuremath{$\theta$}` nested math mode → `$\theta$` (brace-counting parser)
23. Stray `}` removal via brace-depth tracking
24. Auto-upgrade wide figures (`figure` → `figure*`) based on PNG aspect ratio > 1.8
25. Extract math superscripts from `\en{}` blocks (`\en{m/s^2}` → `\en{m/s}$^2$`)

---

## 8. Success Criteria

| Criterion | Target | Current |
|---|---|---|
| Paper length | 25-30 printed pages | 23 pages (v13, with remediation) |
| Quality gate score | >= 90/100 | 96/100 |
| BibTeX entries | >= 10 in quality gate; agent targets >= 14 | 14+ entries |
| LaTeX compilation | PDF > 0 bytes and openable | 4.1 MB PDF, 0 fatal errors |
| Cost per run | <= $0.14 (including worst-case remediation) | ~$0.07-0.15 |
| Execution | Unattended, no manual intervention | Fully autonomous |
