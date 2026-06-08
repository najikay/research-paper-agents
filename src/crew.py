"""
src/crew.py
============
NavigatorCrew assembly — wires agents, tools, tasks, and the TokenAccountant.
Architecture: Robust Sequential Pipeline v5.2 (10-agent, 10-task).
"""

from __future__ import annotations
from pathlib import Path
from crewai import Crew, Process
from src.agents import (
    create_navigation_director,
    create_slam_researcher,
    create_visualization_engineer,
    create_hebrew_academic_writer,
    create_latex_author,
    create_vision_ai_expert,
    create_physics_expert,
    create_algorithms_expert,
    create_aerospace_marine_expert,
    create_biology_expert,
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


def build_crew(topic: str = _DEFAULT_TOPIC, run_folder: str | Path = "") -> tuple[Crew, TokenAccountant]:
    """
    Assemble the Crew with a ROBUST sequential process and model tiering.

    Args:
        topic:      Research topic string.
        run_folder: Absolute path to the per-run working directory.  Agents
                    write LaTeX files and figures into {run_folder}/latex/.
    """
    validate_config()
    _run_folder = Path(run_folder) if run_folder else Path(__file__).resolve().parent.parent

    # ------------------------------------------------------------------
    # Instantiate tools
    # ------------------------------------------------------------------
    serper   = SerperDevSearchTool()
    arxiv    = ArxivSearchTool()
    scraper  = NavigatorWebScraperTool()
    # PythonCodeExecutorTool writes figures into the run-folder, not project root
    executor = PythonCodeExecutorTool(figures_dir=_run_folder / "latex" / "figures")
    writer   = SafeFileWriterTool()
    reader   = FileReaderTool()

    # Research / search tools shared by domain experts
    _research_tools = [reader, writer, serper, arxiv]

    # ------------------------------------------------------------------
    # Core pipeline agents
    # ------------------------------------------------------------------
    director      = create_navigation_director(tools=[reader, writer, serper, arxiv])
    researcher    = create_slam_researcher(tools=[reader, serper, arxiv, scraper])
    visualizer    = create_visualization_engineer(tools=[executor, writer, reader])
    hebrew_writer = create_hebrew_academic_writer(tools=[reader, writer])
    author        = create_latex_author(tools=[writer, reader])

    # ------------------------------------------------------------------
    # Domain expert agents (each with full research + file tools)
    # ------------------------------------------------------------------
    dom_vision_ai  = create_vision_ai_expert(tools=_research_tools)
    dom_physics    = create_physics_expert(tools=_research_tools)
    dom_algorithms = create_algorithms_expert(tools=_research_tools)
    dom_aerospace  = create_aerospace_marine_expert(tools=_research_tools)
    dom_biology    = create_biology_expert(tools=_research_tools)

    # ------------------------------------------------------------------
    # Build 10-task pipeline:
    # outline → research → 5×domain → figures → hebrew_prose → latex
    # ------------------------------------------------------------------
    tasks = create_all_tasks(
        director=director,
        researcher=researcher,
        dom_vision_ai=dom_vision_ai,
        dom_physics=dom_physics,
        dom_algorithms=dom_algorithms,
        dom_aerospace=dom_aerospace,
        dom_biology=dom_biology,
        visualizer=visualizer,
        hebrew_writer=hebrew_writer,
        author=author,
        topic=topic,
        run_folder=_run_folder,
    )

    # Token accounting
    accountant = TokenAccountant()
    accountant.install()

    # Assemble crew — sequential process for maximum stability
    crew = Crew(
        agents=[
            director, researcher,
            dom_vision_ai, dom_physics, dom_algorithms, dom_aerospace, dom_biology,
            visualizer, hebrew_writer, author,
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        step_callback=accountant.step_callback,
        task_callback=accountant.task_callback,
    )

    logger.info(
        "NavigatorCrew v5.2 assembled: "
        f"process=sequential | agents=10 | tasks={len(tasks)}"
    )
    return crew, accountant
