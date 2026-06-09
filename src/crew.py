"""
src/crew.py
============
NavigatorCrew assembly — wires agents, tools, tasks, and the TokenAccountant.

Three pipeline modes:
  full  (default) — 10 agents, 11 tasks, ~60–120 min
  fast  (--fast)  — 5 agents,   6 tasks, ~20–40 min  (skips domain experts)
  smoke (--smoke) — 2 agents,   2 tasks, ~3–8 min    (outline + latex-all)
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
from src.tasks import create_all_tasks, create_smoke_tasks
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

# max_iter for the single combined latex task in smoke mode.
# 11 files × ~2.5 iterations each = ~28 minimum. 35 gives a small buffer.
_SMOKE_AUTHOR_MAX_ITER = 35


def build_crew(
    topic: str = _DEFAULT_TOPIC,
    run_folder: str | Path = "",
    fast_mode: bool = False,
    smoke_mode: bool = False,
) -> tuple[Crew, TokenAccountant]:
    """
    Assemble the NavigatorCrew.

    Args:
        topic:      Research topic string.
        run_folder: Absolute path to the per-run working directory.
        fast_mode:  Skip domain expert agents (6-task pipeline).
        smoke_mode: Minimal 2-task pipeline for quick iteration testing.
    """
    validate_config()
    _run_folder = Path(run_folder) if run_folder else Path(__file__).resolve().parent.parent

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    serper   = SerperDevSearchTool()
    arxiv    = ArxivSearchTool()
    scraper  = NavigatorWebScraperTool()
    executor = PythonCodeExecutorTool(figures_dir=_run_folder / "latex" / "figures")
    writer   = SafeFileWriterTool()
    reader   = FileReaderTool()
    _research_tools = [reader, writer, serper, arxiv]

    # ------------------------------------------------------------------
    # Core agents (always instantiated)
    # ------------------------------------------------------------------
    director = create_navigation_director(tools=[reader, writer, serper, arxiv])
    author   = create_latex_author(tools=[writer, reader])

    # ------------------------------------------------------------------
    # Smoke mode — 2 agents, 2 tasks
    # ------------------------------------------------------------------
    if smoke_mode:
        # Give the author more iterations to write all 11 files in one shot
        author.max_iter = _SMOKE_AUTHOR_MAX_ITER

        tasks = create_smoke_tasks(
            director=director,
            author=author,
            topic=topic,
            run_folder=_run_folder,
        )
        agents_list = [director, author]
        mode_tag = "SMOKE (2 agents, 2 tasks)"

    # ------------------------------------------------------------------
    # Fast mode — 5 agents, 6 tasks (no domain experts)
    # ------------------------------------------------------------------
    elif fast_mode:
        researcher    = create_slam_researcher(tools=[reader, serper, arxiv, scraper])
        visualizer    = create_visualization_engineer(tools=[executor, writer, reader])
        hebrew_writer = create_hebrew_academic_writer(tools=[reader, writer])

        tasks = create_all_tasks(
            director=director,
            researcher=researcher,
            dom_vision_ai=None,
            dom_physics=None,
            dom_algorithms=None,
            dom_aerospace=None,
            dom_biology=None,
            visualizer=visualizer,
            hebrew_writer=hebrew_writer,
            author=author,
            topic=topic,
            run_folder=_run_folder,
            fast_mode=True,
        )
        agents_list = [director, researcher, visualizer, hebrew_writer, author]
        mode_tag = "FAST (5 agents, 6 tasks)"

    # ------------------------------------------------------------------
    # Full mode — 10 agents, 11 tasks
    # ------------------------------------------------------------------
    else:
        researcher    = create_slam_researcher(tools=[reader, serper, arxiv, scraper])
        visualizer    = create_visualization_engineer(tools=[executor, writer, reader])
        hebrew_writer = create_hebrew_academic_writer(tools=[reader, writer])
        dom_vision_ai  = create_vision_ai_expert(tools=_research_tools)
        dom_physics    = create_physics_expert(tools=_research_tools)
        dom_algorithms = create_algorithms_expert(tools=_research_tools)
        dom_aerospace  = create_aerospace_marine_expert(tools=_research_tools)
        dom_biology    = create_biology_expert(tools=_research_tools)

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
            fast_mode=False,
        )
        agents_list = [
            director, researcher,
            dom_vision_ai, dom_physics, dom_algorithms, dom_aerospace, dom_biology,
            visualizer, hebrew_writer, author,
        ]
        mode_tag = "FULL (10 agents, 11 tasks)"

    # ------------------------------------------------------------------
    # Token accounting + Crew assembly
    # ------------------------------------------------------------------
    accountant = TokenAccountant()
    accountant.install()

    crew = Crew(
        agents=agents_list,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        step_callback=accountant.step_callback,
        task_callback=accountant.task_callback,
    )

    logger.info(
        f"NavigatorCrew v5.3 [{mode_tag}]: "
        f"agents={len(agents_list)} | tasks={len(tasks)}"
    )
    return crew, accountant
