"""
tests/test_config_ext.py
=========================
Tests for config_validation.py (embedder config, openai key check) and
task factory functions not covered elsewhere.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import src.config as cfg
from src.config_validation import _openai_key_is_real, get_embedder_config, validate_config


def test_openai_key_is_real_with_sk(monkeypatch):
    """A key starting with 'sk-' is considered real."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "sk-abc123")
    assert _openai_key_is_real() is True


def test_openai_key_is_real_empty(monkeypatch):
    """Empty key is not real."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "")
    assert _openai_key_is_real() is False


def test_openai_key_is_real_placeholder(monkeypatch):
    """A placeholder not starting with sk- is not real."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "your-key-here")
    assert _openai_key_is_real() is False


def test_get_embedder_config_with_valid_key(monkeypatch):
    """With a real OpenAI key, returns OpenAI embedder config dict."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "sk-test123")
    monkeypatch.setattr(cfg, "EMBEDDING_MODEL", "text-embedding-3-small")
    result = get_embedder_config()
    assert result is not None
    assert result["provider"] == "openai"
    assert result["config"]["model"] == "text-embedding-3-small"
    assert result["config"]["api_key"] == "sk-test123"


def test_get_embedder_config_without_valid_key(monkeypatch):
    """Without a real key, returns None."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "")
    result = get_embedder_config()
    assert result is None


def test_validate_config_anthropic_provider(monkeypatch):
    """Anthropic provider validates ANTHROPIC_API_KEY."""
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "anthropic")
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SERPER_API_KEY", "test")
    validate_config()


def test_validate_config_anthropic_missing(monkeypatch):
    """Missing ANTHROPIC_API_KEY raises."""
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "anthropic")
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("SERPER_API_KEY", "test")
    with pytest.raises(OSError, match="ANTHROPIC_API_KEY"):
        validate_config()


# ---------------------------------------------------------------------------
# Task factory coverage: smoke_tasks, review_tasks, latex_split_tasks
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dummy_agent():
    """A minimal mock agent for task factory calls."""
    from src.agents.latex_author import create_latex_author
    return create_latex_author(tools=[])


def test_create_task_latex_smoke(dummy_agent):
    """Smoke task factory returns a Task with expected output_file."""
    from src.tasks.smoke_tasks import create_task_latex_smoke
    t = create_task_latex_smoke(dummy_agent, [], run_folder=Path("/tmp/r"))
    assert t.output_file == "outputs/current/latex_status.md"
    assert "ch01_intro.tex" in t.description


def test_create_smoke_tasks(dummy_agent):
    """create_smoke_tasks returns 2 tasks."""
    from src.agents.navigation_director import create_navigation_director
    from src.tasks.smoke_tasks import create_smoke_tasks
    director = create_navigation_director(tools=[])
    tasks = create_smoke_tasks(director, dummy_agent, "test topic", Path("/tmp/r"))
    assert len(tasks) == 2


def test_create_task_review(dummy_agent):
    """Review task has quality_report.md output."""
    from src.tasks.review_tasks import create_task_review
    t = create_task_review(dummy_agent, [])
    assert "quality_report.md" in t.output_file


def test_create_remediation_task(dummy_agent):
    """Remediation task includes failed sections in description."""
    from src.tasks.review_tasks import create_remediation_task
    t = create_remediation_task(
        dummy_agent, ["ch03", "ch07"],
        "outputs/current/quality_report.md",
        "outputs/current/latex_status.md",
        run_folder=Path("/tmp/r"),
    )
    assert "ch03" in t.description
    assert "ch07" in t.description
    assert "REMEDIATION" in t.description


def test_create_remediation_task_no_run_folder(dummy_agent):
    """Remediation task without run_folder omits path notes."""
    from src.tasks.review_tasks import create_remediation_task
    t = create_remediation_task(
        dummy_agent, ["ch01"], "qr.md", "out.md", run_folder=None,
    )
    assert "REMEDIATION" in t.description


def test_create_task_latex_a(dummy_agent):
    """Writer A task covers abstract + ch01-ch03 + references.bib."""
    from src.tasks.latex_split_tasks import create_task_latex_a
    t = create_task_latex_a(dummy_agent, [], run_folder=Path("/tmp/r"))
    assert "abstract.tex" in t.description
    assert "ch01_intro.tex" in t.description
    assert "ch03_sensors.tex" in t.description


def test_create_task_latex_b(dummy_agent):
    """Writer B task covers ch04-ch06."""
    from src.tasks.latex_split_tasks import create_task_latex_b
    t = create_task_latex_b(dummy_agent, [], run_folder=Path("/tmp/r"))
    assert "ch04_slam.tex" in t.description
    assert "ch06_algorithm.tex" in t.description


def test_create_task_latex_c(dummy_agent):
    """Writer C task covers ch07-ch09."""
    from src.tasks.latex_split_tasks import create_task_latex_c
    t = create_task_latex_c(dummy_agent, [], run_folder=Path("/tmp/r"))
    assert "ch07_oursystem.tex" in t.description
    assert "ch09_conclusion.tex" in t.description


# ---------------------------------------------------------------------------
# Orchestration coverage: create_research_tasks, create_writing_tasks
# ---------------------------------------------------------------------------

def test_create_research_tasks():
    """create_research_tasks returns outline + research + 8 domain tasks."""
    from src.agents import (
        create_aerospace_marine_expert,
        create_algorithms_expert,
        create_biology_expert,
        create_control_systems_expert,
        create_ml_expert,
        create_navigation_director,
        create_physics_expert,
        create_signal_processing_expert,
        create_slam_researcher,
        create_vision_ai_expert,
    )
    from src.tasks.orchestration import create_research_tasks
    director = create_navigation_director(tools=[])
    researcher = create_slam_researcher(tools=[])
    experts = {
        "vision_ai": create_vision_ai_expert(tools=[]),
        "physics": create_physics_expert(tools=[]),
        "algorithms": create_algorithms_expert(tools=[]),
        "aerospace": create_aerospace_marine_expert(tools=[]),
        "biology": create_biology_expert(tools=[]),
        "signal_processing": create_signal_processing_expert(tools=[]),
        "control_systems": create_control_systems_expert(tools=[]),
        "ml": create_ml_expert(tools=[]),
    }
    tasks = create_research_tasks(director, researcher, experts, "Test")
    assert len(tasks) == 10


def test_create_writing_tasks(dummy_agent):
    """create_writing_tasks returns 5 tasks."""
    from src.agents import create_hebrew_academic_writer, create_visualization_engineer
    from src.tasks.orchestration import create_writing_tasks
    vis = create_visualization_engineer(tools=[])
    hw = create_hebrew_academic_writer(tools=[])
    tasks = create_writing_tasks(vis, hw, dummy_agent, dummy_agent, dummy_agent, Path("/tmp/r"))
    assert len(tasks) == 5
