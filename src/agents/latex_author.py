"""
src/agents/latex_author.py
===========================
LaTeXAuthor — IEEE Paper Writing Agent.

Persona:    Dr. Yael Mizrahi
Role:       IEEE LaTeX Technical Author (Hebrew/English Bilingual, Robotics Domain)
Compiler:   XeLaTeX (NOT pdflatex — Hebrew BiDi requires fontspec + polyglossia)
Tools:      SafeFileWriterTool, FileReaderTool
            (injected at crew-assembly time by crew.py)
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

from src.agents.latex_author_prompts import BACKSTORY, CHAPTER_MANIFEST, GOAL, ROLE
from src.config import AGENT_MAX_ITER, SONNET_LLM, logger


def create_latex_author(tools: list[Any] | None = None) -> Agent:
    """
    Instantiate the LaTeXAuthor agent.

    Args:
        tools: [SafeFileWriterTool(), FileReaderTool()]
               Pass [] or None only in test/dry-run contexts.

    Returns:
        A configured CrewAI Agent.
    """
    if tools is None:
        tools = []
        logger.warning(
            "LaTeXAuthor created with NO tools. "
            "Expected: SafeFileWriterTool, FileReaderTool. "
            "Acceptable for unit tests only."
        )

    logger.debug(
        f"Creating LaTeXAuthor | LLM={SONNET_LLM} "
        f"| tools={[type(t).__name__ for t in tools]} "
        f"| max_iter={AGENT_MAX_ITER['latex_author']}"
    )

    return Agent(
        role=ROLE,
        goal=GOAL,
        backstory=BACKSTORY,
        tools=tools,
        llm=SONNET_LLM,
        verbose=True,
        allow_delegation=False,
        max_iter=AGENT_MAX_ITER["latex_author"],
        memory=False,
    )


if __name__ == "__main__":
    agent = create_latex_author()
    print(f"Role    : {agent.role}")
    print(f"LLM     : {agent.llm}")
    print(f"Max iter: {agent.max_iter}")
    print(f"Memory  : {agent.memory}")
    print(f"Tools   : {agent.tools} (empty — expected in self-test)")
    print(f"\nChapters this agent will write ({len(CHAPTER_MANIFEST)}):")
    for ch in CHAPTER_MANIFEST:
        label = ch["label"] or "—"
        print(f"  {ch['file']:<30} \\label{{{label}}}")
