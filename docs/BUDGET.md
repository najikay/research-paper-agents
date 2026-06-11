# Token Budget — NavigatorCrew

## Provider: DeepSeek V3 (`openai/deepseek-chat`)

| Tier       | Price (input) | Price (output) |
|------------|--------------|----------------|
| DeepSeek V3 | $0.27 / 1M   | $1.10 / 1M     |

---

## Per-Run Budget Estimate (v13 split pipeline, 13 agents)

| Phase / Agent            | Avg Input Tokens | Avg Output Tokens | Est. Cost |
|--------------------------|-----------------|-------------------|-----------|
| **Research Phase (10 agents)** |            |                   |           |
| NavigationDirector       | 5,000           | 2,000             | $0.004    |
| SLAMResearcher           | 20,000          | 10,000            | $0.016    |
| 8x Domain Experts        | 64,000          | 40,000            | $0.061    |
| **Writing Phase (5 agents)** |             |                   |           |
| VisualizationEngineer    | 15,000          | 12,000            | $0.017    |
| HebrewAcademicWriter     | 30,000          | 30,000            | $0.041    |
| 3x LaTeX Authors (A/B/C) | 60,000          | 54,000            | $0.076    |
| **Base total per run**   | **~194,000**    | **~148,000**      | **~$0.22**|

> Quality gate, validation, and sanitizer are programmatic — zero LLM tokens.

### With remediation (typical: 2-3 cycles)

| Component          | Extra Tokens          | Extra Cost |
|--------------------|-----------------------|------------|
| Per remediation cycle | ~30,000 in / ~25,000 out | ~$0.036 |
| Typical run (2 cycles) | ~254,000 in / ~198,000 out | **~$0.29** |
| Max run (4 cycles) | ~314,000 in / ~248,000 out | **~$0.36** |

---

## Total Project Token Spend (estimated)

Approximate total across all development and testing, June 7–11 2026.

| Category | Runs | Tokens (in) | Tokens (out) | Est. Cost |
|----------|------|-------------|-------------|-----------|
| Early dev runs (v5.0–v9, pre-run-folder) | ~5 | 500,000 | 350,000 | $0.52 |
| Archived full runs (v10–v13) | 7 | 1,400,000 | 1,050,000 | $1.53 |
| Smoke / fast / dry-run tests | ~8 | 80,000 | 50,000 | $0.08 |
| **Total pipeline (conservative)** | **~20** | **~2,000,000** | **~1,450,000** | **~$2.13** |

> This is a conservative (modest) estimate. Early dev runs used fewer agents (5–8) and
> shorter prompts; later v13 runs use 13 agents with remediation. Actual spend is likely
> in the $1.50–$3.00 range. All runs use DeepSeek V3 at the prices listed above.

### Development tooling — Claude Sonnet 4.6 (via Claude Code)

All project code was built, debugged, and iterated using Claude Code powered by Sonnet 4.6.

| Pricing | Input | Output |
|---------|-------|--------|
| Claude Sonnet 4.6 | $3.00 / 1M | $15.00 / 1M |

| Category | Sessions | Tokens (in) | Tokens (out) | Est. Cost |
|----------|----------|-------------|-------------|-----------|
| Architecture & scaffolding (v5.0) | ~3 | 900,000 | 180,000 | $5.40 |
| Agent development & debugging (v5–v10) | ~5 | 1,500,000 | 300,000 | $9.00 |
| Sanitizer, quality gate, tests (v10–v13) | ~4 | 1,200,000 | 250,000 | $7.35 |
| Threshold tuning & run analysis | ~3 | 600,000 | 120,000 | $3.60 |
| **Total development (conservative)** | **~15** | **~4,200,000** | **~850,000** | **~$25.35** |

> Each Claude Code session involves heavy file reads (context), tool results, and iterative
> code generation. Input tokens dominate because the full file context is re-read on each
> turn. Estimate assumes average ~280K input / ~57K output per session across 15 sessions
> over 5 days (June 7–11). Actual spend likely in the $20–$35 range.

### Combined project total

| Component | Est. Tokens | Est. Cost |
|-----------|-------------|-----------|
| Pipeline runs (DeepSeek V3) | ~3,450,000 | ~$2.13 |
| Development tooling (Sonnet 4.6) | ~5,050,000 | ~$25.35 |
| **Grand total** | **~8,500,000** | **~$27.48** |

---

## Budget Guardrails

Set in `.env`:
```
DEEPSEEK_API_KEY=sk-...
ACTIVE_PROVIDER=deepseek
```

Hard limits enforced in `src/config.py`:
- `AGENT_MAX_ITER` caps each agent's iteration count (12–40 depending on role)
- `MAX_REMEDIATIONS = 4` caps LangGraph feedback loops
- `QUALITY_THRESHOLD = 90` — score below this triggers remediation
- `max_tokens=16384` per LLM call (DeepSeek V3)

## Switching Providers

| Scenario           | Provider        | Change in .env              |
|--------------------|-----------------|-----------------------------|
| Normal runs        | DeepSeek V3     | `ACTIVE_PROVIDER=deepseek`  |
| Anthropic (backup) | Claude Haiku 4.5 | `ACTIVE_PROVIDER=anthropic` |
