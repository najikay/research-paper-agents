"""
src/tasks/tasks_assemble.py — crew-building helpers that wire task factories together.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING
from src.tasks.domains import _DOMAIN_DESCRIPTIONS
from src.tasks.tasks_research_core import (create_task_outline, create_task_research, create_task_figures)
from src.tasks.tasks_domain import create_task_domain_expert
from src.tasks.tasks_prose import create_task_hebrew_prose
from src.tasks.tasks_latex_parts import create_task_latex_part1, create_task_latex_part2
from src.tasks.tasks_latex_split import (create_task_latex_a, create_task_latex_b, create_task_latex_c)

def create_research_tasks(
    director, researcher,
    domain_experts: dict[str, Agent],
    topic: str,
) -> list[Task]:
    """
    Create tasks for the research phase crew:
    outline → research → 8 domain expert tasks (all in parallel context from research).
    """
    t_outline = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    domain_tasks = []
    for key, expert in domain_experts.items():
        desc = _DOMAIN_DESCRIPTIONS.get(key, key)
        t = create_task_domain_expert(expert, key, desc, [t_outline, t_research])
        domain_tasks.append(t)

    return [t_outline, t_research] + domain_tasks


def create_writing_tasks(
    visualizer, hebrew_writer,
    author_a, author_b, author_c,
    run_folder: Path | None = None,
) -> list[Task]:
    """
    Create tasks for the writing phase crew:
    figures → hebrew_prose → latex_a → latex_b → latex_c
    """
    t_figures = create_task_figures(visualizer, [], run_folder=run_folder)
    t_hebrew = create_task_hebrew_prose(hebrew_writer, [t_figures])
    t_latex_a = create_task_latex_a(author_a, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_b = create_task_latex_b(author_b, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex_c = create_task_latex_c(author_c, [t_hebrew, t_figures], run_folder=run_folder)
    return [t_figures, t_hebrew, t_latex_a, t_latex_b, t_latex_c]


def create_all_tasks(
    director,
    researcher,
    dom_vision_ai,
    dom_physics,
    dom_algorithms,
    dom_aerospace,
    dom_biology,
    visualizer,
    hebrew_writer,
    author,
    topic,
    run_folder: Path | None = None,
    fast_mode: bool = False,
) -> list[Task]:
    """
    Full pipeline (fast_mode=False, 11 tasks):
      outline → research
        → domain_vision_ai → domain_physics → domain_algorithms
        → domain_aerospace → domain_biology
        → figures → hebrew_prose
        → latex_part1 → latex_part2

    Fast pipeline (fast_mode=True, 6 tasks — skips domain experts):
      outline → research → figures → hebrew_prose → latex_part1 → latex_part2
    """
    t_outline  = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    if fast_mode:
        # Skip all 5 domain expert tasks — use only outline + research as context
        domain_tasks = []
        hebrew_context = [t_research]
    else:
        t_dom_vision_ai   = create_task_domain_expert(dom_vision_ai,   "vision_ai",   _DOMAIN_DESCRIPTIONS["vision_ai"],   [t_research])
        t_dom_physics     = create_task_domain_expert(dom_physics,     "physics",     _DOMAIN_DESCRIPTIONS["physics"],     [t_research])
        t_dom_algorithms  = create_task_domain_expert(dom_algorithms,  "algorithms",  _DOMAIN_DESCRIPTIONS["algorithms"],  [t_research])
        t_dom_aerospace   = create_task_domain_expert(dom_aerospace,   "aerospace",   _DOMAIN_DESCRIPTIONS["aerospace"],   [t_research])
        t_dom_biology     = create_task_domain_expert(dom_biology,     "biology",     _DOMAIN_DESCRIPTIONS["biology"],     [t_research])

        domain_tasks   = [t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology]
        hebrew_context = [t_research] + domain_tasks

    t_figures  = create_task_figures(visualizer, [t_research], run_folder=run_folder)
    t_hebrew   = create_task_hebrew_prose(hebrew_writer, hebrew_context)
    t_latex1   = create_task_latex_part1(author, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex2   = create_task_latex_part2(author, [t_hebrew, t_figures], run_folder=run_folder)

    return [
        t_outline, t_research,
        *domain_tasks,
        t_figures, t_hebrew, t_latex1, t_latex2,
    ]


# ---------------------------------------------------------------------------
# Smoke pipeline (2 tasks, ~35 LLM calls, ~3–8 minutes)
# ---------------------------------------------------------------------------
