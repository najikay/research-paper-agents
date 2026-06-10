"""
src/crew.py
============
NavigatorCrew assembly — wires agents, tools, tasks, and the TokenAccountant.

v6 architecture — split pipeline:
  Research phase:  director + researcher + 8 domain experts  (10 agents)
  Writing phase:   visualizer + Hebrew writer + 3 LaTeX authors  (5 agents)
  Total:           13 unique agents, ~15 tasks

Pipeline modes:
  full  (default) — 13 agents, split research/writing crews
  fast  (--fast)  — 5 agents,  6 tasks  (skips domain experts, single writer)
  smoke (--smoke) — 2 agents,  2 tasks  (outline + latex-all)
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
    create_signal_processing_expert,
    create_control_systems_expert,
    create_ml_expert,
)
from src.config import logger, validate_config
from src.tasks import (
    create_all_tasks,
    create_smoke_tasks,
    create_research_tasks,
    create_writing_tasks,
)
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
_SMOKE_AUTHOR_MAX_ITER = 45


def build_research_crew(
    topic: str = _DEFAULT_TOPIC,
    run_folder: str | Path = "",
) -> tuple[Crew, TokenAccountant]:
    """
    Research phase crew: director + researcher + 8 domain experts.
    Runs outline → research → domain expert enrichment.
    """
    validate_config()
    _run_folder = Path(run_folder) if run_folder else Path(__file__).resolve().parent.parent

    # Tools
    serper  = SerperDevSearchTool()
    arxiv   = ArxivSearchTool()
    scraper = NavigatorWebScraperTool()
    writer  = SafeFileWriterTool()
    reader  = FileReaderTool()
    _research_tools = [reader, writer, serper, arxiv]

    # Core agents
    director   = create_navigation_director(tools=[reader, writer, serper, arxiv])
    researcher = create_slam_researcher(tools=[reader, writer, serper, arxiv, scraper])

    # Domain experts (8 total: 5 original + 3 new)
    domain_experts = {
        "vision_ai":          create_vision_ai_expert(tools=_research_tools),
        "physics":            create_physics_expert(tools=_research_tools),
        "algorithms":         create_algorithms_expert(tools=_research_tools),
        "aerospace":          create_aerospace_marine_expert(tools=_research_tools),
        "biology":            create_biology_expert(tools=_research_tools),
        "signal_processing":  create_signal_processing_expert(tools=_research_tools),
        "control_systems":    create_control_systems_expert(tools=_research_tools),
        "ml":                 create_ml_expert(tools=_research_tools),
    }

    tasks = create_research_tasks(
        director=director,
        researcher=researcher,
        domain_experts=domain_experts,
        topic=topic,
    )

    agents_list = [director, researcher] + list(domain_experts.values())

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
        f"NavigatorCrew v6.0 [RESEARCH PHASE]: "
        f"agents={len(agents_list)} | tasks={len(tasks)}"
    )
    return crew, accountant


def build_writing_crew(
    run_folder: str | Path = "",
) -> tuple[Crew, TokenAccountant]:
    """
    Writing phase crew: visualizer + Hebrew writer + 3 LaTeX authors.
    Runs figures → Hebrew prose → LaTeX A/B/C.
    """
    validate_config()
    _run_folder = Path(run_folder) if run_folder else Path(__file__).resolve().parent.parent

    # Tools
    executor = PythonCodeExecutorTool(figures_dir=_run_folder / "latex" / "figures")
    writer   = SafeFileWriterTool()
    reader   = FileReaderTool()

    # Agents
    visualizer    = create_visualization_engineer(tools=[executor, writer, reader])
    hebrew_writer = create_hebrew_academic_writer(tools=[reader, writer])
    author_a      = create_latex_author(tools=[writer, reader])
    author_b      = create_latex_author(tools=[writer, reader])
    author_c      = create_latex_author(tools=[writer, reader])

    # Each LaTeX writer handles 3–5 files; 30 iterations is enough
    author_a.max_iter = 30
    author_b.max_iter = 30
    author_c.max_iter = 30

    tasks = create_writing_tasks(
        visualizer=visualizer,
        hebrew_writer=hebrew_writer,
        author_a=author_a,
        author_b=author_b,
        author_c=author_c,
        run_folder=_run_folder,
    )

    agents_list = [visualizer, hebrew_writer, author_a, author_b, author_c]

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
        f"NavigatorCrew v6.0 [WRITING PHASE]: "
        f"agents={len(agents_list)} | tasks={len(tasks)}"
    )
    return crew, accountant


def build_fixer_crew(
    topic: str,
    failed_domains: list[str],
    outline_content: str,
) -> tuple[Crew, TokenAccountant]:
    """
    Mini crew for fixing failed domain expert outputs.
    A single Research Fixer agent fills in gaps for all failed domains.
    """
    from src.tasks.research_tasks import create_task_fix_domain

    validate_config()
    serper = SerperDevSearchTool()
    arxiv  = ArxivSearchTool()
    writer = SafeFileWriterTool()
    reader = FileReaderTool()

    # Reuse the SLAM researcher as the fixer — it has the right tools and backstory
    fixer = create_slam_researcher(tools=[reader, writer, serper, arxiv])
    fixer.max_iter = 20  # enough for focused content generation

    tasks = [
        create_task_fix_domain(fixer, domain_key, topic, outline_content)
        for domain_key in failed_domains
    ]

    accountant = TokenAccountant()
    accountant.install()

    crew = Crew(
        agents=[fixer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        step_callback=accountant.step_callback,
        task_callback=accountant.task_callback,
    )

    logger.info(
        f"NavigatorCrew v6.0 [FIXER]: "
        f"fixing {len(failed_domains)} domain(s): {failed_domains}"
    )
    return crew, accountant


# ---------------------------------------------------------------------------
# Legacy build_crew — used by fast/smoke modes and backward compat
# ---------------------------------------------------------------------------
def build_crew(
    topic: str = _DEFAULT_TOPIC,
    run_folder: str | Path = "",
    fast_mode: bool = False,
    smoke_mode: bool = False,
) -> tuple[Crew, TokenAccountant]:
    """
    Assemble the NavigatorCrew (legacy single-crew mode).
    Used by smoke mode, fast mode, and backward-compatible callers.
    Full mode now uses build_research_crew() + build_writing_crew() instead.
    """
    validate_config()
    _run_folder = Path(run_folder) if run_folder else Path(__file__).resolve().parent.parent

    # Tools
    serper   = SerperDevSearchTool()
    arxiv    = ArxivSearchTool()
    scraper  = NavigatorWebScraperTool()
    executor = PythonCodeExecutorTool(figures_dir=_run_folder / "latex" / "figures")
    writer   = SafeFileWriterTool()
    reader   = FileReaderTool()
    _research_tools = [reader, writer, serper, arxiv]

    # Core agents
    director = create_navigation_director(tools=[reader, writer, serper, arxiv])
    author   = create_latex_author(tools=[writer, reader])

    # Smoke mode — 2 agents, 2 tasks
    if smoke_mode:
        author.max_iter = _SMOKE_AUTHOR_MAX_ITER
        tasks = create_smoke_tasks(
            director=director,
            author=author,
            topic=topic,
            run_folder=_run_folder,
        )
        agents_list = [director, author]
        mode_tag = "SMOKE (2 agents, 2 tasks)"

    # Fast mode — 5 agents, 6 tasks (no domain experts)
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

    # Full mode — redirect to split architecture
    else:
        logger.info("Full mode redirecting to split research/writing crews")
        researcher    = create_slam_researcher(tools=[reader, serper, arxiv, scraper])
        visualizer    = create_visualization_engineer(tools=[executor, writer, reader])
        hebrew_writer = create_hebrew_academic_writer(tools=[reader, writer])
        dom_vision_ai  = create_vision_ai_expert(tools=_research_tools)
        dom_physics    = create_physics_expert(tools=_research_tools)
        dom_algorithms = create_algorithms_expert(tools=_research_tools)
        dom_aerospace  = create_aerospace_marine_expert(tools=_research_tools)
        dom_biology    = create_biology_expert(tools=_research_tools)

        author.max_iter = 65

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

    # Token accounting + Crew assembly
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
        f"NavigatorCrew v6.0 [{mode_tag}]: "
        f"agents={len(agents_list)} | tasks={len(tasks)}"
    )
    return crew, accountant
