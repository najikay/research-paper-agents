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

Approximate total across all development and testing, June 7–12 2026.

| Category | Runs | Tokens (in) | Tokens (out) | Est. Cost |
|----------|------|-------------|-------------|-----------|
| Early dev runs (v5.0–v9, pre-run-folder) | ~8 | 800,000 | 560,000 | $0.83 |
| Archived full runs (v10–v13+) | ~20 | 4,000,000 | 3,000,000 | $4.38 |
| Smoke / fast / dry-run tests | ~12 | 120,000 | 70,000 | $0.11 |
| **Total pipeline** | **~40** | **~4,920,000** | **~3,630,000** | **~$5.32** |

> All runs use DeepSeek V3 at the prices listed above.

### Development tooling — Claude (via Claude Code)

Project code was built and iterated using Claude Code.

| Pricing | Input | Output |
|---------|-------|--------|
| Claude Sonnet 4.6 | $3.00 / 1M | $15.00 / 1M |

| Category | Sessions | Tokens (in) | Tokens (out) | Est. Cost |
|----------|----------|-------------|-------------|-----------|
| Architecture & scaffolding | ~3 | 300,000 | 60,000 | $1.80 |
| Agent development & debugging | ~4 | 500,000 | 100,000 | $3.00 |
| Sanitizer, quality gate, tests | ~3 | 400,000 | 80,000 | $2.40 |
| Threshold tuning & run analysis | ~2 | 100,000 | 20,000 | $0.60 |
| **Total development** | **~12** | **~1,300,000** | **~260,000** | **~$7.80** |

> Input tokens dominate because file context is re-read on each turn.
> Actual spend estimated in the $6–$10 range.

### Combined project total

| Component | Est. Tokens | Est. Cost |
|-----------|-------------|-----------|
| Pipeline runs (DeepSeek V3) | ~8,550,000 | ~$5.32 |
| Development tooling (Claude) | ~1,560,000 | ~$7.80 |
| **Grand total** | **~10,110,000** | **~$13.12** |

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
