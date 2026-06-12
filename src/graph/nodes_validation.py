"""
src/graph/nodes_validation.py
==============================
Research-phase validation: scan domain expert outputs and fix failures.
"""

from __future__ import annotations

import re

from src.config import PROJECT_ROOT, logger
from src.graph.state import PipelineState

_MIN_DOMAIN_BYTES = 500
_LOOP_PATTERN = re.compile(r"(STEP 1|Let me read|Read existing work)", re.IGNORECASE)
_LOOP_THRESHOLD = 3

_DOMAIN_KEYS = [
    "vision_ai", "physics", "algorithms", "aerospace", "biology",
    "signal_processing", "control_systems", "ml",
]


def validate_and_fix_research(state: PipelineState) -> dict:
    """Scan domain_*.md files for failures and spawn a Fixer crew if needed."""
    logger.info("[Graph] NODE: validate_and_fix_research")
    staging = PROJECT_ROOT / "outputs" / "current"
    failed_domains: list[str] = []

    for key in _DOMAIN_KEYS:
        fpath = staging / f"domain_{key}.md"
        if not fpath.exists():
            logger.warning(f"[Validate] domain_{key}.md does not exist")
            failed_domains.append(key)
            continue

        content = fpath.read_text(encoding="utf-8", errors="replace")
        size = len(content.encode("utf-8"))

        if size < _MIN_DOMAIN_BYTES:
            logger.warning(f"[Validate] domain_{key}.md too small ({size} bytes)")
            failed_domains.append(key)
            continue

        loop_matches = _LOOP_PATTERN.findall(content)
        if len(loop_matches) >= _LOOP_THRESHOLD:
            logger.warning(
                f"[Validate] domain_{key}.md has loop pattern "
                f"({len(loop_matches)} matches) — agent was stuck"
            )
            failed_domains.append(key)
            continue

        stripped = content.strip()
        if stripped in ("DOMAIN EXPERT COMPLETE", "DOMAIN SKIP") or len(stripped) < 100:
            logger.warning(f"[Validate] domain_{key}.md is a shortcut/stub")
            failed_domains.append(key)
            continue

        logger.info(f"[Validate] domain_{key}.md OK ({size} bytes)")

    if not failed_domains:
        logger.info("[Validate] All domain expert outputs valid — no fixes needed")
        return {"research_fix_count": 0}

    outline_path = staging / "paper_outline.md"
    outline_content = ""
    if outline_path.exists():
        outline_content = outline_path.read_text(encoding="utf-8", errors="replace")

    logger.info(
        f"[Validate] {len(failed_domains)} domain(s) failed: {failed_domains} — "
        f"spawning Fixer crew"
    )

    from src.crew_fixer import build_fixer_crew
    fixer_crew, _ = build_fixer_crew(
        topic=state["topic"],
        failed_domains=failed_domains,
        outline_content=outline_content,
    )
    fixer_crew.kickoff()

    logger.info(f"[Validate] Fixer crew completed for: {failed_domains}")
    return {"research_fix_count": len(failed_domains)}
