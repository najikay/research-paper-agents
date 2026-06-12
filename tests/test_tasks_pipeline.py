"""
tests/test_tasks_pipeline.py
==============================
Tests for create_all_tasks pipeline ordering and count.
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
from src.tasks import create_all_tasks

_RUN_FOLDER = Path("/tmp/test_navigator_run")


@pytest.fixture(scope="module")
def agents():
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


def _all_tasks(agents):
    """Helper: build the full 11-task pipeline."""
    return create_all_tasks(
        director=agents["director"],
        researcher=agents["researcher"],
        dom_vision_ai=agents["dom_vision_ai"],
        dom_physics=agents["dom_physics"],
        dom_algorithms=agents["dom_algorithms"],
        dom_aerospace=agents["dom_aerospace"],
        dom_biology=agents["dom_biology"],
        visualizer=agents["visualizer"],
        hebrew_writer=agents["hebrew_writer"],
        author=agents["author"],
        topic="Test Topic",
        run_folder=_RUN_FOLDER,
    )


def test_create_all_tasks_returns_11(agents):
    """create_all_tasks must return exactly 11 tasks."""
    tasks = _all_tasks(agents)
    assert len(tasks) == 11


def test_task_pipeline_order(agents):
    """Tasks must follow: outline, research, 5×domain, figures, prose, latex_part1, latex_part2."""
    tasks = _all_tasks(agents)
    assert "outline" in tasks[0].description.lower() or "paper_outline" in tasks[0].description
    assert "research" in tasks[1].description.lower() or "briefs" in tasks[1].description.lower()
    for i in range(2, 7):
        assert "domain" in tasks[i].description.lower() or "specialist" in tasks[i].description.lower()
    assert "figures"    in tasks[7].output_file
    assert "prose"      in tasks[8].output_file
    assert "part1"      in tasks[9].output_file
    assert "latex"      in tasks[10].output_file
