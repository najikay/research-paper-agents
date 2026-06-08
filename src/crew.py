"""
src/crew.py
============
NavigatorCrew assembly — wires agents, tools, tasks, and the TokenAccountant.
Architecture: Robust Sequential Pipeline v4.0.
"""

from __future__ import annotations
from crewai import Crew, Process
from src.agents import (
    create_navigation_director,
    create_slam_researcher,
    create_visualization_engineer,
    create_hebrew_academic_writer,
    create_latex_author,
)
from src.config import logger, validate_config
from src.tasks import create_all_tasks
from src.tools import (
    ArxivSearchTool,
    FileReaderTool,
    NavigatorWebScraperTool,
    PythonCodeExecutorTool,
    SafeFileWriterTool,
    SerperDevSearchTool,
)
from src.utils.token_accountant import TokenAccountant

_DEFAULT_TOPIC = "Bat-Inspired Drone Navigation via Bio-Mimetic Multi-Modal Sensor Fusion"

def build_crew(topic: str = _DEFAULT_TOPIC) -> tuple[Crew, TokenAccountant]:
    """
    Assemble the Crew with a ROBUST sequential process and model tiering.
    """
    validate_config()

    # Instantiate tools
    serper   = SerperDevSearchTool()
    arxiv    = ArxivSearchTool()
    scraper  = NavigatorWebScraperTool()
    executor = PythonCodeExecutorTool()
    writer   = SafeFileWriterTool()
    reader   = FileReaderTool()

    # Instantiate agents (model tiering handled inside factories)
    director       = create_navigation_director(tools=[writer])
    researcher     = create_slam_researcher(tools=[serper, arxiv, scraper])
    visualizer     = create_visualization_engineer(tools=[executor, writer])
    hebrew_writer  = create_hebrew_academic_writer(tools=[reader, writer])
    author         = create_latex_author(tools=[writer, reader])
    # Note: quality_editor excluded — quality gate is programmatic (nodes.py)

    # Build tasks (5-task pipeline: outline → research → figures → hebrew_prose → latex)
    tasks = create_all_tasks(
        director=director,
        researcher=researcher,
        visualizer=visualizer,
        hebrew_writer=hebrew_writer,
        author=author,
        topic=topic,
    )

    # Token accounting
    accountant = TokenAccountant()
    accountant.install()

    # Assemble crew — sequential process for maximum stability
    crew = Crew(
        agents=[director, researcher, visualizer, hebrew_writer, author],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        step_callback=accountant.step_callback,
        task_callback=accountant.task_callback,
    )

    logger.info(
        "NavigatorCrew v5.1 assembled: "
        f"process=sequential | agents=5 | tasks={len(tasks)}"
    )
    return crew, accountant
