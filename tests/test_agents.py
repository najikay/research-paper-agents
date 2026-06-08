"""
tests/test_agents.py
====================
Unit tests for all 5 NavigatorCrew agent factory functions.
No LLM calls are made — tests assert on the returned Agent object properties.
"""

from __future__ import annotations

import pytest

from src.agents.navigation_director import create_navigation_director
from src.agents.slam_researcher import create_slam_researcher
from src.agents.visualization_engineer import create_visualization_engineer
from src.agents.hebrew_academic_writer import create_hebrew_academic_writer
from src.agents.latex_author import create_latex_author, CHAPTER_MANIFEST
from src.config import AGENT_MAX_ITER


# ---------------------------------------------------------------------------
# NavigationResearchDirector
# ---------------------------------------------------------------------------

def test_navigation_director_instantiates():
    """NavigationResearchDirector must instantiate without raising."""
    agent = create_navigation_director(tools=[])
    assert agent is not None


def test_navigation_director_role():
    """NavigationResearchDirector role must contain 'Director' or 'Navigation'."""
    agent = create_navigation_director(tools=[])
    assert "Director" in agent.role or "Navigation" in agent.role


def test_navigation_director_no_delegation():
    """NavigationResearchDirector must have allow_delegation=False."""
    agent = create_navigation_director(tools=[])
    assert agent.allow_delegation is False


def test_navigation_director_max_iter():
    """NavigationResearchDirector max_iter must match AGENT_MAX_ITER['research_director']."""
    agent = create_navigation_director(tools=[])
    assert agent.max_iter == AGENT_MAX_ITER["research_director"]


# ---------------------------------------------------------------------------
# SLAMAndFusionResearcher
# ---------------------------------------------------------------------------

def test_slam_researcher_instantiates():
    """SLAMAndFusionResearcher must instantiate without raising."""
    agent = create_slam_researcher(tools=[])
    assert agent is not None


def test_slam_researcher_role():
    """SLAMAndFusionResearcher role must contain 'Researcher' or 'SLAM'."""
    agent = create_slam_researcher(tools=[])
    assert "Researcher" in agent.role or "SLAM" in agent.role


def test_slam_researcher_english_language_rule():
    """SLAMAndFusionResearcher goal must mention 'English' (language rule)."""
    agent = create_slam_researcher(tools=[])
    assert (
        "English" in agent.goal
        or "ENGLISH" in agent.goal
        or "english" in agent.goal
    ), "Researcher goal must specify the English-language rule"


def test_slam_researcher_no_delegation():
    """SLAMAndFusionResearcher must have allow_delegation=False."""
    agent = create_slam_researcher(tools=[])
    assert agent.allow_delegation is False


# ---------------------------------------------------------------------------
# VisualizationEngineer
# ---------------------------------------------------------------------------

def test_visualization_engineer_instantiates():
    """VisualizationEngineer must instantiate without raising."""
    agent = create_visualization_engineer(tools=[])
    assert agent is not None


def test_visualization_engineer_role():
    """VisualizationEngineer role must contain 'Visualization' or 'Engineer'."""
    agent = create_visualization_engineer(tools=[])
    assert "Visualization" in agent.role or "Engineer" in agent.role


def test_visualization_engineer_no_delegation():
    """VisualizationEngineer must have allow_delegation=False."""
    agent = create_visualization_engineer(tools=[])
    assert agent.allow_delegation is False


# ---------------------------------------------------------------------------
# HebrewAcademicWriter
# ---------------------------------------------------------------------------

def test_hebrew_academic_writer_instantiates():
    """HebrewAcademicWriter must instantiate without raising."""
    agent = create_hebrew_academic_writer(tools=[])
    assert agent is not None


def test_hebrew_academic_writer_role():
    """HebrewAcademicWriter role must contain 'Hebrew'."""
    agent = create_hebrew_academic_writer(tools=[])
    assert "Hebrew" in agent.role


def test_hebrew_academic_writer_goal_mentions_english():
    """HebrewAcademicWriter goal must mention 'English' (language principle)."""
    agent = create_hebrew_academic_writer(tools=[])
    assert "English" in agent.goal


def test_hebrew_academic_writer_no_delegation():
    """HebrewAcademicWriter must have allow_delegation=False."""
    agent = create_hebrew_academic_writer(tools=[])
    assert agent.allow_delegation is False


# ---------------------------------------------------------------------------
# LaTeXAuthor
# ---------------------------------------------------------------------------

def test_latex_author_instantiates():
    """LaTeXAuthor must instantiate without raising."""
    agent = create_latex_author(tools=[])
    assert agent is not None


def test_latex_author_role():
    """LaTeXAuthor role must contain 'LaTeX'."""
    agent = create_latex_author(tools=[])
    assert "LaTeX" in agent.role


def test_latex_author_goal_has_em_dash_prohibition():
    """LaTeXAuthor goal must contain 'FORBIDDEN' or 'PROHIBITION' (em-dash rule)."""
    agent = create_latex_author(tools=[])
    assert "FORBIDDEN" in agent.goal or "PROHIBITION" in agent.goal


def test_latex_author_goal_has_required_bibtex_keys():
    """LaTeXAuthor goal must contain the canonical key 'Thrun2005ProbRobotics'."""
    agent = create_latex_author(tools=[])
    assert "Thrun2005ProbRobotics" in agent.goal


def test_latex_author_chapter_manifest_excludes_protected():
    """CHAPTER_MANIFEST must not include ch04_slam.tex, main.tex, or cover.tex."""
    files_in_manifest = [ch["file"] for ch in CHAPTER_MANIFEST]
    assert "ch04_slam.tex" not in files_in_manifest, (
        "ch04_slam.tex is protected and must not be in manifest"
    )
    assert "main.tex" not in files_in_manifest, (
        "main.tex is protected and must not be in manifest"
    )
    assert "cover.tex" not in files_in_manifest, (
        "cover.tex is protected and must not be in manifest"
    )


def test_latex_author_no_delegation():
    """LaTeXAuthor must have allow_delegation=False."""
    agent = create_latex_author(tools=[])
    assert agent.allow_delegation is False


# ---------------------------------------------------------------------------
# Cross-agent checks
# ---------------------------------------------------------------------------

def test_all_agents_memory_disabled():
    """All 5 agents must have memory disabled (falsy — None or False)."""
    agents = [
        create_navigation_director(tools=[]),
        create_slam_researcher(tools=[]),
        create_visualization_engineer(tools=[]),
        create_hebrew_academic_writer(tools=[]),
        create_latex_author(tools=[]),
    ]
    for agent in agents:
        assert not agent.memory, (
            f"Agent {agent.role!r} must have memory disabled, got {agent.memory!r}"
        )


def test_all_agents_verbose():
    """All 5 agents must have verbose=True."""
    agents = [
        create_navigation_director(tools=[]),
        create_slam_researcher(tools=[]),
        create_visualization_engineer(tools=[]),
        create_hebrew_academic_writer(tools=[]),
        create_latex_author(tools=[]),
    ]
    for agent in agents:
        assert agent.verbose is True, f"Agent {agent.role!r} must have verbose=True"
