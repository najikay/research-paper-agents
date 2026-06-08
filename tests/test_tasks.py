"""
tests/test_tasks.py
===================
Unit tests for the task factory functions in src/tasks/research_tasks.py.
"""

from __future__ import annotations

import pytest

from src.agents.navigation_director import create_navigation_director
from src.agents.slam_researcher import create_slam_researcher
from src.agents.visualization_engineer import create_visualization_engineer
from src.agents.hebrew_academic_writer import create_hebrew_academic_writer
from src.agents.latex_author import create_latex_author
from src.tasks.research_tasks import (
    create_all_tasks,
    create_task_figures,
    create_task_hebrew_prose,
    create_task_latex,
    create_task_outline,
    create_task_research,
)

# Required BibTeX keys that must appear in the latex task description
REQUIRED_CITE_KEYS = [
    "Thrun2005ProbRobotics",
    "Kalman1960",
    "Grisetti2010g2o",
    "MurArtal2015ORB",
    "Julier1997CovarianceIntersection",
    "GriffinBatEcholocation",
    "GriffithBatEcholocation",
    "Simmons1979BatSonar",
    "Schnitzler1968DSC",
    "Schuller1974DSC",
    "MossEcholocation",
    "Rihaczek1969MatchedFilter",
    "CrewAIDocs",
    "AnthropicClaude",
]


# Shared real agents (no LLM calls made at instantiation time)
@pytest.fixture(scope="module")
def agents():
    """Real CrewAI agent instances — instantiation makes no LLM calls."""
    return {
        "director":      create_navigation_director(tools=[]),
        "researcher":    create_slam_researcher(tools=[]),
        "visualizer":    create_visualization_engineer(tools=[]),
        "hebrew_writer": create_hebrew_academic_writer(tools=[]),
        "author":        create_latex_author(tools=[]),
    }


@pytest.fixture(scope="module")
def outline_task(agents):
    return create_task_outline(agents["director"], topic="Bat-Inspired Drone Navigation")


@pytest.fixture(scope="module")
def research_task(agents, outline_task):
    return create_task_research(agents["researcher"], context=[outline_task])


@pytest.fixture(scope="module")
def figures_task(agents, research_task):
    return create_task_figures(agents["visualizer"], context=[research_task])


@pytest.fixture(scope="module")
def hebrew_task(agents, research_task):
    return create_task_hebrew_prose(agents["hebrew_writer"], context=[research_task])


@pytest.fixture(scope="module")
def latex_task(agents, hebrew_task, figures_task):
    return create_task_latex(agents["author"], context=[hebrew_task, figures_task])


# ---------------------------------------------------------------------------
# Outline task
# ---------------------------------------------------------------------------

def test_outline_task_output_file(outline_task):
    """Outline task must write to outputs/paper_outline.md."""
    assert outline_task.output_file == "outputs/paper_outline.md"


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

def test_research_task_output_file(research_task):
    """Research task must write to outputs/research_briefs.md."""
    assert research_task.output_file == "outputs/research_briefs.md"


def test_research_task_has_context(research_task):
    """Research task must have a non-empty context list."""
    assert research_task.context is not None
    assert len(research_task.context) > 0


# ---------------------------------------------------------------------------
# Figures task
# ---------------------------------------------------------------------------

def test_figures_task_output_file(figures_task):
    """Figures task must write to outputs/figures_manifest.md."""
    assert figures_task.output_file == "outputs/figures_manifest.md"


# ---------------------------------------------------------------------------
# Hebrew prose task
# ---------------------------------------------------------------------------

def test_hebrew_prose_task_output_file(hebrew_task):
    """Hebrew prose task must write to outputs/hebrew_prose.md."""
    assert hebrew_task.output_file == "outputs/hebrew_prose.md"


# ---------------------------------------------------------------------------
# LaTeX task
# ---------------------------------------------------------------------------

def test_latex_task_output_file(latex_task):
    """LaTeX task status file must be outputs/latex_status.md.
    Note: references.bib is written by the agent via SafeFileWriterTool, not
    via the task output_file mechanism (which would overwrite it with plain text).
    """
    assert latex_task.output_file == "outputs/latex_status.md"


def test_latex_task_does_not_write_ch04_slam(latex_task):
    """ch04_slam.tex must not appear in the FILES TO WRITE section of the latex task."""
    desc = latex_task.description
    if "FILES TO WRITE" in desc:
        write_section = desc.split("FILES TO WRITE")[1]
        assert "ch04_slam.tex" not in write_section, (
            "ch04_slam.tex must not appear in the FILES TO WRITE section"
        )
    else:
        assert "ch04_slam.tex" in desc, "ch04_slam.tex should be mentioned as protected"


def test_latex_task_does_not_write_main_tex(latex_task):
    """latex/main.tex must appear only in the PROTECTED block, not FILES TO WRITE."""
    desc = latex_task.description
    if "FILES TO WRITE" in desc:
        write_section = desc.split("FILES TO WRITE")[1]
        assert "latex/main.tex" not in write_section, (
            "latex/main.tex is protected and must not appear in FILES TO WRITE"
        )


def test_latex_task_has_all_14_citation_keys(latex_task):
    """All 14 required BibTeX citation keys must appear in the latex task description."""
    for key in REQUIRED_CITE_KEYS:
        assert key in latex_task.description, f"Required citation key missing from task: {key}"


# ---------------------------------------------------------------------------
# create_all_tasks
# ---------------------------------------------------------------------------

def test_create_all_tasks_returns_5(agents):
    """create_all_tasks must return exactly 5 tasks."""
    tasks = create_all_tasks(
        agents["director"], agents["researcher"], agents["visualizer"],
        agents["hebrew_writer"], agents["author"],
        topic="Test Topic",
    )
    assert len(tasks) == 5


def test_task_pipeline_order(agents):
    """Tasks must be returned in the order: outline, research, figures, prose, latex."""
    tasks = create_all_tasks(
        agents["director"], agents["researcher"], agents["visualizer"],
        agents["hebrew_writer"], agents["author"],
        topic="Test Topic",
    )
    assert "outline"  in tasks[0].output_file
    assert "research" in tasks[1].output_file
    assert "figures"  in tasks[2].output_file
    assert "prose"    in tasks[3].output_file
    assert "latex"    in tasks[4].output_file  # outputs/latex_status.md
