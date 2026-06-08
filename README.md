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
  CrewAI Sequential Crew
  ┌──────────────────────────────────────────────┐
  │  1. NavigationDirector  → paper_outline.md   │
  │  2. SLAMResearcher      → research_briefs.md │
  │  3. VisualizationEngineer → 9 PNG figures    │
  │  4. HebrewAcademicWriter → hebrew_prose.md   │
  │  5. LaTeXAuthor         → .tex chapters + .bib│
  └──────────────────────────────────────────────┘
        │
        ▼
  Programmatic quality gate (no LLM — deterministic)
        │
        ▼
  XeLaTeX compiler (xelatex → bibtex → xelatex × 2)
        │
        ▼
  outputs/runs/{slug}-{date}/paper.pdf
```

### Key Design Decisions

| Feature | Implementation |
|---|---|
| **Language separation** | Research in English → HebrewAcademicWriter → LaTeXAuthor (pure formatter) |
| **Quality gate** | Programmatic checker in LangGraph node — no LLM, no loop risk |
| **Feedback loop** | LangGraph conditional edge: score < 75 → targeted remediation (max 2 cycles) |
| **Fault tolerance** | Every task writes an `output_file`; `--resume` skips completed tasks |
| **Run archiving** | Each run gets its own folder in `outputs/runs/` with figures, LaTeX source, and PDF |
| **Cost** | DeepSeek V3 via OpenAI-compatible API (~$0.07/run) |
| **Bilingual LaTeX** | XeLaTeX + polyglossia + bidi; `bidi` must be loaded last; `\\[len]` → `\vspace{}` |
| **Protected files** | `cover.tex`, `main.tex`, `ch01_intro.tex`, `ch04_slam.tex` blocked from agent writes |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- XeLaTeX: `sudo apt install texlive-xetex texlive-lang-other`

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
# Edit .env with your keys
```

```env
DEEPSEEK_API_KEY=sk-...     # platform.deepseek.com
ACTIVE_PROVIDER=deepseek
SERPER_API_KEY=...          # free at serper.dev
```

### 4. Install bidi (first time only)

```bash
tlmgr init-usertree
tlmgr --repository http://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2023/tlnet-final install bidi
```

Register Windows fonts with fontconfig (WSL only):

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

# Content only, no PDF compilation
python main.py --topic "..." --no-pdf

# Skip archiving (smoke tests / quick iterations)
python main.py --topic "..." --no-archive
```

### Output Layout

Each run is automatically archived to a uniquely-named folder:

```
outputs/runs/
└── bat-inspired-drone-navigation-2026-06-08/   ← {topic-slug}-{date}
    ├── figures/                   ← 9 PNG figures (300 DPI) — direct access
    │   ├── fig_bat_sonar.png
    │   └── ...
    ├── outputs/                   ← agent reports
    │   ├── paper_outline.md       ← Director's topic decomposition
    │   ├── research_briefs.md     ← Researcher's English-language findings
    │   ├── hebrew_prose.md        ← HebrewAcademicWriter prose (pre-LaTeX)
    │   ├── figures_manifest.md    ← figure descriptions and PNG paths
    │   ├── latex_status.md        ← LaTeXAuthor completion status
    │   ├── quality_report.md      ← programmatic gate verdict (JSON)
    │   └── token_report.md        ← per-agent cost accounting
    ├── latex/                     ← full LaTeX source snapshot
    │   ├── main.tex
    │   ├── chapters/              ← cover + abstract + 9 chapter .tex files
    │   ├── figures/               ← same PNGs as top-level figures/
    │   └── references.bib         ← 14+ BibTeX entries
    ├── paper.pdf                  ← compiled IEEE paper
    └── run_manifest.txt           ← index of all archived files

# Duplicate dates get versioned automatically:
└── bat-inspired-drone-navigation-2026-06-08-v2/
```

> `outputs/runs/` is excluded from git — archives are local only.

---

## Agents

| Agent | Model | Tools | Role |
|---|---|---|---|
| NavigationDirector | DeepSeek V3 | FileWriter | Decomposes topic → 8 sub-domains; writes outline with English search keywords |
| SLAMResearcher | DeepSeek V3 | Serper, ArXiv, WebScraper | English-language literature research; produces structured briefs per chapter |
| VisualizationEngineer | DeepSeek V3 | CodeExecutor, FileWriter | Generates 9 IEEE-standard PNG figures via matplotlib |
| HebrewAcademicWriter | DeepSeek V3 | FileReader, FileWriter | Converts English briefs → polished Hebrew academic prose; preserves English technical terms by judgment |
| LaTeXAuthor | DeepSeek V3 | FileWriter, FileReader | Pure formatter: wraps Hebrew prose in XeLaTeX environments; inserts equations, figures, tables |

**Quality gate** is programmatic (no LLM) — checks equation count, figure count, BibTeX key completeness, forbidden patterns (`\begin{center}`, em dashes, placeholders), and word count per chapter. Deterministic, zero loop risk.

---

## Originality Contribution: AF-AFC Controller

The paper's central original contribution, derived from the biology of *Rhinolophus ferrumequinum* (horseshoe bats):

> Horseshoe bats lower their emission frequency by exactly the expected Doppler shift so the echo always lands at their cochlear "acoustic fovea" — a hyperacuity zone covering 30% of the basilar membrane tuned to 83 kHz.

We translate this into a closed-loop drone sonar controller:

$$f_{e,k}(t) = f_0\!\left(1 - \frac{2\hat{v}_{r,k}(t)}{c}\right) + K_p\varepsilon_k(t) + K_i\int_0^t \varepsilon_k(\tau)\,d\tau$$

where $\hat{v}_{r,k}$ comes from the EKF posterior and $\varepsilon_k$ is the foveal error (echo frequency deviation from $f_0$). This eliminates Doppler smearing in range resolution without sacrificing velocity measurement.

---

## Cost

| Provider | Model | Estimated Cost per Run |
|---|---|---|
| DeepSeek V3 | deepseek-chat | ~$0.07 |
| DeepSeek V3 (with 2 remediation cycles) | deepseek-chat | ~$0.14 max |

---

## Project Structure

```
.
├── main.py                    ← entry point; run archiving; PDF compilation
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py              ← LLM init, PROTECTED_FILES, logging
│   ├── crew.py                ← CrewAI assembly (5 agents, 5 tasks)
│   ├── agents/                ← factory functions for each agent
│   ├── tasks/                 ← task factories (outline/research/figures/prose/latex)
│   ├── tools/                 ← ArXiv, Serper, WebScraper, SafeFileWriter, CodeExecutor
│   ├── graph/                 ← LangGraph state machine (state, nodes, graph)
│   └── utils/                 ← TokenAccountant
├── latex/
│   ├── main.tex               ← PROTECTED master document
│   ├── chapters/              ← cover.tex (PROTECTED), ch01_intro.tex (PROTECTED),
│   │                             ch04_slam.tex (PROTECTED), + agent-written chapters
│   ├── figures/               ← agent-generated PNG figures
│   ├── references.bib         ← agent-generated bibliography
│   ├── IEEEtran.cls
│   └── IEEEtran.bst
├── outputs/
│   └── runs/                  ← per-run archives (gitignored)
└── docs/                      ← PLAN.md, PRD.md, TODO.md, BUDGET.md
```
