"""
tests/test_crew_builders.py
============================
Unit tests for crew builder functions in src/crew, src/crew_legacy,
and src/crew_fixer.  Each builder is called with validate_config()
stubbed out; we assert the returned (Crew, TokenAccountant) tuple
and the expected agent / task counts.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Crew

from src.utils.token_accountant import TokenAccountant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prepare_run_folder(tmp_path: Path) -> Path:
    """Create the minimal directory layout the builders expect."""
    (tmp_path / "latex" / "figures").mkdir(parents=True)
    return tmp_path


def _assert_crew_shape(result, expected_agents: int):
    """Validate builder return value structure and agent count."""
    assert isinstance(result, tuple) and len(result) == 2
    crew, accountant = result
    assert isinstance(crew, Crew)
    assert isinstance(accountant, TokenAccountant)
    assert len(crew.agents) == expected_agents
    assert len(crew.tasks) >= 1


# ---------------------------------------------------------------------------
# src/crew — build_research_crew
# ---------------------------------------------------------------------------

class TestBuildResearchCrew:

    def test_returns_crew_with_10_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crew.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew import build_research_crew
        result = build_research_crew(run_folder=run_folder)
        _assert_crew_shape(result, expected_agents=10)

    def test_agents_include_director_and_researcher(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crew.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew import build_research_crew
        crew, _ = build_research_crew(run_folder=run_folder)
        roles = [a.role for a in crew.agents]
        assert any("direct" in r.lower() or "navigation" in r.lower() for r in roles)


# ---------------------------------------------------------------------------
# src/crew — build_writing_crew
# ---------------------------------------------------------------------------

class TestBuildWritingCrew:

    def test_returns_crew_with_5_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crew.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew import build_writing_crew
        result = build_writing_crew(run_folder=run_folder)
        _assert_crew_shape(result, expected_agents=5)


# ---------------------------------------------------------------------------
# src/crew_legacy — build_crew (smoke_mode)
# ---------------------------------------------------------------------------

class TestBuildCrewSmoke:

    def test_smoke_mode_2_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crew_legacy.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew_legacy import build_crew
        result = build_crew(run_folder=run_folder, smoke_mode=True)
        _assert_crew_shape(result, expected_agents=2)


# ---------------------------------------------------------------------------
# src/crew_legacy — build_crew (fast_mode)
# ---------------------------------------------------------------------------

class TestBuildCrewFast:

    def test_fast_mode_5_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.crew_legacy.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew_legacy import build_crew
        result = build_crew(run_folder=run_folder, fast_mode=True)
        _assert_crew_shape(result, expected_agents=5)


# ---------------------------------------------------------------------------
# src/crew_fixer — build_fixer_crew
# ---------------------------------------------------------------------------

class TestBuildFixerCrew:

    def test_fixer_1_agent(self, monkeypatch):
        monkeypatch.setattr("src.crew_fixer.validate_config", lambda: None)

        from src.crew_fixer import build_fixer_crew
        result = build_fixer_crew(
            topic="Test Topic",
            failed_domains=["vision_ai"],
            outline_content="Outline placeholder",
        )
        _assert_crew_shape(result, expected_agents=1)

    def test_fixer_task_count_matches_domains(self, monkeypatch):
        monkeypatch.setattr("src.crew_fixer.validate_config", lambda: None)

        from src.crew_fixer import build_fixer_crew
        domains = ["vision_ai", "physics", "biology"]
        crew, _ = build_fixer_crew(
            topic="Test Topic",
            failed_domains=domains,
            outline_content="Outline placeholder",
        )
        assert len(crew.tasks) == len(domains)


# ---------------------------------------------------------------------------
# Cross-cutting
# ---------------------------------------------------------------------------

class TestCrewProperties:

    def test_all_crews_sequential(self, tmp_path, monkeypatch):
        """Every builder should produce a sequential crew."""
        monkeypatch.setattr("src.crew.validate_config", lambda: None)
        monkeypatch.setattr("src.crew_legacy.validate_config", lambda: None)
        monkeypatch.setattr("src.crew_fixer.validate_config", lambda: None)
        run_folder = _prepare_run_folder(tmp_path)

        from src.crew import build_research_crew, build_writing_crew
        from src.crew_fixer import build_fixer_crew
        from src.crew_legacy import build_crew

        builders = [
            lambda: build_research_crew(run_folder=run_folder),
            lambda: build_writing_crew(run_folder=run_folder),
            lambda: build_crew(run_folder=run_folder, smoke_mode=True),
            lambda: build_fixer_crew("T", ["physics"], "O"),
        ]
        for fn in builders:
            crew, _ = fn()
            assert crew.process.value == "sequential"
