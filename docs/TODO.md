# NavigatorCrew — TODO

## Done

### Pipeline & Architecture
- [x] 13-agent CrewAI pipeline, split into research + writing phases
- [x] LangGraph state machine: research → validate → writing → quality gate → remediation → END
- [x] Research validation node (checks domain output sizes, detects stuck agents, re-runs failures)
- [x] Programmatic quality gate with per-chapter thresholds (calibrated from 3 runs)
- [x] `--resume`, `--no-pdf`, `--no-archive` flags
- [x] Run-folder architecture: each run self-contained in `outputs/runs/{slug}-{date}/`
- [x] `setup_run_latex()`, `compile_pdf()` (5 xelatex passes), `finalize_run()`

### Speed Modes
- [x] `--fast` mode: 5 agents, 6 tasks (skip domain experts), ~20-40 min
- [x] `--smoke` mode: 2 agents, 2 tasks (outline + latex-all), ~10-20 min
- [x] `--dry-run` mode: zero LLM calls (~5-30 sec), score 100/100

### Agents (13 total)
- [x] NavigationDirector, SLAMResearcher (core research)
- [x] 8 domain experts: VisionAI, Physics, Algorithms, AerospaceMarine, Biology, SignalProcessing, ControlSystems, ML
- [x] VisualizationEngineer (figure generation)
- [x] HebrewAcademicWriter (English research → Hebrew prose)
- [x] LaTeXAuthor x3 (A: abstract+ch01-ch03+bib, B: ch04-ch06, C: ch07-ch09)
- [x] All agents use DeepSeek V3; max_iter tuned per role
- [x] DOMAIN SKIP mechanism for irrelevant topics

### Content Depth
- [x] Hebrew writer per-chapter targets: 1500-2500 words
- [x] LaTeX author CONTENT DEPTH CONTRACT: 2500-4000 words per chapter
- [x] 3-split task targets aligned with shared rules (2500-4000)
- [x] Quality gate word thresholds calibrated to LLM output: default 1400, ch06/ch08 1800, ch07 1600, ch09 700

### LaTeX / Compilation
- [x] 25-fix sanitizer in `_sanitize_tex_files()`
- [x] Fix 20: Brace repair for truncated files (unclosed `{`)
- [x] Fix 21: Author-name commands (`\Au`, `\Thorp`) → `\en{}`
- [x] Fix 22: `\ensuremath{$\theta$}` nested math → `$\theta$` (brace-counting parser)
- [x] Fix 23: Stray `}` removal via brace-depth tracking
- [x] Fix 24: Auto-upgrade wide figures (`figure` → `figure*`) based on PNG aspect ratio
- [x] Fix 25: Extract math superscripts from `\en{}` (`\en{m/s^2}` → `\en{m/s}$^2$`)
- [x] Removed `-halt-on-error` — PDFs compile fully past non-fatal errors
- [x] `main.tex` `\IfFileExists` guards for all chapters
- [x] `fig_stub.png` pre-seeded; auto-stubbing of missing figures
- [x] Font fallback chain: hebrewfont, hebrewfonttt, hebrewfontsf, englishfont
- [x] LaTeX task 3-way split (Writers A/B/C)
- [x] Figure WIDTH rules: `figure*`+`\textwidth` for wide figs
- [x] Label uniqueness: chapter-prefix convention
- [x] `\en{}` wrapping for inline English
- [x] `cover.tex` bidi crash fixed
- [x] Only `cover.tex` is static; all 10 content files are agent-written

### Quality Gate & Remediation
- [x] `QUALITY_THRESHOLD` raised 75 → 90 (remediation fires more often)
- [x] `MAX_REMEDIATIONS` raised 3 → 4
- [x] Thresholds calibrated to LLM output: set ~10% below observed, stricter thresholds drive better remediation
- [x] Remediation prompt: reads references.bib, targets 400+ words/chapter expansion

### Tests
- [x] Test suite: 143 tests across agents, tasks, quality gate, config, tools, run archive, latex sources
- [x] Test fixtures updated for calibrated quality gate thresholds

---

## Active Targets

- [ ] Push page count to 25 pages (currently 23)
- [ ] Push score to 100/100 consistently (currently 96)

---

## Backlog

- [ ] Post-run `references.bib` key validator
- [ ] Token budget enforcement (abort if projected cost > threshold)
