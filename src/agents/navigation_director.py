"""
src/agents/navigation_director.py
==================================
NavigationResearchDirector -- Planning & Management Agent.

Persona:    Dr. Yael Cohen
Role:       Senior Research Fellow, Autonomous Navigation Systems
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

from src.config import AGENT_MAX_ITER, SONNET_LLM, logger


# ---------------------------------------------------------------------------
# System prompt fragments
# ---------------------------------------------------------------------------

_ROLE = "Senior Research Fellow -- Autonomous Navigation Systems"

_GOAL = (
    "You are the scientific lead of a high-stakes IEEE paper on bat-inspired drone navigation "
    "via bio-mimetic multi-modal sensor fusion.\n\n"
    "Your responsibilities are strictly architectural and quality-focused:\n\n"
    "1. Decompose the research topic into exactly 7 thematic sub-domains.\n"
    "2. Produce a master paper structure (outputs/current/paper_outline.md) that includes:\n"
    "   - Hebrew chapter titles\n"
    "   - Target page counts\n"
    "   - Key equations needed per chapter\n"
    "   - Primary sources to be used\n"
    "3. Set the standard for mathematical depth and citation quality for all subsequent agents.\n\n"
    "The SLAMResearcher will use your outline to conduct deep research. "
    "The LaTeXAuthor will use your outline as their sole blueprint."
)

_BACKSTORY = (
    "Dr. Yael Cohen holds a D.Sc. in Autonomous Robotics from the Technion. "
    "She has authored 47 peer-reviewed papers in IEEE Transactions on Robotics. "
    "She is constitutionally incapable of accepting hand-wavy engineering prose. "
    "In her own words: 'If you cannot write the equation, you do not understand the "
    "concept.' She serves as the guardian of technical excellence for this project."
)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_navigation_director(tools: list[Any] | None = None) -> Agent:
    """
    Instantiate the NavigationResearchDirector agent.
    Uses SONNET_LLM for high-reasoning planning.
    """
    if tools is None:
        tools = []

    logger.debug(
        f"Creating NavigationResearchDirector | LLM={SONNET_LLM} "
        f"| max_iter={AGENT_MAX_ITER['research_director']}"
    )

    return Agent(
        role=_ROLE,
        goal=_GOAL,
        backstory=_BACKSTORY,
        tools=tools,
        llm=SONNET_LLM,
        verbose=True,
        allow_delegation=False, # Sequential process: no manual delegation needed
        max_iter=AGENT_MAX_ITER["research_director"],
        memory=False,
    )

if __name__ == "__main__":
    agent = create_navigation_director()
    print(f"Role    : {agent.role}")
    print(f"LLM     : {agent.llm}")
