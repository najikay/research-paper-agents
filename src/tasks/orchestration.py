"""
src/tasks/orchestration.py
===========================
Crew-building helpers that assemble tasks into phase-specific lists.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

from src.tasks.domain_tasks import (
    DOMAIN_DESCRIPTIONS,
    create_task_domain_expert,
)
from src.tasks.latex_split_tasks import (
    create_task_latex_a,
    create_task_latex_b,
    create_task_latex_c,
)
from src.tasks.latex_tasks import (
    create_task_latex_part1,
    create_task_latex_part2,
)
from src.tasks.research_tasks import (
    create_task_figures,
    create_task_outline,
    create_task_research,
)
from src.tasks.writing_tasks import create_task_hebrew_prose


def create_research_tasks(
    director: Agent,
    researcher: Agent,
    domain_experts: dict[str, Agent],
    topic: str,
) -> list[Task]:
    """Create tasks for the research phase crew."""
    t_outline = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    domain_tasks = []
    for key, expert in domain_experts.items():
        desc = DOMAIN_DESCRIPTIONS.get(key, key)
        t = create_task_domain_expert(expert, key, desc, [t_outline, t_research])
        domain_tasks.append(t)

    return [t_outline, t_research] + domain_tasks


def create_writing_tasks(
    visualizer: Agent,
    hebrew_writer: Agent,
    author_a: Agent,
    author_b: Agent,
    author_c: Agent,
    run_folder: Path | None = None,
) -> list[Task]:
    """Create tasks for the writing phase crew."""
    t_figures = create_task_figures(visualizer, [], run_folder=run_folder)
    t_hebrew = create_task_hebrew_prose(hebrew_writer, [t_figures])
    t_latex_a = create_task_latex_a(author_a, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_b = create_task_latex_b(author_b, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_c = create_task_latex_c(author_c, [t_hebrew, t_figures], run_folder=run_folder)
    return [t_figures, t_hebrew, t_latex_a, t_latex_b, t_latex_c]


def create_all_tasks(
    director: Agent,
    researcher: Agent,
    dom_vision_ai: Agent,
    dom_physics: Agent,
    dom_algorithms: Agent,
    dom_aerospace: Agent,
    dom_biology: Agent,
    visualizer: Agent,
    hebrew_writer: Agent,
    author: Agent,
    topic: str,
    run_folder: Path | None = None,
    fast_mode: bool = False,
) -> list[Task]:
    """Build the full or fast pipeline task list."""
    t_outline = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    if fast_mode:
        domain_tasks: list[Task] = []
        hebrew_context = [t_research]
    else:
        t_dom_vision = create_task_domain_expert(
            dom_vision_ai, "vision_ai", DOMAIN_DESCRIPTIONS["vision_ai"], [t_research],
        )
        t_dom_physics = create_task_domain_expert(
            dom_physics, "physics", DOMAIN_DESCRIPTIONS["physics"], [t_research],
        )
        t_dom_algorithms = create_task_domain_expert(
            dom_algorithms, "algorithms", DOMAIN_DESCRIPTIONS["algorithms"], [t_research],
        )
        t_dom_aerospace = create_task_domain_expert(
            dom_aerospace, "aerospace", DOMAIN_DESCRIPTIONS["aerospace"], [t_research],
        )
        t_dom_biology = create_task_domain_expert(
            dom_biology, "biology", DOMAIN_DESCRIPTIONS["biology"], [t_research],
        )
        domain_tasks = [
            t_dom_vision, t_dom_physics, t_dom_algorithms,
            t_dom_aerospace, t_dom_biology,
        ]
        hebrew_context = [t_research] + domain_tasks

    t_figures = create_task_figures(visualizer, [t_research], run_folder=run_folder)
    t_hebrew = create_task_hebrew_prose(hebrew_writer, hebrew_context)
    t_latex1 = create_task_latex_part1(author, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex2 = create_task_latex_part2(author, [t_hebrew, t_figures], run_folder=run_folder)

    return [
        t_outline, t_research,
        *domain_tasks,
        t_figures, t_hebrew, t_latex1, t_latex2,
    ]
