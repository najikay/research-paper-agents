"""
tests/test_tasks.py
===================
Unit tests for the task factory functions in src/tasks/research_tasks.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.aerospace_marine_expert import create_aerospace_marine_expert
from src.agents.algorithms_expert import create_algorithms_expert
from src.agents.biology_expert import create_biology_expert
from src.agents.hebrew_academic_writer import create_hebrew_academic_writer
from src.agents.latex_author import create_latex_author
from src.agents.navigation_director import create_navigation_director
from src.agents.physics_expert import create_physics_expert
from src.agents.slam_researcher import create_slam_researcher
from src.agents.vision_ai_expert import create_vision_ai_expert
from src.agents.visualization_engineer import create_visualization_engineer
from src.tasks.research_tasks import (
    create_task_figures,
    create_task_hebrew_prose,
    create_task_latex_part1,
    create_task_latex_part2,
    create_task_outline,
    create_task_research,
)

# Stable fake run folder used across module-scoped fixtures
_RUN_FOLDER = Path("/tmp/test_navigator_run")

# Minimum number of BibTeX entries the part-1 task must request (count-based)
_MIN_BIB_ENTRIES_REQUESTED = 14


# Shared real agents (no LLM calls made at instantiation time)
@pytest.fixture(scope="module")
def agents():
    """Real CrewAI agent instances — instantiation makes no LLM calls."""
    return {
        "director":       create_navigation_director(tools=[]),
        "researcher":     create_slam_researcher(tools=[]),
        "visualizer":     create_visualization_engineer(tools=[]),
        "hebrew_writer":  create_hebrew_academic_writer(tools=[]),
        "author":         create_latex_author(tools=[]),
        "dom_vision_ai":  create_vision_ai_expert(tools=[]),
        "dom_physics":    create_physics_expert(tools=[]),
        "dom_algorithms": create_algorithms_expert(tools=[]),
        "dom_aerospace":  create_aerospace_marine_expert(tools=[]),
        "dom_biology":    create_biology_expert(tools=[]),
    }


@pytest.fixture(scope="module")
def outline_task(agents):
    return create_task_outline(agents["director"], topic="Bat-Inspired Drone Navigation")


@pytest.fixture(scope="module")
def research_task(agents, outline_task):
    return create_task_research(agents["researcher"], context=[outline_task])


@pytest.fixture(scope="module")
def figures_task(agents, research_task):
    return create_task_figures(agents["visualizer"], context=[research_task], run_folder=_RUN_FOLDER)


@pytest.fixture(scope="module")
def hebrew_task(agents, research_task):
    return create_task_hebrew_prose(agents["hebrew_writer"], context=[research_task])


@pytest.fixture(scope="module")
def latex_part1_task(agents, hebrew_task, figures_task):
    """Part 1: abstract + ch02/03/05 + references.bib."""
    return create_task_latex_part1(agents["author"], context=[hebrew_task, figures_task], run_folder=_RUN_FOLDER)


@pytest.fixture(scope="module")
def latex_task(agents, latex_part1_task):
    """Part 2 (final latex task): ch06/07/08/09 + appendix."""
    return create_task_latex_part2(agents["author"], context=[latex_part1_task], run_folder=_RUN_FOLDER)


# ---------------------------------------------------------------------------
# Outline task
# ---------------------------------------------------------------------------

def test_outline_task_no_output_file(outline_task):
    """Outline task must NOT have output_file (SafeFileWriterTool writes content; output_file overwrites it)."""
    assert not outline_task.output_file


def test_outline_task_description_has_topic(outline_task):
    """Outline task description must embed the given topic string."""
    assert "Bat-Inspired Drone Navigation" in outline_task.description


def test_outline_task_description_mentions_25_30_pages(outline_task):
    """Outline task description must reference both 25 and 30 (page range)."""
    assert "25" in outline_task.description
    assert "30" in outline_task.description


# ---------------------------------------------------------------------------
# Research task
# ---------------------------------------------------------------------------

def test_research_task_no_output_file(research_task):
    """Research task must NOT have output_file (SafeFileWriterTool writes content; output_file overwrites it)."""
    assert not research_task.output_file


def test_research_task_has_context(research_task):
    """Research task must have a non-empty context list."""
    assert research_task.context is not None
    assert len(research_task.context) > 0


# ---------------------------------------------------------------------------
# Figures task
# ---------------------------------------------------------------------------

def test_figures_task_output_file(figures_task):
    """Figures task output_file must be a separate status file, not figures_manifest.md.
    The manifest itself is written by SafeFileWriterTool — using the same path for
    output_file would cause CrewAI to overwrite the manifest with the agent's short
    final response."""
    assert figures_task.output_file == "outputs/current/figures_status.md"


# ---------------------------------------------------------------------------
# Hebrew prose task
# ---------------------------------------------------------------------------

