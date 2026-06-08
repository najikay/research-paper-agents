# NavigatorCrew

An autonomous multi-agent research platform that takes a `--topic` argument and produces a complete, compiled IEEE-formatted academic paper in XeLaTeX (Hebrew/English bilingual).

Built for Assignment 3 — *Orchestration of AI Agents*, Semester B 2026.

---

## Architecture

```
main.py --topic "..."
        │
        ▼
┌─────────────────────────────────────────────┐
│           LangGraph State Machine           │
│                                             │
│  [run_main_pipeline]                        │
│         │                                   │
│         ▼                                   │
│  [run_quality_gate] ──PASS──► [END]         │
│         │                                   │
│        FAIL                                 │
│         ▼                                   │
│  [run_remediation] ──────────► [run_quality_gate]
│         (max 2 cycles)                      │
└─────────────────────────────────────────────┘
        │
        ▼
  CrewAI Sequential Crew (inside each node)
  ┌──────────────────────────────────────────┐
  │  1. NavigationDirector   → paper_outline │
  │  2. SLAMResearcher       → research_briefs│
  │  3. VisualizationEngineer → 9 PNG figures │
  │  4. LaTeXAuthor          → .tex + .bib   │
  │  5. QualityEditor        → quality_report│
  └──────────────────────────────────────────┘
        │
        ▼
  XeLaTeX compiler (automatic)
        │
        ▼
  outputs/NavigatorCrew_paper.pdf
```

### Key Design Decisions

| Feature | Implementation |
|---|---|
| **Feedback loop** | LangGraph conditional edge: quality score < 75 → targeted remediation sub-crew |
| **Fault tolerance** | Every task writes an `output_file`; `--resume` skips completed tasks |
| **Cost optimization** | DeepSeek V3 (~$0.03/full run vs ~$3+ with GPT-4) |
| **Strict tools fix** | Patched `crewai/utilities/agent_utils.py` — hardcoded `strict: True` → `False` |
| **Bilingual LaTeX** | XeLaTeX + polyglossia + bidi; correct package load order (bidi must be last) |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- XeLaTeX: `sudo apt install texlive-xetex texlive-lang-other`
- bidi (installed automatically via `make setup` or `tlmgr`)

### 2. Install

```bash
git clone https://github.com/najikay/crewai-latex-project
cd crewai-latex-project
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
cp .env.example .env
# Edit .env:
```

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...     # or leave blank if using DeepSeek
SERPER_API_KEY=...               # free at serper.dev

# DeepSeek (recommended — much cheaper, fully compatible)
DEEPSEEK_API_KEY=sk-...          # get at platform.deepseek.com
ACTIVE_PROVIDER=deepseek         # switch: "anthropic" | "deepseek"
```

### 4. Install bidi (first time only)

```bash
tlmgr init-usertree
tlmgr --repository http://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2023/tlnet-final install bidi
```

And register Windows fonts with fontconfig (WSL only):

```bash
mkdir -p ~/.config/fontconfig
cat > ~/.config/fontconfig/fonts.conf << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>/mnt/c/Windows/Fonts</dir>
</fontconfig>
EOF
fc-cache -f ~/.config/fontconfig
```

---

## Usage

```bash
source venv/bin/activate

# Full run — generates content + compiles PDF + archives to outputs/runs/
python main.py --topic "Bat-Inspired Drone Navigation via Bio-Mimetic Sensor Fusion"

# Resume after crash (skips tasks with existing output files)
python main.py --topic "..." --resume

# Content only, skip PDF compilation
python main.py --topic "..." --no-pdf

# Skip archiving (smoke tests)
python main.py --topic "..." --no-archive
```

### Output Layout

Each run is automatically archived to a uniquely-named folder:

```
outputs/runs/
└── bat-inspired-drone-navigation-2026-06-08/   ← {topic-slug}-{date}
    ├── outputs/
    │   ├── paper_outline.md       ← Director's topic decomposition
    │   ├── research_briefs.md     ← Researcher's English-language findings
    │   ├── hebrew_prose.md        ← HebrewAcademicWriter prose (pre-LaTeX)
    │   ├── figures_manifest.md    ← figure descriptions and PNG paths
    │   ├── quality_report.md      ← programmatic gate verdict (JSON)
    │   └── token_report.md        ← per-agent cost accounting
    ├── latex/                     ← full LaTeX source snapshot
    │   ├── main.tex
    │   ├── chapters/              ← abstract + cover + 8 chapter files
    │   ├── figures/               ← 9 PNG figures (300 DPI)
    │   └── references.bib         ← 14 BibTeX entries
    ├── paper.pdf                  ← compiled IEEE paper
    └── run_manifest.txt           ← human-readable file index

# If same date already exists, the next run gets -v2, -v3, etc.:
└── bat-inspired-drone-navigation-2026-06-08-v2/
```

> `outputs/runs/` is excluded from git — archives are local only.

---

## Agents

| Agent | Model | Tools | Role |
|---|---|---|---|
| NavigationDirector | DeepSeek V3 | FileWriter | Decomposes topic → 8 sub-domains, writes outline with English search keywords |
| SLAMResearcher | DeepSeek V3 | Serper, ArXiv, WebScraper | Deep English-language literature research, produces structured briefs |
| VisualizationEngineer | DeepSeek V3 | CodeExecutor, FileWriter | Generates 9 IEEE-standard figures via matplotlib |
| HebrewAcademicWriter | DeepSeek V3 | FileReader, FileWriter | Converts English briefs → polished Hebrew academic prose; preserves English technical terms by judgment |
| LaTeXAuthor | DeepSeek V3 | FileWriter, FileReader | Pure formatter: wraps pre-written Hebrew prose in XeLaTeX environments, inserts equations/figures/tables |

> **Quality gate** is programmatic (no LLM agent) — checks equation count, figure count, BibTeX key completeness, forbidden patterns, and word estimates per chapter. Deterministic, zero loop risk.

---

## Originality Contributions

### AF-AFC Controller (Acoustic Fovea — Adaptive Frequency Controller)

The paper's central original contribution, derived from the biology of *Rhinolophus ferrumequinum* (horseshoe bats):

> Horseshoe bats lower their emission frequency by exactly the expected Doppler shift so the echo always lands at their cochlear "acoustic fovea" — a hyperacuity zone covering 30% of the basilar membrane tuned to 83 kHz.

We translate this into a closed-loop drone sonar controller:

$$f_{e,k}(t) = f_0\!\left(1 - \frac{2\hat{v}_{r,k}(t)}{c}\right) + K_p\varepsilon_k(t) + K_i\int_0^t \varepsilon_k(\tau)\,d\tau$$

where $\hat{v}_{r,k}$ comes from the EKF posterior and $\varepsilon_k$ is the foveal error (echo frequency deviation from $f_0$). This eliminates Doppler smearing in range resolution without sacrificing velocity measurement.

---

## Cost

| Provider | Model | Full Run Cost |
|---|---|---|
| DeepSeek V3 | deepseek-chat | ~$0.07 |

---

## Project Structure

```
.
├── main.py                    ← entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py              ← LLM init, model switching, logging
│   ├── crew.py                ← CrewAI assembly
│   ├── agents/                ← 5 agent factory functions
│   ├── tasks/                 ← task factories + remediation task
│   ├── tools/                 ← ArXiv, Serper, WebScraper, FileWriter, CodeExecutor
│   ├── graph/                 ← LangGraph state machine (state, nodes, graph)
│   └── utils/                 ← TokenAccountant
├── latex/                     ← generated LaTeX source + figures
├── outputs/                   ← generated research artifacts + final PDF
├── docs/                      ← PLAN.md, PRD.md, TODO.md
└── tests/                     ← agent and tool unit tests
```
