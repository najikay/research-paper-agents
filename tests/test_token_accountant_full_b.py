"""
tests/test_token_accountant_full_b.py
======================================
TokenAccountant tests: record, LiteLLM callback, finalize, report, save.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import src.utils.token_accountant as ta_module
from src.utils.token_accountant import TokenAccountant, TokenUsageRecord


def test_record_attributes_to_current_context():
    """record() under a context must populate total, per_agent and per_task."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Author", task_name="latex_task")
    acc.record(120, 80)
    assert acc.total.total_tokens == 200
    assert acc.per_agent["Author"].input_tokens == 120
    assert acc.per_task["latex_task"].total_tokens == 200


def test_litellm_callback_object_usage():
    """The callback must extract token counts from an object-shaped usage."""
    acc = TokenAccountant()
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=40, completion_tokens=10))
    acc._litellm_success_callback({}, response, 0, 1)
    assert acc.total.input_tokens == 40
    assert acc.total.output_tokens == 10


def test_litellm_callback_dict_usage():
    """The callback must extract token counts from a dict-shaped completion response."""
    acc = TokenAccountant()
    usage = MagicMock()
    usage.prompt_tokens = 7
    usage.completion_tokens = 3
    acc._litellm_success_callback({}, {"usage": usage}, 0, 1)
    assert acc.total.input_tokens == 7
    assert acc.total.output_tokens == 3


def test_litellm_callback_missing_usage_is_noop():
    """The callback must do nothing when no usage info is present."""
    acc = TokenAccountant()
    acc._litellm_success_callback({}, SimpleNamespace(), 0, 1)
    acc._litellm_success_callback({}, {"no_usage": True}, 0, 1)
    assert acc.total.total_tokens == 0


def test_litellm_callback_zero_tokens_is_noop():
    """The callback must skip accumulation when both token counts are zero."""
    acc = TokenAccountant()
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0))
    acc._litellm_success_callback({}, response, 0, 1)
    assert acc.total.call_count == 0


def test_litellm_callback_handles_none_token_fields():
    """The callback must coerce None token fields to 0 without error."""
    acc = TokenAccountant()
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=None, completion_tokens=12))
    acc._litellm_success_callback({}, response, 0, 1)
    assert acc.total.input_tokens == 0
    assert acc.total.output_tokens == 12


def test_litellm_callback_swallows_malformed_usage():
    """The callback must log and swallow errors from malformed usage values."""
    acc = TokenAccountant()
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens="not-a-number", completion_tokens=5))
    acc._litellm_success_callback({}, response, 0, 1)
    assert acc.total.call_count == 0


def test_accumulate_thread_safe():
    """Concurrent _accumulate() calls must produce a consistent grand total."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Worker", task_name="job")

    def worker():
        for _ in range(200):
            acc._accumulate(2, 1)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert acc.total.call_count == 1600
    assert acc.total.input_tokens == 3200


def test_finalize_none_is_noop():
    """finalize(None) must leave crew metrics unmerged."""
    acc = TokenAccountant()
    acc.finalize(None)
    assert acc.report()["crew_metrics_merged"] is False


def test_finalize_object_metrics():
    """finalize() must read fields from an object-shaped usage metric."""
    acc = TokenAccountant()
    metrics = SimpleNamespace(total_tokens=300, prompt_tokens=200, completion_tokens=100, successful_requests=4)
    acc.finalize(metrics)
    assert acc.report()["crew_metrics_merged"] is True
    assert acc.report()["crew_metrics"]["total_tokens"] == 300


def test_finalize_dict_metrics():
    """finalize() must copy a dict-shaped usage metric."""
    acc = TokenAccountant()
    acc.finalize({"total_tokens": 99, "custom": "value"})
    assert acc.report()["crew_metrics"] == {"total_tokens": 99, "custom": "value"}


def test_finalize_swallows_errors():
    """finalize() must swallow errors raised while reading metric attributes."""
    acc = TokenAccountant()

    class Boom:
        @property
        def total_tokens(self):
            raise RuntimeError("boom")

    acc.finalize(Boom())
    assert acc.report()["crew_metrics_merged"] is False


def test_report_enriches_with_pct_of_total():
    """report() must add pct_of_total to each per-agent/per-task entry."""
    acc = TokenAccountant()
    acc.set_context(agent_role="A", task_name="t1")
    acc.record(75, 0)
    acc.set_context(agent_role="B", task_name="t2")
    acc.record(25, 0)
    report = acc.report()
    assert report["per_agent"]["A"]["pct_of_total"] == 75.0
    assert report["per_agent"]["B"]["pct_of_total"] == 25.0


def test_report_markdown_contains_totals():
    """report_markdown() must contain summary totals and breakdowns."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Director", task_name="Setup")
    acc.record(1000, 500)
    md = acc.report_markdown()
    assert "# NavigatorCrew" in md
    assert "Director" in md


def test_report_markdown_empty_breakdowns():
    """report_markdown() must emit placeholders when nothing recorded."""
    acc = TokenAccountant()
    md = acc.report_markdown()
    assert "_No per-agent data recorded._" in md


def test_save_report_relative_path(tmp_path, monkeypatch):
    """save_report() with a relative path must write under PROJECT_ROOT."""
    monkeypatch.setattr(ta_module, "PROJECT_ROOT", tmp_path)
    acc = TokenAccountant()
    acc.record(10, 5)
    acc.save_report("outputs/run/token_report.md")
    dest = tmp_path / "outputs" / "run" / "token_report.md"
    assert dest.exists()


def test_save_report_absolute_path(tmp_path):
    """save_report() with an absolute path must write to exactly that path."""
    acc = TokenAccountant()
    acc.record(5, 5)
    dest = tmp_path / "abs_report.md"
    acc.save_report(str(dest))
    assert dest.exists()


def test_token_usage_record_to_dict():
    """TokenUsageRecord.to_dict() must expose all four counters."""
    rec = TokenUsageRecord()
    rec.add(10, 4)
    rec.add(6, 0)
    assert rec.to_dict() == {
        "input_tokens": 16, "output_tokens": 4,
        "total_tokens": 20, "call_count": 2,
    }
