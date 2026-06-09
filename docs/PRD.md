# Product Requirements Document — NavigatorCrew
**Version**: 5.5 | **Date**: 2026-06-09

---

## 1. Summary

NavigatorCrew is an autonomous multi-agent system that takes a research topic as input and produces a complete, compiled IEEE-formatted bilingual (Hebrew/English) academic paper. It is built on CrewAI v1.14+ (sequential process) wrapped in a LangGraph state machine with a programmatic quality gate and automatic run archiving.

---

## 2. Pipeline Architecture

```
main.py --topic "..." [--fast | --smoke | --dry-run]
  ├─► --dry-run  → write_stub_chapters() → run_quality_gate() → compile_pdf()  (~5–30 sec, 0 LLM calls)
  └─► LangGraph state machine
        ├─ run_main_pipeline   → CrewAI crew (10/5/2 agents, 11/6/2 tasks by mode)
        ├─ run_quality_gate    → programmatic checker (no LLM)
        ├─ run_remediation     → targeted fix crew (max 2 cycles)
        └─ END                 → XeLaTeX compile (5 passes) + run archive
```

### Speed Modes

| Flag | Agents | Tasks | Est. Time | LLM Calls | Use case |
|---|---|---|---|---|---|
| (none) | 10 | 11 | 60–120 min | ~500 | Production runs |
| `--fast` | 5 | 6 | 20–40 min | ~200 | Dev iteration, skip domain experts |
| `--smoke` | 2 | 2 | 10–20 min | ~35 | Quick structural test, outline + latex |
| `--dry-run` | 0 | 0 | 5–30 sec | 0 | PDF compile pipeline verification only |

### Full Pipeline — CrewAI Sequential (11 tasks)

| # | Agent | Input | Output |
|---|---|---|---|
| 1 | NavigationDirector | `--topic` | `outputs/current/paper_outline.md` |
| 2 | SLAMResearcher | outline | `outputs/current/research_briefs.md` |
| 3 | VisionAIExpert | briefs | `outputs/current/domain_vision_ai.md` |
| 4 | PhysicsExpert | briefs | `outputs/current/domain_physics.md` |
| 5 | AlgorithmsExpert | briefs | `outputs/current/domain_algorithms.md` |
| 6 | AerospaceMarineExpert | briefs | `outputs/current/domain_aerospace.md` |
| 7 | BiologyExpert | briefs | `outputs/current/domain_biology.md` |
| 8 | VisualizationEngineer | outline + briefs | `{run_folder}/latex/figures/*.png` + `figures_manifest.md` |
| 9 | HebrewAcademicWriter | briefs + all domain files | `outputs/current/hebrew_prose.md` |
| 10 | LaTeXAuthor (part 1) | outline + prose (or briefs fallback) | `abstract.tex`, `ch01–ch05.tex`, `references.bib` (7 files) |
| 11 | LaTeXAuthor (part 2) | outline + figures manifest + prose | `ch06–ch09.tex` (4 files) |

All `outputs/current/` paths are **staging** — moved to `{run_folder}/outputs/` by `finalize_run()` on completion.

### Smoke Pipeline — 2 tasks

| # | Agent | Task |
|---|---|---|
| 1 | NavigationDirector | Outline — writes `paper_outline.md` |
| 2 | LaTeXAuthor | Writes all 11 files from outline in one pass (max_iter=35) |

No research, no domain experts, no figures agent, no Hebrew prose step. Uses `fig_stub.png` for all figures.

### Domain Expert DOMAIN SKIP Mechanism

Each domain expert reads the research briefs and assesses relevance. If the topic has no meaningful intersection with their field they output `"DOMAIN SKIP: [reason]"`. Downstream agents detect this prefix and ignore those files.

### Quality Gate (programmatic, in LangGraph node)

Per-chapter minimums (default — abstract/ch01/ch09 have relaxed thresholds):

| Check | Default | abstract | ch01 | ch09 |
|---|---|---|---|---|
| Equations | ≥ 3 | 0 | 1 | 0 |
| Figures | ≥ 1 | 0 | 0 | 0 |
| Subsections | ≥ 3 | 0 | 2 | 2 |
| Citations | ≥ 2 | 0 | 2 | 1 |
| Words | ≥ 600 | 50 | 400 | 300 |

Additional checks:
- `references.bib` entry count ≥ 10 (topic-agnostic; agent targets ≥14)
- Missing figure file penalty capped at −20 total
- No `\begin{center}` at document level, no em dashes in Hebrew prose, no placeholder `\fbox` boxes

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
| VisualizationEngineer | DeepSeek V3 | 22 | CodeExecutor, SafeFileWriter, FileReader |
| HebrewAcademicWriter | DeepSeek V3 | 40 | FileReader, SafeFileWriter |
| LaTeXAuthor | DeepSeek V3 | 55 | SafeFileWriter, FileReader |

---

## 4. Content Strategy

Research is conducted entirely in English (Serper/ArXiv queries, research briefs, domain expert outputs). HebrewAcademicWriter converts the English content into Hebrew academic prose (800–1200 words per chapter). LaTeXAuthor wraps the prose in XeLaTeX — if `hebrew_prose.md` is missing or empty, it writes Hebrew content itself from `research_briefs.md`. All inline English in Hebrew prose is wrapped with `\en{}` to prevent bidi crashes.

---

## 5. Protected Files

| File | Reason |
|---|---|
| `main.tex` | Controls chapter order and XeLaTeX preamble |
| `cover.tex` | `\vspace{}` fix for bidi crash; student name/date |
| `src/config.py` | Runtime configuration |
| `.env`, `.gitignore`, `requirements.txt` | Project hygiene |

All content chapters (abstract, ch01–ch09) are **agent-written**. `cover.tex` is the only static chapter.

---

## 6. Run-Folder Architecture

Each run is **self-contained** in `outputs/runs/{topic-slug}-{YYYY-MM-DD}/` (versioned with `-v2`, `-v3`). Project-root `latex/` is a read-only template never modified during a run.

```
outputs/runs/{slug}-{date}/
  latex/
    chapters/   ← cover.tex (static) + 10 agent-written .tex files (abstract + ch01–ch09)
    figures/    ← fig_stub.png (pre-seeded) + agent-generated PNGs
    references.bib
    main.tex, IEEEtran.cls/bst
  outputs/      ← agent .md reports (moved from outputs/current/ on completion)
  paper.pdf     ← compiled PDF
  run_manifest.txt
```

Key functions:
- `setup_run_latex(run_folder)` — copies template; `fig_stub.png` is pre-seeded into figures/
- `compile_pdf(run_folder)` — auto-stubs any missing `\includegraphics` files with `fig_stub.png` before xelatex runs; 5 total passes (xelatex→bibtex→xelatex×3)
- `main.tex` uses `\IfFileExists` for every chapter — compilation never crashes on a missing file
- `finalize_run(run_folder)` — moves staging files, writes manifest

---

## 7. Figure Requirements

Exactly 9 figures per paper in full/fast mode, topic-determined via `paper_outline.md`:
- Minimum 300 DPI PNG
- Minimum font size 11pt for all text elements
- Wide figures use `figure*` float with `[width=\textwidth]`
- Single-column figures use `[width=0.98\columnwidth]`
- Labels prefixed with chapter ID: `\label{fig:ch02_name}`
- `figures_manifest.md` written by SafeFileWriterTool (output_file is `figures_status.md` to prevent CrewAI overwrite)
- Smoke mode: no figures agent — all chapters use `figures/fig_stub.png`

---

## 8. Success Criteria

| Criterion | Target |
|---|---|
| Paper length | 25–30 printed pages |
| Quality gate score | ≥ 75/100 |
| BibTeX entries | ≥ 10 in quality gate; agent targets ≥ 14 |
| LaTeX compilation | PDF > 0 bytes and openable |
| Cost per run | ≤ $0.14 (including worst-case remediation) |
| Execution | Unattended, no manual intervention |
