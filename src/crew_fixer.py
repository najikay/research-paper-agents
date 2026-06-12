"""
src/crew_fixer.py
==================
Mini crew for fixing failed domain expert outputs.
"""

from __future__ import annotations

from crewai import Crew, Process

from src.agents import create_slam_researcher
from src.config import logger, validate_config
from src.tasks import create_task_fix_domain
from src.tools import (
    ArxivSearchTool,
    FileReaderTool,
    SafeFileWriterTool,
    SerperDevSearchTool,
)
from src.utils.token_accountant import TokenAccountant


def build_fixer_crew(
    topic: str,
    failed_domains: list[str],
    outline_content: str,
) -> tuple[Crew, TokenAccountant]:
    """A single Research Fixer agent fills in gaps for all failed domains."""
    validate_config()
    serper = SerperDevSearchTool()
    arxiv = ArxivSearchTool()
    writer = SafeFileWriterTool()
    reader = FileReaderTool()

    fixer = create_slam_researcher(tools=[reader, writer, serper, arxiv])
    fixer.max_iter = 20

    tasks = [
        create_task_fix_domain(fixer, domain_key, topic, outline_content)
        for domain_key in failed_domains
    ]
    accountant = TokenAccountant()
    accountant.install()

    crew = Crew(
        agents=[fixer], tasks=tasks, process=Process.sequential,
        verbose=True, memory=False,
        step_callback=accountant.step_callback, task_callback=accountant.task_callback,
    )
    logger.info(
        f"NavigatorCrew v6.0 [FIXER]: "
        f"fixing {len(failed_domains)} domain(s): {failed_domains}"
    )
    return crew, accountant
