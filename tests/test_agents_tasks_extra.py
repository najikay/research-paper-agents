"""
tests/test_agents_tasks_extra.py
================================
Extra coverage for the ``if tools is None`` warning branch of all 13 agent
factories (the existing tests/test_agents.py always passes tools=[], so that
branch was never exercised).
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


@pytest.fixture
def real_agent():
    """A real CrewAI Agent (construction makes no LLM call)."""
    return create_navigation_director(tools=[])


# ---------------------------------------------------------------------------
# (a) Agent factories — exercise the `if tools is None:` warning branch.
# ---------------------------------------------------------------------------

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
    agent = factory()
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
