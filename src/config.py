"""
src/config.py
=============
Central configuration module for ResearchCrew.

Responsibilities:
  - Load all environment variables from .env
  - Expose typed constants used across the project
  - Validate that required API keys are present at startup
  - Configure structured logging (loguru) for the whole application
  - Provide the ChromaDB embedder config with an OpenAI/HuggingFace fallback

Usage:
  from src.config import MODEL_NAME, LATEX_DIR, validate_config
  validate_config()   # call once at the entry point (main.py / app.py)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# 1. Load .env  (safe to call multiple times — dotenv is idempotent)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# 2. Resolve project paths  (all relative paths are anchored here)
# ---------------------------------------------------------------------------
# config.py lives at:  <project_root>/src/config.py
# So PROJECT_ROOT  is:  <project_root>/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

SRC_DIR:     Path = PROJECT_ROOT / "src"
LATEX_DIR:   Path = PROJECT_ROOT / "latex"
FIGURES_DIR: Path = LATEX_DIR / "figures"
CHAPTERS_DIR: Path = LATEX_DIR / "chapters"
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
DOCS_DIR:    Path = PROJECT_ROOT / "docs"
TESTS_DIR:   Path = PROJECT_ROOT / "tests"

# Ensure critical output directories exist at import time
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 3. API Keys  (read from environment — NEVER hardcode values here)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
SERPER_API_KEY:    str = os.getenv("SERPER_API_KEY", "")
OPENAI_API_KEY:    str = os.getenv("OPENAI_API_KEY", "")

# If OPENAI_API_KEY is a placeholder (not a real key), remove it from the
# process environment entirely so CrewAI's internal subsystems (memory.analyze,
# etc.) cannot accidentally pick it up and make failing API calls.
if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("sk-"):
    os.environ.pop("OPENAI_API_KEY", None)
    OPENAI_API_KEY = ""

# ---------------------------------------------------------------------------
# 4. Model Constants & LLM Initialization
# ---------------------------------------------------------------------------
from crewai import LLM as CrewLLM

# ---------------------------------------------------------------------------
# MODEL PROVIDER SWITCH
# Set ACTIVE_PROVIDER to "anthropic" or "deepseek".
# DeepSeek is OpenAI-compatible, very cheap (~$0.27/M input), and highly capable.
# To use DeepSeek: set DEEPSEEK_API_KEY in .env, set ACTIVE_PROVIDER="deepseek"
# ---------------------------------------------------------------------------
ACTIVE_PROVIDER: str = os.getenv("ACTIVE_PROVIDER", "anthropic")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

if ACTIVE_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
    # DeepSeek V3 — GPT-4 class quality, ~$0.27/M input tokens
    # Uses OpenAI-compatible API. CrewAI routes via "openai/" provider + base_url override.
    # Both tiers share the same model — DeepSeek is cheap enough not to need tiering.
    _DS_KWARGS = dict(
        model="openai/deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        max_tokens=16384,  # DeepSeek V3 supports up to 64K; 8K was too small for full chapters
    )
    SONNET_LLM: CrewLLM = CrewLLM(**_DS_KWARGS, temperature=0.3)
    HAIKU_LLM:  CrewLLM = CrewLLM(**_DS_KWARGS, temperature=0.1)
    MODEL_NAME: str = "openai/deepseek-chat"
else:
    # Anthropic — Sonnet quota blown, use Haiku for ALL agents.
    # Haiku 4.5 is fast and cheap. Sonnet can be re-enabled once quota resets.
    # Confirmed working model IDs (pinned, not rolling -latest aliases):
    HAIKU_MODEL_ID:  str = "anthropic/claude-haiku-4-5-20251001"
    SONNET_MODEL_ID: str = "anthropic/claude-haiku-4-5-20251001"  # override: use Haiku

    SONNET_LLM: CrewLLM = CrewLLM(
        model=SONNET_MODEL_ID,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.3,
        max_tokens=8192,
    )
    HAIKU_LLM: CrewLLM = CrewLLM(
        model=HAIKU_MODEL_ID,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.1,
        max_tokens=4096,
    )
    MODEL_NAME: str = SONNET_MODEL_ID

LLM_IDENTIFIER: CrewLLM = SONNET_LLM

# Embedding model (used by ChromaDB memory layer)
EMBEDDING_MODEL: str = "text-embedding-3-small"

# Local fallback model if OpenAI key is absent
EMBEDDING_FALLBACK_MODEL: str = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# 5. Agent / Crew Runtime Constants
# ---------------------------------------------------------------------------
# Pricing per 1M tokens (Claude Sonnet 4: $3.00 input / $15.00 output)
PRICE_PER_1M_INPUT_TOKENS: float = 3.00
PRICE_PER_1M_OUTPUT_TOKENS: float = 15.00

# Pricing for OpenAI Embeddings (text-embedding-3-small: $0.02 per 1M)
EMBEDDING_PRICE_PER_1M: float = 0.02

# Maximum LLM iterations per agent before CrewAI raises MaxIterationsError.
# quality_editor is higher because it reads multiple files before writing the report.
# latex_author is highest — it writes 10 files, each requiring a separate tool call.
AGENT_MAX_ITER: dict[str, int] = {
    "research_director": 12,
    "deep_researcher":   18,
    "data_visualizer":   40,   # 9 figures × ~4 tool calls each (read+write+execute+check) = ~36 needed
    "hebrew_writer":     40,   # writes 9 chapter prose sections; increased to handle fallback reads
    "latex_author":      30,   # 3–4 files per task (split into 3 writers); each needs ~7 iter/file
    "biology_expert":    15,   # biological ground-truth for echolocation chapters
    "vision_ai_expert":  15,   # visual SLAM, depth estimation, semantic perception
    "physics_expert":    15,   # acoustics, matched filter, Doppler, wave propagation
    "algorithms_expert": 15,   # probabilistic algorithms, SLAM, estimation theory
    "aerospace_marine_expert": 15,   # UAV dynamics, INS, submarine/AUV sonar
    "signal_processing_expert": 15,  # acoustic chirp analysis, beamforming, matched filtering
    "control_systems_expert":   15,  # UAV dynamics, PID/LQR, path planning
    "ml_expert":                15,  # neural architectures, fusion networks, RL navigation
}

# Target paper length used in agent prompts
PAPER_TARGET_PAGES: int = 28          # midpoint of 25–30 range
PAPER_MIN_PAGES:    int = 25
PAPER_MAX_PAGES:    int = 30

# ---------------------------------------------------------------------------
# 6. Tool Constants
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_BYTES: int   = 1 * 1024 * 1024   # 1 MB — FileReaderTool limit
CODE_EXECUTOR_TIMEOUT: int = 30                 # seconds — PythonCodeExecutorTool
ARXIV_MAX_RESULTS: int     = 5                  # default ArXiv results per query

# Directories agents are allowed to write into (relative to PROJECT_ROOT)
WRITABLE_DIRS: tuple[str, ...] = ("latex", "outputs", "docs")

# Files that must never be overwritten by an agent.
# Entries can be basenames (matched against filename) or PROJECT_ROOT-relative
# paths (matched against the full relative path).
# cover.tex is the only static chapter — contains assignment cover page layout.
# main.tex controls chapter input order and the XeLaTeX preamble.
# All content chapters (ch01–ch09) are now agent-written and fully dynamic.
PROTECTED_FILES: tuple[str, ...] = (
    # Basenames — block the filename regardless of directory
    ".env",
    ".gitignore",
    "requirements.txt",
    "main.tex",
    "cover.tex",
    # Relative paths from PROJECT_ROOT — belt-and-suspenders
    "src/config.py",
    "latex/main.tex",
    "latex/chapters/cover.tex",
)

# ---------------------------------------------------------------------------
# 7. Logging Configuration (loguru)
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE:  Path = OUTPUTS_DIR / "researchcrew.log"

# Remove the default stderr sink so we can add our own formatted ones
logger.remove()

# Console sink — human-readable, colourised
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    ),
)

# File sink — structured, persistent, rotated daily
logger.add(
    str(LOG_FILE),
    level="DEBUG",          # always capture everything to disk
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
)

logger.info(f"ResearchCrew starting. PROJECT_ROOT={PROJECT_ROOT}")

# ---------------------------------------------------------------------------
# 8. Embedder Configuration  (used by src/crew.py when building the Crew)
# ---------------------------------------------------------------------------

def _openai_key_is_real() -> bool:
    """Return True only if OPENAI_API_KEY looks like an actual key, not a placeholder."""
    return bool(OPENAI_API_KEY) and OPENAI_API_KEY.startswith("sk-")


def get_embedder_config() -> dict | None:
    """
    Return the ChromaDB embedder config for CrewAI memory, or None if no
    valid embedder is available.

    Strategy:
      - If OPENAI_API_KEY is a real key (starts with 'sk-') → text-embedding-3-small
      - Otherwise → None (caller should set memory=False on the Crew)

    Note: CrewAI 1.14+ requires CHROMA_HUGGINGFACE_API_KEY for the HuggingFace
    provider, making it no longer a free local fallback. Until that key is
    configured, we skip memory rather than crash.
    """
    if _openai_key_is_real():
        logger.info("Embedder: OpenAI text-embedding-3-small")
        return {
            "provider": "openai",
            "config": {
                "model": EMBEDDING_MODEL,
                "api_key": OPENAI_API_KEY,
            },
        }
    else:
        logger.warning(
            "No valid embedder available (OPENAI_API_KEY not set or is a placeholder). "
            "Crew memory will be disabled for this run. "
            "Set a real OPENAI_API_KEY in .env to enable long-term memory."
        )
        return None


# ---------------------------------------------------------------------------
# 9. Config Validation  (call once at application entry point)
# ---------------------------------------------------------------------------

def validate_config() -> None:
    """
    Validate that required API keys are present for the active provider.

    Raises:
        EnvironmentError: If a required key is missing.
    """
    missing: list[str] = []

    if ACTIVE_PROVIDER == "deepseek":
        if not DEEPSEEK_API_KEY:
            missing.append("  • DEEPSEEK_API_KEY: Get yours at platform.deepseek.com")
    else:
        if not ANTHROPIC_API_KEY:
            missing.append("  • ANTHROPIC_API_KEY: Get yours at console.anthropic.com")

    if not os.getenv("SERPER_API_KEY", ""):
        missing.append("  • SERPER_API_KEY: Free key at serper.dev")

    if missing:
        raise EnvironmentError(
            f"\n\n[NavigatorCrew] Missing required environment variables:\n"
            + "\n".join(missing)
            + "\n\nCopy .env.example → .env and fill in the values.\n"
        )

    logger.success(f"Config validation passed. Provider={ACTIVE_PROVIDER}.")


# ---------------------------------------------------------------------------
# 10. Quick self-test  (python src/config.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== ResearchCrew Config Self-Test ===\n")
    print(f"PROJECT_ROOT : {PROJECT_ROOT}")
    print(f"LATEX_DIR    : {LATEX_DIR}")
    print(f"FIGURES_DIR  : {FIGURES_DIR}")
    print(f"OUTPUTS_DIR  : {OUTPUTS_DIR}")
    print(f"MODEL_NAME   : {MODEL_NAME}")
    print(f"LLM_IDENT    : {LLM_IDENTIFIER}")
    print(f"LOG_LEVEL    : {LOG_LEVEL}")
    print()

    # Show which keys are set (masked) vs missing
    for key in ("ANTHROPIC_API_KEY", "SERPER_API_KEY", "OPENAI_API_KEY"):
        val = os.getenv(key, "")
        status = f"SET ({val[:8]}...)" if val else "NOT SET"
        print(f"{key:25s}: {status}")

    print()
    try:
        validate_config()
    except EnvironmentError as exc:
        print(str(exc))
        sys.exit(1)

    print("\nEmbedder config:")
    import json
    cfg = get_embedder_config()
    # Mask the API key in output
    if "config" in cfg and "api_key" in cfg["config"]:
        cfg["config"]["api_key"] = cfg["config"]["api_key"][:8] + "..."
    print(json.dumps(cfg, indent=2))
