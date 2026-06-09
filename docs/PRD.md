# Product Requirements Document — NavigatorCrew
**Version**: 5.2 | **Date**: 2026-06-09

---

## 1. Summary

NavigatorCrew is an autonomous multi-agent system that takes a research topic as input and produces a complete, compiled IEEE-formatted bilingual (Hebrew/English) academic paper. It is built on CrewAI v1.14+ (sequential process) wrapped in a LangGraph state machine with a programmatic quality gate and automatic run archiving.

---

## 2. Pipeline Architecture

```
main.py --topic "..."
  └─► LangGraph state machine
        ├─ run_main_pipeline   → 10-agent CrewAI crew (11 tasks, sequential)
        ├─ run_quality_gate    → programmatic checker (no LLM)
        ├─ run_remediation     → targeted fix crew (max 2 cycles)
        └─ END                 → XeLaTeX compile (5 passes) + run archive
```

### CrewAI Sequential Pipeline (11 tasks)

| # | Agent | Input | Output |
|---|---|---|---|
| 1 | NavigationDirector | `--topic` | `outputs/current/paper_outline.md` |
| 2 | SLAMResearcher | outline | `outputs/current/research_briefs.md` |
| 3 | VisionAIExpert | briefs | `outputs/current/domain_vision_ai.md` |
| 4 | PhysicsExpert | briefs | `outputs/current/domain_physics.md` |
| 5 | AlgorithmsExpert | briefs | `outputs/current/domain_algorithms.md` |
| 6 | AerospaceMarineExpert | briefs | `outputs/current/domain_aerospace.md` |
| 7 | BiologyExpert | briefs | `outputs/current/domain_biology.md` |
| 8 | VisualizationEngineer | briefs | `{run_folder}/latex/figures/*.png` + `figures_manifest.md` |
| 9 | HebrewAcademicWriter | briefs + all domain files | `outputs/current/hebrew_prose.md` |
| 10 | LaTeXAuthor (part 1) | prose + figures + domain files | `abstract.tex`, `ch02-03.tex`, `ch05.tex`, `references.bib` |
| 11 | LaTeXAuthor (part 2) | part 1 output | `ch06-09.tex` + appendix (symbols table) |

All `outputs/current/` paths are **staging** — moved to `{run_folder}/outputs/` by `finalize_run()` on completion.

### Domain Expert DOMAIN SKIP Mechanism

Each domain expert reads the research briefs and assesses relevance. If the topic has no meaningful intersection with their field they output `"DOMAIN SKIP: [reason]"`. Downstream agents (HebrewAcademicWriter, LaTeXAuthor) detect this prefix and ignore those files. This prevents irrelevant domain content from polluting the paper while keeping all experts available for any topic.

### Quality Gate (programmatic, in LangGraph node)

Checks per agent-written chapter file:
- Equation count ≥ 3
- Figure count ≥ 1
- Subsection count ≥ 3
- Word estimate ≥ 600
- Citation count ≥ 2
- All 14 required BibTeX keys present in `references.bib`
- No forbidden patterns: `\begin{center}` at document level, em dashes in Hebrew prose (outside `\en{}`), placeholder `\fbox` boxes, missing figure files

Score < 75 → FAIL → remediation crew (max 2 cycles) → re-check.

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
| VisualizationEngineer | DeepSeek V3 | 12 | CodeExecutor, SafeFileWriter, FileReader |
| HebrewAcademicWriter | DeepSeek V3 | 35 | FileReader, SafeFileWriter |
| LaTeXAuthor | DeepSeek V3 | 40 | SafeFileWriter, FileReader |

---

## 4. Language Separation

Research is conducted entirely in English (Serper/ArXiv queries, research briefs, domain expert outputs). HebrewAcademicWriter converts the English content into polished Hebrew academic prose (800–1200 words per chapter), preserving English technical terms by judgment (the same way a Technion professor writes). LaTeXAuthor is a pure formatter: it wraps pre-written Hebrew prose in XeLaTeX environments, enforcing `\en{}` wrapping for all inline English to prevent bidi crashes.

---

## 5. Protected Files

The following files are blocked from agent writes in `SafeFileWriterTool` via both basename and relative-path matching (protection works in the project root **and** inside run folders):

| File | Reason |
|---|---|
| `main.tex` | Controls chapter order and XeLaTeX preamble |
| `cover.tex` | `\\[len]` fix for bidi crash; student name/date |
| `ch01_intro.tex` | Static intro with fixed citation keys |
| `ch04_slam.tex` | Static SLAM chapter with fixed citation keys |
| `src/config.py` | Runtime configuration |
| `.env`, `.gitignore`, `requirements.txt` | Project hygiene |

---

## 6. Run-Folder Architecture

Each run is **self-contained** in `outputs/runs/{topic-slug}-{YYYY-MM-DD}/` (versioned with `-v2`, `-v3`). Project-root `latex/` is a read-only template and is never modified during a run.

```
outputs/runs/{slug}-{date}/
  latex/
    chapters/   ← template static files (ch01, ch04, cover) + 8 agent-written .tex files
    figures/    ← agent-generated PNGs (300 DPI, min 11pt font)
    references.bib
    main.tex, IEEEtran.cls/bst
  outputs/      ← agent .md reports + domain expert files (moved from outputs/current/)
  paper.pdf     ← compiled PDF
  run_manifest.txt ← file index with figure listing
```

`setup_run_latex(run_folder)` copies the template before the pipeline starts. `compile_pdf(run_folder)` runs xelatex→bibtex→xelatex×3 inside `run_folder/latex/` (5 total passes) and copies the PDF to `run_folder/paper.pdf`. `finalize_run(run_folder)` moves staging files and writes the manifest.

---

## 7. Figure Requirements

Each of the 9 required figures:
- Minimum 300 DPI PNG
- Minimum font size 11pt for all text elements
- Wide figures (flowcharts, multi-panel, block diagrams) use `figure*` float with `[width=\textwidth]`
- Single-column figures use `[width=0.98\columnwidth]`
- All labels prefixed with chapter ID to prevent multiply-defined-label warnings

---

## 8. Success Criteria

| Criterion | Target |
|---|---|
| Paper length | 25–30 printed A4 pages |
| Quality gate score | ≥ 75/100 |
| Required BibTeX keys | All 14 present |
| LaTeX compilation | xelatex exits 0, no `!` errors |
| Cost per run | ≤ $0.14 (including worst-case remediation) |
| Execution | Unattended, no manual intervention |
