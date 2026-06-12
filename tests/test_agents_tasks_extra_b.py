"""
tests/test_agents_tasks_extra_b.py
==================================
Extra coverage for uncovered task-builder functions in src/tasks/*.
Split from test_agents_tasks_extra.py.
"""

from __future__ import annotations

import pytest

from src.agents import create_navigation_director
from src.tasks.tasks_assemble import create_all_tasks, create_research_tasks, create_writing_tasks
from src.tasks.tasks_domain import create_task_domain_expert, create_task_fix_domain
from src.tasks.tasks_latex_split import create_task_latex_a, create_task_latex_b, create_task_latex_c
from src.tasks.tasks_remediate import create_remediation_task, create_task_review
from src.tasks.tasks_smoke import create_smoke_tasks, create_task_latex_smoke


@pytest.fixture
def real_agent():
    """A real CrewAI Agent (construction makes no LLM call)."""
    return create_navigation_director(tools=[])


def _assert_valid_task(task):
    """Every CrewAI Task must carry a non-empty description and expected_output."""
    assert task is not None
    assert isinstance(task.description, str) and task.description.strip()
    assert isinstance(task.expected_output, str) and task.expected_output.strip()


# ---------------------------------------------------------------------------
# tasks_latex_split.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "builder",
    [create_task_latex_a, create_task_latex_b, create_task_latex_c],
    ids=["latex_a", "latex_b", "latex_c"],
)
def test_latex_split_builders_default_dir(builder, real_agent):
    task = builder(real_agent, context=[])
    _assert_valid_task(task)


@pytest.mark.parametrize(
    "builder",
    [create_task_latex_a, create_task_latex_b, create_task_latex_c],
    ids=["latex_a", "latex_b", "latex_c"],
)
def test_latex_split_builders_run_folder(builder, real_agent, tmp_path):
    task = builder(real_agent, context=[], run_folder=tmp_path)
    _assert_valid_task(task)
    assert str(tmp_path) in task.description or "latex" in task.description


# ---------------------------------------------------------------------------
# tasks_remediate.py
# ---------------------------------------------------------------------------

def test_create_task_review(real_agent):
    task = create_task_review(real_agent, context=[])
    _assert_valid_task(task)


def test_create_remediation_task_no_run_folder(real_agent):
    task = create_remediation_task(
        real_agent,
        failed_sections=["methodology", "equations"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
    )
    _assert_valid_task(task)
    assert "methodology" in task.description


def test_create_remediation_task_with_run_folder(real_agent, tmp_path):
    task = create_remediation_task(
        real_agent,
        failed_sections=["algorithms"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
        run_folder=tmp_path,
    )
    _assert_valid_task(task)
    assert str(tmp_path) in task.description


# ---------------------------------------------------------------------------
# tasks_smoke.py
# ---------------------------------------------------------------------------

def test_create_task_latex_smoke_default(real_agent):
    task = create_task_latex_smoke(real_agent, context=[])
    _assert_valid_task(task)


def test_create_task_latex_smoke_run_folder(real_agent, tmp_path):
    task = create_task_latex_smoke(real_agent, context=[], run_folder=tmp_path)
    _assert_valid_task(task)


def test_create_smoke_tasks(real_agent, tmp_path):
    tasks = create_smoke_tasks(
        real_agent, real_agent, topic="bat-inspired drone navigation", run_folder=tmp_path
    )
    assert len(tasks) == 2
    for t in tasks:
        _assert_valid_task(t)


# ---------------------------------------------------------------------------
# tasks_domain.py
# ---------------------------------------------------------------------------

def test_create_task_domain_expert(real_agent):
    task = create_task_domain_expert(
        real_agent, "algorithms", "EKF/UKF/particle filters", context=[]
    )
    _assert_valid_task(task)


def test_create_task_fix_domain(real_agent):
    task = create_task_fix_domain(
        real_agent, domain_key="physics", topic="bat-inspired drone navigation",
        outline_content="# Outline\nChapter 1 ...",
    )
    _assert_valid_task(task)


# ---------------------------------------------------------------------------
# tasks_assemble.py
# ---------------------------------------------------------------------------

def test_create_research_tasks(real_agent):
    domain_experts = {
        "vision_ai": real_agent, "physics": real_agent,
        "algorithms": real_agent, "aerospace": real_agent, "biology": real_agent,
    }
    tasks = create_research_tasks(
        real_agent, real_agent, domain_experts, topic="bat navigation"
    )
    assert len(tasks) == 2 + len(domain_experts)
    for t in tasks:
        _assert_valid_task(t)


def test_create_writing_tasks(real_agent, tmp_path):
    tasks = create_writing_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, run_folder=tmp_path
    )
    assert len(tasks) == 5
    for t in tasks:
        _assert_valid_task(t)


def test_create_all_tasks_fast_mode(real_agent, tmp_path):
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation", run_folder=tmp_path, fast_mode=True,
    )
    assert len(tasks) == 6
    for t in tasks:
        _assert_valid_task(t)


def test_create_all_tasks_full_mode(real_agent, tmp_path):
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation", run_folder=tmp_path, fast_mode=False,
    )
    assert len(tasks) == 11
    for t in tasks:
        _assert_valid_task(t)
