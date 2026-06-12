"""
tests/test_nodes_config_extra.py
================================
Covers the uncovered logic in src/graph/nodes.py (the research/writing crew
nodes and the programmatic validate_and_fix_research gate) and the embedder/
validation helpers in src/config.py. All crew kickoffs and network calls are
replaced with MagicMocks — no real LLM/network is touched.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import src.config as cfg
import src.graph.nodes as nodes

# ---------------------------------------------------------------------------
# Crew-running nodes — build_* is monkeypatched so kickoff() is a no-op.
# ---------------------------------------------------------------------------

def _fake_crew_builder(*args, **kwargs):
    """Return a (crew, accountant) pair whose kickoff() does nothing."""
    return MagicMock(), MagicMock()


def test_run_main_pipeline(monkeypatch):
    """Legacy node builds the crew, kickstarts it, returns PENDING verdict."""
    monkeypatch.setattr("src.crew.build_crew", _fake_crew_builder)
    out = nodes.run_main_pipeline(
        {"topic": "t", "run_folder": "rf", "fast_mode": True, "smoke_mode": False}
    )
    assert out["quality_verdict"] == "PENDING"


def test_run_research_phase(monkeypatch):
    """Research-phase node returns PENDING + zero fix count."""
    monkeypatch.setattr("src.crew.build_research_crew", _fake_crew_builder)
    out = nodes.run_research_phase({"topic": "t", "run_folder": "rf"})
    assert out["quality_verdict"] == "PENDING"
    assert out["research_fix_count"] == 0


def test_run_writing_phase(monkeypatch):
    """Writing-phase node returns PENDING verdict."""
    monkeypatch.setattr("src.crew.build_writing_crew", _fake_crew_builder)
    out = nodes.run_writing_phase({"topic": "t", "run_folder": "rf"})
    assert out["quality_verdict"] == "PENDING"


# ---------------------------------------------------------------------------
# validate_and_fix_research — programmatic file scanning.
# ---------------------------------------------------------------------------

_DOMAIN_KEYS = [
    "vision_ai", "physics", "algorithms", "aerospace", "biology",
    "signal_processing", "control_systems", "ml",
]


def _write_domains(staging, contents: dict[str, str]):
    """Write domain_<key>.md files into the staging dir for the given map."""
    staging.mkdir(parents=True, exist_ok=True)
    for key, text in contents.items():
        (staging / f"domain_{key}.md").write_text(text, encoding="utf-8")


def test_validate_research_all_valid(tmp_path, monkeypatch):
    """When every domain file is substantial, no fixer is spawned."""
    monkeypatch.setattr(nodes, "PROJECT_ROOT", tmp_path)
    staging = tmp_path / "outputs" / "current"
    good = "Valid domain analysis. " * 60  # well over 500 bytes, no loop markers
    _write_domains(staging, {k: good for k in _DOMAIN_KEYS})

    out = nodes.validate_and_fix_research({"topic": "t"})
    assert out["research_fix_count"] == 0


def test_validate_research_detects_failures_and_spawns_fixer(tmp_path, monkeypatch):
    """Missing/short/looping/stub files are flagged and the fixer crew runs."""
    monkeypatch.setattr(nodes, "PROJECT_ROOT", tmp_path)
    staging = tmp_path / "outputs" / "current"

    good = "Valid domain analysis. " * 60
    contents = {
        "vision_ai": good,
        "physics": "tiny",                                    # too small (<500 bytes)
        "algorithms": ("Let me read the file. " * 3) + good,  # loop pattern (>=3)
        "aerospace": "DOMAIN SKIP",                           # shortcut stub
        "biology": good,
        "signal_processing": good,
        "control_systems": good,
        # "ml" intentionally missing -> counts as a failure
    }
    _write_domains(staging, contents)
    # outline file the fixer reads
    (staging / "paper_outline.md").write_text("# Outline\nCh1\n", encoding="utf-8")

    fake_crew = MagicMock()
    captured = {}

    def _fake_fixer(topic, failed_domains, outline_content):
        captured["failed"] = failed_domains
        return fake_crew, MagicMock()

    monkeypatch.setattr("src.crew.build_fixer_crew", _fake_fixer)

    out = nodes.validate_and_fix_research({"topic": "bat nav"})

    # physics, algorithms, aerospace, ml = 4 failures
    assert out["research_fix_count"] == 4
    assert set(captured["failed"]) == {"physics", "algorithms", "aerospace", "ml"}
    fake_crew.kickoff.assert_called_once()


# ---------------------------------------------------------------------------
# config.py — embedder + key + validation helpers.
# ---------------------------------------------------------------------------

def test_openai_key_is_real(monkeypatch):
    """Only an 'sk-'-prefixed non-empty key counts as real."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "")
    assert cfg._openai_key_is_real() is False
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "placeholder")
    assert cfg._openai_key_is_real() is False
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "sk-realkey123")
    assert cfg._openai_key_is_real() is True


def test_get_embedder_config_with_real_key(monkeypatch):
    """A real OpenAI key yields the openai embedder provider dict."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "sk-realkey123")
    conf = cfg.get_embedder_config()
    assert conf["provider"] == "openai"
    assert conf["config"]["api_key"] == "sk-realkey123"


def test_get_embedder_config_without_key(monkeypatch):
    """No real key -> None (caller disables crew memory)."""
    monkeypatch.setattr(cfg, "OPENAI_API_KEY", "")
    assert cfg.get_embedder_config() is None


def test_validate_config_passes_deepseek(monkeypatch):
    """DeepSeek provider with both keys present validates without raising."""
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "ds-key")
    monkeypatch.setenv("SERPER_API_KEY", "serper-key")
    cfg.validate_config()  # must not raise


def test_validate_config_missing_provider_key_raises(monkeypatch):
    """Missing the active provider's key raises OSError."""
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("SERPER_API_KEY", "serper-key")
    with pytest.raises(OSError):
        cfg.validate_config()


def test_validate_config_missing_serper_raises(monkeypatch):
    """Missing SERPER_API_KEY raises OSError regardless of provider."""
    monkeypatch.setattr(cfg, "ACTIVE_PROVIDER", "deepseek")
    monkeypatch.setattr(cfg, "DEEPSEEK_API_KEY", "ds-key")
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    with pytest.raises(OSError):
        cfg.validate_config()
