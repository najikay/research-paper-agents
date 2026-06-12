"""
tests/test_crew.py
==================
Coverage tests for src/crew.py — exercise every builder function and every
build_crew mode branch. These tests only CONSTRUCT Crew objects; they never
call .kickoff(), so no network calls are made.
"""

from __future__ import annotations

import pytest
from crewai import Crew, Process

from src.crew import (
    build_crew,
    build_fixer_crew,
    build_research_crew,
    build_writing_crew,
)
from src.utils.token_accountant import TokenAccountant


@pytest.fixture(autouse=True)
def _no_validate(monkeypatch):
    """Make validate_config a no-op so tests don't depend on env keys."""
    monkeypatch.setattr("src.crew.validate_config", lambda: None)


def _assert_crew(crew, accountant, n_agents, n_tasks):
    """Common assertions for a constructed crew + accountant pair."""
    assert isinstance(crew, Crew)
    assert isinstance(accountant, TokenAccountant)
    assert len(crew.agents) == n_agents
    assert len(crew.tasks) == n_tasks
    assert crew.process == Process.sequential


def test_build_research_crew(tmp_path):
    crew, accountant = build_research_crew(topic="Test Topic", run_folder=tmp_path)
    try:
        # director + researcher + 8 domain experts = 10 agents
        _assert_crew(crew, accountant, n_agents=10, n_tasks=len(crew.tasks))
        assert len(crew.agents) == 10
        assert len(crew.tasks) >= 1
    finally:
        accountant.uninstall()


def test_build_writing_crew(tmp_path):
    crew, accountant = build_writing_crew(run_folder=tmp_path)
    try:
        # visualizer + hebrew writer + 3 LaTeX authors = 5 agents
        _assert_crew(crew, accountant, n_agents=5, n_tasks=len(crew.tasks))
        assert len(crew.agents) == 5
        assert len(crew.tasks) >= 1
    finally:
        accountant.uninstall()


def test_build_fixer_crew(tmp_path):
    failed_domains = ["physics", "biology"]
    outline = "Short outline content for the fixer crew."
    crew, accountant = build_fixer_crew(
        topic="Test Topic",
        failed_domains=failed_domains,
        outline_content=outline,
    )
    try:
        # single fixer agent, one task per failed domain
        _assert_crew(crew, accountant, n_agents=1, n_tasks=len(failed_domains))
    finally:
        accountant.uninstall()


def test_build_crew_smoke_mode(tmp_path):
    crew, accountant = build_crew(
        topic="Test Topic",
        run_folder=tmp_path,
        smoke_mode=True,
    )
    try:
        # smoke mode — 2 agents
        _assert_crew(crew, accountant, n_agents=2, n_tasks=len(crew.tasks))
        assert len(crew.agents) == 2
    finally:
        accountant.uninstall()


def test_build_crew_fast_mode(tmp_path):
    crew, accountant = build_crew(
        topic="Test Topic",
        run_folder=tmp_path,
        fast_mode=True,
    )
    try:
        # fast mode — 5 agents
        _assert_crew(crew, accountant, n_agents=5, n_tasks=len(crew.tasks))
        assert len(crew.agents) == 5
    finally:
        accountant.uninstall()


def test_build_crew_full_mode(tmp_path):
    crew, accountant = build_crew(
        topic="Test Topic",
        run_folder=tmp_path,
        fast_mode=False,
        smoke_mode=False,
    )
    try:
        # full mode — 10 agents
        _assert_crew(crew, accountant, n_agents=10, n_tasks=len(crew.tasks))
        assert len(crew.agents) == 10
    finally:
        accountant.uninstall()
