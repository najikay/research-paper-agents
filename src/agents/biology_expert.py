"""
src/agents/biology_expert.py
=====================================
BiologyExpert — Neuroethology & Bio-Inspired Systems Specialist.

Persona:    Dr. Noa Tal
Role:       Neuroethology, Biological Sensing & Bio-Inspired Systems Specialist
Tools:      FileReaderTool, SafeFileWriterTool
            (injected at crew-assembly time by crew.py)
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

from src.agents.biology_expert_prompts import BACKSTORY, GOAL, ROLE
from src.config import AGENT_MAX_ITER, SONNET_LLM, logger


def create_biology_expert(tools: list[Any] | None = None) -> Agent:
    """
    Build the BiologyExpert agent (Dr. Noa Tal): a neuroethology and bio-inspired
    systems specialist that supplies biological ground truth on echolocation,
    sensory biology, and neural computation for downstream chapters.
    """
    if tools is None:
        tools = []
        logger.warning("BiologyExpert created with NO tools.")

    logger.debug(
        f"Creating BiologyExpert | LLM={SONNET_LLM} "
        f"| tools={[type(t).__name__ for t in tools]} "
        f"| max_iter={AGENT_MAX_ITER['biology_expert']}"
    )

    return Agent(
        role=ROLE,
        goal=GOAL,
        backstory=BACKSTORY,
        tools=tools,
        llm=SONNET_LLM,
        verbose=True,
        allow_delegation=False,
        max_iter=AGENT_MAX_ITER["biology_expert"],
        memory=False,
    )


if __name__ == "__main__":
    import sys

    print("=== BiologyExpert self-test ===")
    try:
        agent = create_biology_expert(tools=[])
        assert agent.role == ROLE, "role mismatch"
        assert agent.goal == GOAL, "goal mismatch"
        assert agent.backstory == BACKSTORY, "backstory mismatch"
        assert agent.max_iter == AGENT_MAX_ITER["biology_expert"], "max_iter mismatch"
        assert agent.verbose is True, "verbose should be True"
        assert agent.allow_delegation is False, "allow_delegation should be False"
        print("All assertions passed.")
        print(f"  role      : {agent.role}")
        print(f"  max_iter  : {agent.max_iter}")
        print(f"  llm       : {agent.llm}")
        print(f"  memory    : {agent.memory}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
