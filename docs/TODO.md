# NavigatorCrew — TODO

## Done ✅

### Pipeline
- [x] 5-agent CrewAI sequential crew (Director → Researcher → Visualizer → HebrewWriter → LaTeXAuthor)
- [x] LangGraph state machine (main pipeline → quality gate → remediation → END)
- [x] Programmatic quality gate (replaces infinite-loop LLM reviewer)
- [x] `--resume` flag: task-level checkpointing via `output_file`
- [x] `--no-pdf` flag for content-only runs
- [x] `--no-archive` flag for smoke tests
- [x] Run archiving: `outputs/runs/{slug}-{date}/` with figures/, outputs/, latex/, paper.pdf

### Agents
- [x] HebrewAcademicWriter agent (language separation: English research → Hebrew prose)
- [x] LaTeXAuthor simplified to pure formatter (no translation)
- [x] Researcher forced to search in English (Serper/ArXiv queries)
- [x] All agents use DeepSeek V3

### LaTeX / Compilation
- [x] `cover.tex` bidi crash fixed: `\\[length]` → `\vspace{}` throughout
- [x] `main.tex` restored: ch0X_ naming, cover.tex + abstract.tex included
- [x] Stale `chapter0X_*.tex` duplicates deleted
- [x] PROTECTED_FILES blocks agent writes to cover.tex, main.tex, ch01, ch04, config.py
- [x] SafeFileWriterTool checks both basename and relative path
- [x] Required 14 BibTeX keys baked into agent prompt and task description
- [x] Em dash prohibition in LaTeXAuthor goal
- [x] Package load order: fontspec → polyglossia → bidi (last)
- [x] `references.bib` overwrite bug fixed: latex task `output_file` → `outputs/latex_status.md`; agent now instructed to write bib via SafeFileWriterTool
- [x] `\textenglish` hyperref crash fixed: `\newcommand{\en}` now uses `\texorpdfstring`
- [x] PDF no longer copied to `outputs/`; `compile_pdf()` returns `latex/main.pdf` directly for archive
- [x] Stale `outputs/runs/` folder and loose `.md`/`.pdf` files deleted before clean run

### Configuration
- [x] DeepSeek V3 as sole provider (Anthropic removed from .env.example)
- [x] Provider-aware `validate_config()` (only checks DEEPSEEK_API_KEY)
- [x] `outputs/NavigatorCrew_paper.pdf` removed from git tracking

### Docs
- [x] README reflects v5.1 architecture, 5-agent crew, run archive layout
- [x] PRD updated to v5.1
- [x] PLAN updated to v5.1

## Next Run Targets 🎯

- [ ] Paper compiles without xelatex errors
- [ ] Paper reaches 25–30 pages
- [ ] Quality gate score ≥ 75 (was 18 — root causes fixed in this session)
- [ ] references.bib has all 14 required keys (protected from overwrite now)
- [ ] All chapter .tex files pass structural checks (≥ 600 words, ≥ 4 subsections, ≥ 3 equations)
- [ ] Push to GitHub

## Backlog

- [ ] ArXiv tool for researcher (real citations)
- [ ] Post-run references.bib key validator (belt-and-suspenders guard)
- [ ] Token budget enforcement (abort if cost projected > threshold)
- [ ] Evaluate adding domain-expert agents (physics prof, CS prof, AI engineering prof) — adds depth but increases cost and latency
