# Product Requirements Document — NavigatorCrew
**Version**: 5.1 | **Date**: 2026-06-08

---

## 1. Summary

NavigatorCrew is an autonomous multi-agent system that takes a research topic as input and produces a complete, compiled IEEE-formatted bilingual (Hebrew/English) academic paper. It is built on CrewAI v1.14+ (sequential process) wrapped in a LangGraph state machine with a programmatic quality gate and automatic run archiving.

---

## 2. Pipeline Architecture

```
main.py --topic "..."
  └─► LangGraph state machine
        ├─ run_main_pipeline   → 5-agent CrewAI crew (sequential)
        ├─ run_quality_gate    → programmatic checker (no LLM)
        ├─ run_remediation     → targeted fix crew (max 2 cycles)
        └─ END                 → XeLaTeX compile + run archive
```

### CrewAI Sequential Pipeline

| # | Agent | Input | Output |
|---|---|---|---|
| 1 | NavigationDirector | `--topic` | `outputs/paper_outline.md` |
| 2 | SLAMResearcher | outline | `outputs/research_briefs.md` |
| 3 | VisualizationEngineer | briefs | `latex/figures/*.png` + `outputs/figures_manifest.md` |
| 4 | HebrewAcademicWriter | briefs | `outputs/hebrew_prose.md` |
| 5 | LaTeXAuthor | prose + figures | `latex/chapters/*.tex` + `latex/references.bib` + `outputs/latex_status.md` |

### Quality Gate (programmatic, in LangGraph node)

Checks per chapter file:
- Equation count ≥ 2
- Figure count ≥ 1
- Subsection count ≥ 3
- Word estimate ≥ 300
- Citation count ≥ 2
- All 14 required BibTeX keys present in `references.bib`
- No forbidden patterns: `\begin{center}` at document level, em dashes in Hebrew prose, placeholder `\fbox` boxes

Score < 75 → FAIL → remediation crew (max 2 cycles) → re-check.

---

## 3. Agents

| Agent | Model | Max Iter | Tools |
|---|---|---|---|
| NavigationDirector | DeepSeek V3 | 12 | SafeFileWriter |
| SLAMResearcher | DeepSeek V3 | 18 | Serper, ArXiv, WebScraper |
| VisualizationEngineer | DeepSeek V3 | 12 | CodeExecutor, SafeFileWriter |
| HebrewAcademicWriter | DeepSeek V3 | 20 | FileReader, SafeFileWriter |
| LaTeXAuthor | DeepSeek V3 | 25 | SafeFileWriter, FileReader |

---

## 4. Language Separation

Research is conducted entirely in English (Serper/ArXiv queries, research briefs). A dedicated HebrewAcademicWriter converts the English briefs into polished Hebrew academic prose, preserving English technical terms by judgment (not a hardcoded list — the same way a Technion professor writes). LaTeXAuthor is a pure formatter: it wraps pre-written Hebrew prose in XeLaTeX environments without translating or paraphrasing.

---

## 5. Protected Files

The following files are blocked from agent writes in `SafeFileWriterTool`:

| File | Reason |
|---|---|
| `latex/main.tex` | Controls chapter order and XeLaTeX preamble |
| `latex/chapters/cover.tex` | `\\[len]` fix for bidi crash; student name/date |
| `latex/chapters/ch01_intro.tex` | Static intro with fixed citation keys |
| `latex/chapters/ch04_slam.tex` | Static SLAM chapter with fixed citation keys |
| `src/config.py` | Runtime configuration |
| `.env`, `.gitignore`, `requirements.txt` | Project hygiene |

---

## 6. Run Archiving

Each run is saved to `outputs/runs/{topic-slug}-{YYYY-MM-DD}/` (versioned with `-v2`, `-v3` on same date). Archive contains:
- `figures/` — PNG figures for direct access
- `outputs/` — all agent .md reports
- `latex/` — full LaTeX source snapshot
- `paper.pdf` — compiled PDF
- `run_manifest.txt` — file index

---

## 7. Success Criteria

| Criterion | Target |
|---|---|
| Paper length | 25–30 printed A4 pages |
| Quality gate score | ≥ 75/100 |
| Required BibTeX keys | All 14 present |
| LaTeX compilation | xelatex exits 0, no `!` errors |
| Cost per run | ≤ $0.14 (including worst-case remediation) |
| Execution | Unattended, no manual intervention |
