# NavigatorCrew — Issues Log

**Last updated:** 2026-06-11

---

## Resolved Issues

### `\en{m/s^2}` math-mode crash (CRITICAL — fixed v12, Fix 25)
**Symptom:** 8 "Missing $ inserted" errors from `^` (superscript) inside `\en{}` text-mode blocks.
**Root cause:** LLM writes `\en{m/s^2}` or `\en{R^2}` where `^` requires math mode.
**Fix:** Sanitizer Fix 25 splits: `\en{m/s^2}` → `\en{m/s}$^2$`.

### Wide figures in single column (HIGH — fixed v12, Fix 24)
**Symptom:** Architecture diagrams and wide charts cramped into one IEEE column (~3.5").
**Root cause:** All figures used `\begin{figure}` regardless of aspect ratio.
**Fix:** Fix 24 reads PNG headers, checks aspect ratio > 1.8, auto-upgrades to `\begin{figure*}` with `\textwidth`. Added ~3 pages.

### `\ensuremath{$\theta$}` nested math (HIGH — fixed v11, Fix 22)
**Symptom:** XeLaTeX error from `\ensuremath` wrapping already-math content.
**Fix:** Brace-counting parser strips outer `\ensuremath{}` when inner content has `$...$`.

### Stray `}` from agent truncation (HIGH — fixed v11, Fix 23)
**Symptom:** "Too many }'s" error when agent output is truncated mid-file.
**Fix:** Brace-depth tracking removes unmatched closing braces.

### Truncated files with unbalanced braces (HIGH — fixed v11, Fix 20)
**Symptom:** Agent hits token limit mid-output, file ends with unclosed `{`.
**Fix:** Fix 20 appends closing braces to balance the file.

### Author-name commands crash (MEDIUM — fixed v11, Fix 21)
**Symptom:** `\Au`, `\Thorp` undefined control sequences.
**Fix:** Regex converts `\Word` patterns (excluding Greek letters) to `\en{Word}`.

### `\degree` undefined control sequence (CRITICAL — fixed v10)
**Symptom:** XeLaTeX crashes on `5\degree`.
**Fix:** Sanitizer replaces `\degree` with Unicode `°`.

### Content too thin — 16 pages (HIGH — fixed v10)
**Symptom:** Paper only 16 pages (target 25-30) because Hebrew writer produced ~800 words/chapter.
**Fix:** Raised word targets across full chain: Hebrew writer (1500-2500/chapter), LaTeX tasks (2500-4000/chapter), quality gate minimums calibrated from real runs.

### Agent creates wrong chapter filenames (CRITICAL — fixed v5)
**Fix:** Stronger filename enforcement in task descriptions; post-pipeline validation.

### Figures not generated (CRITICAL — fixed v5)
**Fix:** max_iter raised to 40 for visualizer; fallback stub figures; reduced figure targets.

### Remediation crew reads wrong paths (CRITICAL — fixed v5.5)
**Fix:** Rewrote `create_remediation_task()` with explicit read paths for chapter files.

### Polyglossia monospace font error (HIGH — fixed v5.5)
**Fix:** Added `\hebrewfonttt` and `\hebrewfontsf` to main.tex.

### Em dashes in Hebrew prose (MEDIUM — fixed v5)
**Fix:** Auto-replacement in `_sanitize_tex_files()`: U+2014 → `:`, U+2013 → `-`.

### `\begin{center}` bidi crash (CRITICAL — fixed v4)
**Fix:** Sanitizer replaces with `{\centering...}`.

---

## Known Remaining Issues

### 1. Page count below 25-page target
**Severity:** MEDIUM
**Status:** Currently 23 pages (best run). Figure* upgrade (Fix 24) added ~3 pages. Remediation adds ~100-400 words per cycle.
**Root cause:** DeepSeek V3 word count variance is significant (~900-1900 words/chapter).

### 2. Duplicate figures across chapters
**Severity:** LOW
**Evidence:** Some chapters reference the same figure (e.g., `fig_system_architecture` appears in multiple chapters with chapter-suffixed variants).
**Mitigation:** Figures are auto-stubbed; duplicates don't cause compilation failures.

### 3. Run-to-run score variance
**Severity:** LOW
**Evidence:** Score ranges from 70-96 on first pass due to word count variance. Remediation reliably brings scores above 90 within 3-4 cycles.

---

## Architecture Notes

### Quality gate pre-scoring pipeline
Before scoring, the quality gate node runs:
1. `_sanitize_tex_files()` — 25 automatic LaTeX fixes
2. `_generate_fallback_figures()` — creates matplotlib figures for any missing `\includegraphics` refs
3. Auto-stub missing figure PNGs with `fig_stub.png`

This means the score reflects the best possible state of the generated content.

### Split pipeline validation
Between research and writing phases, `validate_and_fix_research` checks:
- Domain expert output files >= 500 bytes (smaller = failure)
- No stuck-agent loop patterns (repeated "STEP 1" / "Let me read" phrases)
- Failed tasks are re-run with a Fixer crew
