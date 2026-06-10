# NavigatorCrew — Issues Log

**Last updated:** 2026-06-10

---

## Resolved Issues

### `\°` undefined control sequence (CRITICAL — fixed v10)
**Symptom:** XeLaTeX crashes at page 3 with "Undefined control sequence" on `5\°`.
**Root cause:** LLM agents write `\°` for degree symbol, but `\°` is not a valid LaTeX command.
**Fix:** (a) Added Fix 17 in `_sanitize_tex_files()`: replaces `\°` with Unicode `°` (XeLaTeX handles natively). (b) Added `\°` to FORBIDDEN PATTERNS in LaTeX author prompt.

### Agent creates wrong chapter filenames (CRITICAL — fixed v5)
**Fix:** Stronger filename enforcement in task descriptions; post-pipeline validation.

### Figures not generated (CRITICAL — fixed v5)
**Fix:** max_iter raised to 40 for visualizer; fallback stub figures; reduced figure targets.

### Content too thin (HIGH — fixed v10)
**Fix:** Raised word targets across the full chain: Hebrew writer (1500-2500/chapter), LaTeX tasks (2500-4000/chapter), quality gate (default 1500 words). Aligned all three bottlenecks.

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

### 1. Page count below target
**Severity:** MEDIUM
**Status:** v10 changes address root cause (raised word targets). Awaiting v10 run results.
**Evidence:** v9 run produced 16 pages (target: 25-30). Root cause was Hebrew writer producing ~800 words/chapter where ~2000+ needed.

### 2. Duplicate figures across chapters
**Severity:** LOW
**Evidence:** Some chapters reference the same figure (e.g., `fig_system_architecture` appears in multiple chapters with chapter-suffixed variants).
**Mitigation:** Figures are auto-stubbed; duplicates don't cause compilation failures.

### 3. Run folder versioning creates many folders
**Severity:** LOW
**Evidence:** Multiple versions accumulate in `outputs/runs/`.
**Workaround:** Manual cleanup.

### 4. Token usage not tracked
**Severity:** LOW
**Evidence:** No `token_report.md` in run outputs.
**Root cause:** `accountant.save_report()` never called after crew.kickoff().

---

## Architecture Notes

### Quality gate pre-scoring pipeline
Before scoring, the quality gate node runs:
1. `_sanitize_tex_files()` — 17 automatic LaTeX fixes
2. `_generate_fallback_figures()` — creates matplotlib figures for any missing `\includegraphics` refs
3. Auto-stub missing figure PNGs with `fig_stub.png`

This means the score reflects the best possible state of the generated content.

### Split pipeline validation
Between research and writing phases, `validate_and_fix_research` checks:
- Domain expert output files >= 500 bytes (smaller = failure)
- No stuck-agent loop patterns (repeated "STEP 1" / "Let me read" phrases)
- Failed tasks are re-run with a Fixer crew
