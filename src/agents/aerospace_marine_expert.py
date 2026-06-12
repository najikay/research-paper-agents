"""
src/agents/aerospace_marine_expert.py
======================================
AerospacemarineExpert — Aerospace Engineering & Marine/Submarine Navigation Agent.

Persona:    Dr. Ethan Ben-David
Role:       Aerospace Engineering & Marine/Submarine Navigation Specialist
Tools:      FileReaderTool, SafeFileWriterTool
            (injected at crew-assembly time by crew.py)
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

from src.agents.aerospace_marine_expert_prompts import BACKSTORY, GOAL, ROLE
from src.config import AGENT_MAX_ITER, SONNET_LLM, logger


def create_aerospace_marine_expert(tools: list[Any] | None = None) -> Agent:
    """
    Instantiate the AerospacemarineExpert agent.

    Args:
        tools: [FileReaderTool(), SafeFileWriterTool()]
               Pass [] or None only in test/dry-run contexts.

    Returns:
        A configured CrewAI Agent.
    """
    if tools is None:
        tools = []
        logger.warning(
            "AerospacemarineExpert created with NO tools. "
            "Expected: FileReaderTool, SafeFileWriterTool. "
            "Acceptable for unit tests only."
        )

    logger.debug(
        f"Creating AerospacemarineExpert | LLM={SONNET_LLM} "
        f"| tools={[type(t).__name__ for t in tools]} "
        f"| max_iter={AGENT_MAX_ITER['aerospace_marine_expert']}"
    )

    return Agent(
        role=ROLE,
        goal=GOAL,
        backstory=BACKSTORY,
        tools=tools,
        llm=SONNET_LLM,
        verbose=True,
        allow_delegation=False,
        max_iter=AGENT_MAX_ITER["aerospace_marine_expert"],
        memory=False,
    )


if __name__ == "__main__":
    agent = create_aerospace_marine_expert()
    print(f"Role    : {agent.role}")
    print(f"LLM     : {agent.llm}")
    print(f"Max iter: {agent.max_iter}")
    print(f"Memory  : {agent.memory}")
    print(f"Tools   : {agent.tools} (empty — expected in self-test)")
    print("\nPersona : Dr. Ethan Ben-David")
    print("Domain  : Aerospace Engineering & Marine/Submarine Navigation")
