"""
tests/test_agents_tasks_extra.py
================================
Extra coverage for:
  (a) the ``if tools is None`` warning branch of all 13 agent factories
      (the existing tests/test_agents.py always pass tools=[], so that
      branch was never exercised), and
  (b) the uncovered task-builder functions in src/tasks/*.

Constructing a CrewAI Agent or Task makes NO network/LLM call, so these
tests are fast and deterministic. A local ``real_agent`` fixture supplies a
real Agent wherever a builder needs a pydantic-valid agent argument.
"""

from __future__ import annotations

import pytest

from src.agents import (
    create_aerospace_marine_expert,
    create_algorithms_expert,
    create_biology_expert,
    create_control_systems_expert,
    create_hebrew_academic_writer,
    create_latex_author,
    create_ml_expert,
    create_navigation_director,
    create_physics_expert,
    create_signal_processing_expert,
    create_slam_researcher,
    create_vision_ai_expert,
    create_visualization_engineer,
)
from src.tasks.tasks_assemble import (
    create_all_tasks,
    create_research_tasks,
    create_writing_tasks,
)
from src.tasks.tasks_domain import create_task_domain_expert, create_task_fix_domain
from src.tasks.tasks_latex_split import (
    create_task_latex_a,
    create_task_latex_b,
    create_task_latex_c,
)
from src.tasks.tasks_remediate import create_remediation_task, create_task_review
from src.tasks.tasks_smoke import create_smoke_tasks, create_task_latex_smoke


@pytest.fixture
def real_agent():
    """A real CrewAI Agent (construction makes no LLM call). Task builders
    validate their ``agent`` field via pydantic, which rejects a MagicMock,
    so the task-builder tests use this instead of conftest's mock_agent."""
    return create_navigation_director(tools=[])


# ---------------------------------------------------------------------------
# (a) Agent factories — exercise the `if tools is None:` warning branch.
# ---------------------------------------------------------------------------

# All 13 factories, each called with NO arguments so `tools` defaults to None.
ALL_AGENT_FACTORIES = [
    create_navigation_director,
    create_slam_researcher,
    create_visualization_engineer,
    create_hebrew_academic_writer,
    create_latex_author,
    create_biology_expert,
    create_vision_ai_expert,
    create_physics_expert,
    create_algorithms_expert,
    create_aerospace_marine_expert,
    create_signal_processing_expert,
    create_control_systems_expert,
    create_ml_expert,
]


@pytest.mark.parametrize(
    "factory", ALL_AGENT_FACTORIES, ids=[f.__name__ for f in ALL_AGENT_FACTORIES]
)
def test_agent_factory_tools_none_branch(factory):
    """Calling each factory with no args (tools=None) must set tools=[]."""
    agent = factory()  # tools defaults to None -> hits the warning branch
    assert agent is not None
    assert agent.tools == []
    assert isinstance(agent.role, str)
    assert agent.role.strip(), "agent role must be non-empty"


def test_all_thirteen_factories_present():
    """Sanity: exactly the 13 documented factories are exercised."""
    assert len(ALL_AGENT_FACTORIES) == 13


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_task(task):
    """Every CrewAI Task must carry a non-empty description and expected_output."""
    assert task is not None
    assert isinstance(task.description, str) and task.description.strip()
    assert isinstance(task.expected_output, str) and task.expected_output.strip()


# ---------------------------------------------------------------------------
# (b) tasks_latex_split.py — writers A/B/C, with and without run_folder.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "builder",
    [create_task_latex_a, create_task_latex_b, create_task_latex_c],
    ids=["latex_a", "latex_b", "latex_c"],
)
def test_latex_split_builders_default_dir(builder, real_agent):
    """Builders work with the default (no run_folder) 'latex' path."""
    task = builder(real_agent, context=[])
    _assert_valid_task(task)


@pytest.mark.parametrize(
    "builder",
    [create_task_latex_a, create_task_latex_b, create_task_latex_c],
    ids=["latex_a", "latex_b", "latex_c"],
)
def test_latex_split_builders_run_folder(builder, real_agent, tmp_path):
    """Builders work with an explicit run_folder (covers the str(run_folder) branch)."""
    task = builder(real_agent, context=[], run_folder=tmp_path)
    _assert_valid_task(task)
    # run_folder path must be reflected in the generated description.
    assert str(tmp_path) in task.description or "latex" in task.description


# ---------------------------------------------------------------------------
# (b) tasks_remediate.py — review + targeted remediation.
# ---------------------------------------------------------------------------

def test_create_task_review(real_agent):
    task = create_task_review(real_agent, context=[])
    _assert_valid_task(task)
    assert "JSON verdict" in task.description or "verdict" in task.description


def test_create_remediation_task_no_run_folder(real_agent):
    """No run_folder -> paths_note stays empty (covers the falsy branch)."""
    task = create_remediation_task(
        real_agent,
        failed_sections=["methodology", "equations"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
    )
    _assert_valid_task(task)
    assert "methodology" in task.description
    assert "equations" in task.description


def test_create_remediation_task_with_run_folder(real_agent, tmp_path):
    """run_folder set -> paths_note is built (covers lines 54-80)."""
    task = create_remediation_task(
        real_agent,
        failed_sections=["algorithms"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
        run_folder=tmp_path,
    )
    _assert_valid_task(task)
    assert str(tmp_path) in task.description
    assert "algorithms" in task.description


# ---------------------------------------------------------------------------
# (b) tasks_smoke.py — single combined smoke task + 2-task pipeline.
# ---------------------------------------------------------------------------

def test_create_task_latex_smoke_default(real_agent):
    task = create_task_latex_smoke(real_agent, context=[])
    _assert_valid_task(task)


def test_create_task_latex_smoke_run_folder(real_agent, tmp_path):
    task = create_task_latex_smoke(real_agent, context=[], run_folder=tmp_path)
    _assert_valid_task(task)
    assert str(tmp_path) in task.description


def test_create_smoke_tasks(real_agent, tmp_path):
    """2-task smoke pipeline: outline -> latex_all (covers lines 96-98)."""
    tasks = create_smoke_tasks(
        real_agent, real_agent, topic="bat-inspired drone navigation", run_folder=tmp_path
    )
    assert len(tasks) == 2
    for task in tasks:
        _assert_valid_task(task)


# ---------------------------------------------------------------------------
# (b) tasks_domain.py — domain expert + domain fix.
# ---------------------------------------------------------------------------

def test_create_task_domain_expert(real_agent):
    task = create_task_domain_expert(
        real_agent, "algorithms", "EKF/UKF/particle filters", context=[]
    )
    _assert_valid_task(task)


def test_create_task_fix_domain(real_agent):
    """Covers lines 99-100 — _DOMAIN_DESCRIPTIONS lookup + Task build."""
    task = create_task_fix_domain(
        real_agent,
        domain_key="physics",
        topic="bat-inspired drone navigation",
        outline_content="# Outline\nChapter 1 ...",
    )
    _assert_valid_task(task)
    assert "physics" in task.description.lower() or "physics" in task.expected_output


# ---------------------------------------------------------------------------
# (b) tasks_assemble.py — crew-building helpers.
# ---------------------------------------------------------------------------

def test_create_research_tasks(real_agent):
    """outline -> research -> N domain expert tasks (covers lines 35-44)."""
    domain_experts = {
        "vision_ai": real_agent,
        "physics": real_agent,
        "algorithms": real_agent,
        "aerospace": real_agent,
        "biology": real_agent,
    }
    tasks = create_research_tasks(
        real_agent, real_agent, domain_experts, topic="bat navigation"
    )
    # outline + research + 5 domain tasks
    assert len(tasks) == 2 + len(domain_experts)
    for task in tasks:
        _assert_valid_task(task)


def test_create_writing_tasks(real_agent, tmp_path):
    """figures -> hebrew_prose -> latex_a/b/c (covers lines 56-61)."""
    tasks = create_writing_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, run_folder=tmp_path
    )
    assert len(tasks) == 5
    for task in tasks:
        _assert_valid_task(task)


def test_create_all_tasks_fast_mode(real_agent, tmp_path):
    """fast_mode=True skips domain experts (covers lines 95-96)."""
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation",
        run_folder=tmp_path,
        fast_mode=True,
    )
    # outline, research, figures, hebrew, latex1, latex2 = 6 tasks (no domain experts)
    assert len(tasks) == 6
    for task in tasks:
        _assert_valid_task(task)


def test_create_all_tasks_full_mode(real_agent, tmp_path):
    """fast_mode=False builds the full 11-task pipeline including domain experts."""
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation",
        run_folder=tmp_path,
        fast_mode=False,
    )
    # outline, research, 5 domain, figures, hebrew, latex1, latex2 = 11 tasks
    assert len(tasks) == 11
    for task in tasks:
        _assert_valid_task(task)
