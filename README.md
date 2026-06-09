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
  CrewAI Sequential Crew (10 agents, 11 tasks)
  ┌──────────────────────────────────────────────────────┐
  │   1. NavigationDirector    → paper_outline.md        │
  │   2. SLAMResearcher        → research_briefs.md      │
  │   3. VisionAIExpert        → domain_vision_ai.md     │
  │   4. PhysicsExpert         → domain_physics.md       │
  │   5. AlgorithmsExpert      → domain_algorithms.md    │
  │   6. AerospaceMarine Expert→ domain_aerospace.md     │
  │   7. BiologyExpert         → domain_biology.md       │
  │   8. VisualizationEngineer → 9 PNG figures           │
  │   9. HebrewAcademicWriter  → hebrew_prose.md         │
  │  10. LaTeXAuthor (part 1)  → abstract+ch02/03/05+bib │
  │  11. LaTeXAuthor (part 2)  → ch06/07/08/09+appendix  │
  └──────────────────────────────────────────────────────┘
        │
        ▼
  Programmatic quality gate (no LLM — deterministic)
        │
        ▼
  XeLaTeX compiler (xelatex → bibtex → xelatex × 3)
        │
        ▼
  outputs/runs/{slug}-{date}/paper.pdf
```

### Key Design Decisions

| Feature | Implementation |
|---|---|
| **Language separation** | Research in English → HebrewAcademicWriter → LaTeXAuthor (pure formatter) |
| **Domain experts** | 5 PhD-level specialists contribute depth; write "DOMAIN SKIP:" when irrelevant |
| **Split LaTeX task** | Part 1 (early chapters + bib) and Part 2 (later chapters + appendix) — each gets its own 40-iter budget |
| **Quality gate** | Programmatic checker in LangGraph node — no LLM, no loop risk |
| **Feedback loop** | LangGraph conditional edge: score < 75 → targeted remediation (max 2 cycles) |
| **Fault tolerance** | Every task writes an `output_file`; `--resume` skips completed tasks |
| **Run-folder architecture** | `outputs/runs/{slug}-{date}/` is single source of truth; project-root `latex/` is read-only template |
| **Cost** | DeepSeek V3 via OpenAI-compatible API (~$0.07/run) |
| **Bilingual LaTeX** | XeLaTeX + polyglossia + bidi; `bidi` loaded last; `\en{}` wraps all English in Hebrew prose |
| **Protected files** | `cover.tex`, `main.tex`, `ch01_intro.tex`, `ch04_slam.tex` blocked by basename matching |

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

# Full run — default topic
python main.py

# Custom topic
python main.py --topic "Autonomous Underwater Vehicle Navigation Using Acoustic SLAM and Bio-Inspired Sonar"

# Resume after crash (skips tasks with existing output files)
python main.py --topic "..." --resume

# Content only, no PDF compilation
python main.py --topic "..." --no-pdf

# Skip archiving (smoke tests / quick iterations)
python main.py --topic "..." --no-archive
```

### Output Layout

Each run is self-contained. The project-root `latex/` is a **read-only template** and is never modified during a run:

```
outputs/runs/
└── bat-inspired-drone-navigation-2026-06-08/   ← {topic-slug}-{date}
    ├── latex/                     ← primary LaTeX workspace (agents write here)
    │   ├── main.tex               ← PROTECTED
    │   ├── chapters/              ← cover + ch01 + ch04 (static) + 8 agent-written .tex
    │   ├── figures/               ← 9 agent-generated PNG figures (300 DPI)
    │   ├── references.bib         ← 14+ BibTeX entries (agent-written)
    │   ├── IEEEtran.cls / .bst
    │   └── main.log               ← XeLaTeX compile log
    ├── outputs/                   ← agent .md reports (moved from staging on completion)
    │   ├── paper_outline.md
    │   ├── research_briefs.md
    │   ├── domain_vision_ai.md    ← Vision-AI expert contribution (or "DOMAIN SKIP:")
    │   ├── domain_physics.md
    │   ├── domain_algorithms.md
    │   ├── domain_aerospace.md
    │   ├── domain_biology.md
    │   ├── hebrew_prose.md
    │   ├── figures_manifest.md
    │   ├── latex_status_part1.md
    │   ├── latex_status.md        ← part 2 final status
    │   ├── quality_report.md
    │   └── token_report.md
    ├── paper.pdf                  ← compiled IEEE paper
    └── run_manifest.txt           ← file index with figure listing
```

---

## Agents

| Agent | Model | Max Iter | Tools | Role |
|---|---|---|---|---|
| NavigationDirector | DeepSeek V3 | 12 | FileReader, FileWriter, Serper, ArXiv | Decomposes topic → 8 sub-domains with outline |
| SLAMResearcher | DeepSeek V3 | 18 | FileReader, Serper, ArXiv, WebScraper | English-language literature research per chapter |
| VisionAIExpert | DeepSeek V3 | 15 | FileReader, FileWriter, Serper, ArXiv | Visual SLAM, depth estimation, semantic perception |
| PhysicsExpert | DeepSeek V3 | 15 | FileReader, FileWriter, Serper, ArXiv | Acoustics, matched filter, Doppler, wave propagation |
| AlgorithmsExpert | DeepSeek V3 | 15 | FileReader, FileWriter, Serper, ArXiv | EKF/UKF/particle filters, factor graph SLAM, CRLB |
| AerospaceMarineExpert | DeepSeek V3 | 15 | FileReader, FileWriter, Serper, ArXiv | UAV dynamics, INS, AUV/submarine sonar, DVL |
| BiologyExpert | DeepSeek V3 | 15 | FileReader, FileWriter, Serper, ArXiv | Bat echolocation, DSC, neural computation, biosonar |
| VisualizationEngineer | DeepSeek V3 | 12 | CodeExecutor, FileWriter, FileReader | 9 IEEE-standard PNG figures via matplotlib |
| HebrewAcademicWriter | DeepSeek V3 | 35 | FileReader, FileWriter | English briefs + domain inputs → Hebrew prose (800-1200 words/chapter) |
| LaTeXAuthor | DeepSeek V3 | 40 | FileWriter, FileReader | Pure formatter: wraps Hebrew prose in XeLaTeX (split across 2 tasks) |

**Domain experts** each independently read the research briefs and contribute PhD-level content (equations, algorithms, references) in their specialty. If the topic has no intersection with their field they write `"DOMAIN SKIP: [reason]"` — downstream agents ignore those files.

**Quality gate** is programmatic (no LLM) — checks equation count (≥3), figure count (≥1), subsection count (≥3), citation count (≥2), word estimate (≥600), BibTeX key completeness (14 keys), and forbidden patterns. Deterministic, zero loop risk.

---

## Project Structure

```
.
├── main.py                    ← entry point; run setup; PDF compilation; finalize
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py              ← LLM init, PROTECTED_FILES, AGENT_MAX_ITER, logging
│   ├── crew.py                ← CrewAI assembly (10 agents, 11 tasks)
│   ├── agents/                ← factory function per agent (10 files)
│   │   ├── navigation_director.py
│   │   ├── slam_researcher.py
│   │   ├── vision_ai_expert.py
│   │   ├── physics_expert.py
│   │   ├── algorithms_expert.py
│   │   ├── aerospace_marine_expert.py
│   │   ├── biology_expert.py
│   │   ├── visualization_engineer.py
│   │   ├── hebrew_academic_writer.py
│   │   └── latex_author.py
│   ├── tasks/                 ← task factories (outline/research/domain/figures/prose/latex×2)
│   ├── tools/                 ← ArXiv, Serper, WebScraper, SafeFileWriter, CodeExecutor, FileReader
│   ├── graph/                 ← LangGraph state machine (state, nodes, graph)
│   └── utils/                 ← TokenAccountant
├── latex/                     ← READ-ONLY TEMPLATE (never modified during runs)
│   ├── main.tex               ← PROTECTED master document
│   ├── chapters/              ← cover.tex, ch01_intro.tex, ch04_slam.tex (all PROTECTED)
│   ├── figures/               ← empty; figures go to run_folder/latex/figures/
│   ├── references.bib         ← seed bibliography (14 required keys)
│   ├── IEEEtran.cls / .bst
├── outputs/
│   └── runs/                  ← per-run archives (gitignored)
├── tests/                     ← 132 tests across 11 files
└── docs/                      ← PLAN.md, PRD.md, TODO.md, BUDGET.md
```
