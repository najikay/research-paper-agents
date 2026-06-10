# Token Budget — NavigatorCrew

## Provider: DeepSeek V3 (`openai/deepseek-chat`)

| Tier       | Price (input) | Price (output) |
|------------|--------------|----------------|
| DeepSeek V3 | $0.27 / 1M   | $1.10 / 1M     |

---

## Per-Run Budget Estimate (v10 split pipeline)

| Phase / Agent            | Avg Input Tokens | Avg Output Tokens | Est. Cost |
|--------------------------|-----------------|-------------------|-----------|
| **Research Phase**       |                 |                   |           |
| ResearchDirector         | 3,000           | 2,000             | $0.003    |
| SLAMResearcher           | 15,000          | 8,000             | $0.013    |
| 8x Domain Experts        | 40,000          | 24,000            | $0.037    |
| **Writing Phase**        |                 |                   |           |
| VisualizationEng.        | 10,000          | 8,000             | $0.012    |
| HebrewAcademicWriter     | 20,000          | 25,000            | $0.033    |
| 3x LaTeXAuthor           | 45,000          | 50,000            | $0.067    |
| **Total per run**        | **~133,000**    | **~117,000**      | **~$0.16**|

> Quality gate and validation are programmatic — no LLM tokens used.

### Max-cost scenario (remediation x 3 loops)

| Component          | Extra Tokens          | Extra Cost |
|--------------------|-----------------------|------------|
| Remediation run 1  | ~25,000 in / ~20,000 out | ~$0.029 |
| Remediation run 2  | ~25,000 in / ~20,000 out | ~$0.029 |
| Remediation run 3  | ~25,000 in / ~20,000 out | ~$0.029 |
| **Max total**      | ~208,000 in / ~177,000 out | **~$0.25** |

---

## Budget Guardrails

Set in `.env`:
```
DEEPSEEK_API_KEY=sk-...
ACTIVE_PROVIDER=deepseek
```

Hard limits enforced in `src/config.py`:
- `AGENT_MAX_ITER` caps each agent's iteration count (12-40 depending on role)
- `MAX_REMEDIATIONS = 3` caps LangGraph feedback loops
- `max_tokens=8192` per LLM call

## Switching Providers

| Scenario           | Provider        | Change in .env              |
|--------------------|-----------------|-----------------------------|
| Normal runs        | DeepSeek V3     | `ACTIVE_PROVIDER=deepseek`  |
| Anthropic (backup) | Claude Haiku 4.5 | `ACTIVE_PROVIDER=anthropic` |
