"""
tests/test_tasks.py
===================
Unit tests for the task factory functions in src/tasks/research_tasks.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.navigation_director import create_navigation_director
from src.agents.slam_researcher import create_slam_researcher
from src.agents.visualization_engineer import create_visualization_engineer
from src.agents.hebrew_academic_writer import create_hebrew_academic_writer
from src.agents.latex_author import create_latex_author
from src.agents.vision_ai_expert import create_vision_ai_expert
from src.agents.physics_expert import create_physics_expert
from src.agents.algorithms_expert import create_algorithms_expert
from src.agents.aerospace_marine_expert import create_aerospace_marine_expert
from src.agents.biology_expert import create_biology_expert
from src.tasks.research_tasks import (
    create_all_tasks,
    create_task_figures,
    create_task_hebrew_prose,
    create_task_latex,
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

def test_outline_task_output_file(outline_task):
    """Outline task must write to outputs/current/paper_outline.md."""
    assert outline_task.output_file == "outputs/current/paper_outline.md"


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
    """Research task must write to outputs/current/research_briefs.md."""
    assert research_task.output_file == "outputs/current/research_briefs.md"


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

def test_hebrew_prose_task_output_file(hebrew_task):
    """Hebrew prose task status file must be hebrew_prose_status.md.
    The actual prose is written by SafeFileWriterTool to hebrew_prose.md;
    output_file is the status/summary file so CrewAI doesn't overwrite the prose.
    """
    assert hebrew_task.output_file == "outputs/current/hebrew_prose_status.md"


# ---------------------------------------------------------------------------
# LaTeX task
# ---------------------------------------------------------------------------

def test_latex_task_output_file(latex_task):
    """LaTeX task status file must be outputs/latex_status.md.
    Note: references.bib is written by the agent via SafeFileWriterTool, not
    via the task output_file mechanism (which would overwrite it with plain text).
    """
    assert latex_task.output_file == "outputs/current/latex_status.md"


def test_latex_part1_writes_ch01_and_ch04(latex_part1_task):
    """Part-1 task description must include ch01_intro.tex and ch04_slam.tex in FILES TO WRITE."""
    desc = latex_part1_task.description
    assert "ch01_intro.tex" in desc, "ch01_intro.tex must be in part-1 FILES TO WRITE"
    assert "ch04_slam.tex" in desc, "ch04_slam.tex must be in part-1 FILES TO WRITE"


def test_latex_part2_does_not_write_ch01_ch04(latex_task):
    """ch01_intro.tex and ch04_slam.tex must NOT appear in the part-2 FILES TO WRITE section."""
    desc = latex_task.description
    if "WRITE these" in desc:
        write_section = desc.split("WRITE these")[1]
        assert "ch01_intro.tex" not in write_section, (
            "ch01_intro.tex must not appear in part-2 FILES TO WRITE"
        )
        assert "ch04_slam.tex" not in write_section, (
            "ch04_slam.tex must not appear in part-2 FILES TO WRITE"
        )


def test_latex_task_does_not_write_main_tex(latex_task):
    """latex/main.tex must appear only in the PROTECTED block, not FILES TO WRITE."""
    desc = latex_task.description
    if "FILES TO WRITE" in desc:
        write_section = desc.split("FILES TO WRITE")[1]
        assert "latex/main.tex" not in write_section, (
            "latex/main.tex is protected and must not appear in FILES TO WRITE"
        )


def test_latex_part1_requests_minimum_bib_entries(latex_part1_task):
    """Part-1 task must request at least 14 BibTeX entries (count-based, not key-based)."""
    assert f"≥{_MIN_BIB_ENTRIES_REQUESTED}" in latex_part1_task.description, (
        f"Part-1 task must mention '≥{_MIN_BIB_ENTRIES_REQUESTED}' BibTeX entries"
    )


# ---------------------------------------------------------------------------
# create_all_tasks
# ---------------------------------------------------------------------------

def _all_tasks(agents):
    """Helper: build the full 10-task pipeline for reuse in tests."""
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
    assert "outline"    in tasks[0].output_file
    assert "research"   in tasks[1].output_file
    # Domain expert tasks have no output_file (by design — SafeFileWriterTool writes
    # the real content; setting output_file would let CrewAI overwrite it).
    # Verify via description instead.
    for i in range(2, 7):
        assert tasks[i].output_file is None or "domain_" in (tasks[i].output_file or "")
        assert "domain" in tasks[i].description.lower() or "specialist" in tasks[i].description.lower()
    assert "figures"    in tasks[7].output_file
    assert "prose"      in tasks[8].output_file
    assert "part1"      in tasks[9].output_file   # latex_status_part1.md
    assert "latex"      in tasks[10].output_file  # latex_status.md
