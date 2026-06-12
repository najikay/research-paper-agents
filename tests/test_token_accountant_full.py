"""
tests/test_token_accountant_full.py
====================================
Additional unit tests for TokenAccountant that exercise the lifecycle,
CrewAI callbacks, the LiteLLM success callback, finalize(), and the
report/markdown/save paths. Complements tests/test_token_accountant.py.

All tests are deterministic, offline, and use synthetic data only.
"""

from __future__ import annotations

import sys
import threading
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import src.utils.token_accountant as ta_module
from src.utils.token_accountant import TokenAccountant, TokenUsageRecord

# ---------------------------------------------------------------------------
# Lifecycle: install / uninstall / reset
# ---------------------------------------------------------------------------

def _make_fake_litellm(monkeypatch):
    """Inject a fake `litellm` module exposing a success_callback list."""
    fake = types.ModuleType("litellm")
    fake.success_callback = []
    monkeypatch.setitem(sys.modules, "litellm", fake)
    return fake


def test_install_registers_callback(monkeypatch):
    """install() must append the success callback and flip the installed flag."""
    fake = _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()

    acc.install()

    assert acc._installed is True
    assert acc._litellm_success_callback in fake.success_callback


def test_install_is_idempotent(monkeypatch):
    """A second install() must not register the callback twice."""
    fake = _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()

    acc.install()
    acc.install()

    assert fake.success_callback.count(acc._litellm_success_callback) == 1


def test_install_handles_missing_litellm(monkeypatch):
    """install() must swallow ImportError and stay uninstalled."""
    monkeypatch.setitem(sys.modules, "litellm", None)  # forces ImportError
    acc = TokenAccountant()

    acc.install()

    assert acc._installed is False


def test_uninstall_removes_callback(monkeypatch):
    """uninstall() after install() must remove the callback and clear the flag."""
    fake = _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()
    acc.install()

    acc.uninstall()

    assert acc._installed is False
    assert acc._litellm_success_callback not in fake.success_callback


def test_uninstall_when_not_installed_is_noop(monkeypatch):
    """uninstall() before install() must do nothing and not raise."""
    _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()

    acc.uninstall()  # should hit the early return

    assert acc._installed is False


def test_uninstall_handles_missing_litellm(monkeypatch):
    """uninstall() must swallow ImportError when litellm vanishes after install."""
    fake = _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()
    acc.install()
    # Now make litellm un-importable while still "installed".
    monkeypatch.setitem(sys.modules, "litellm", None)

    acc.uninstall()  # ImportError path

    # Flag remains True because the except branch is reached before clearing.
    assert acc._installed is True
    # Sanity: the real fake list still holds the callback (never removed).
    assert acc._litellm_success_callback in fake.success_callback


def test_reset_clears_context_and_metrics():
    """reset() must clear context, per-task data, and merged crew metrics."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Director", task_name="Setup")
    acc.record(100, 50)
    acc.finalize({"total_tokens": 5})

    acc.reset()

    assert acc.total.total_tokens == 0
    assert acc.per_agent == {}
    assert acc.per_task == {}
    assert acc._current_agent is None
    assert acc._current_task is None
    assert acc.report()["crew_metrics_merged"] is False


# ---------------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------------

def test_set_context_sets_both_fields():
    """set_context() must store agent_role and task_name verbatim."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Researcher", task_name="outline")
    assert acc._current_agent == "Researcher"
    assert acc._current_task == "outline"


# ---------------------------------------------------------------------------
# CrewAI step_callback
# ---------------------------------------------------------------------------

def test_step_callback_reads_agent_role_attribute():
    """step_callback() must read a direct agent_role attribute."""
    acc = TokenAccountant()
    step = SimpleNamespace(agent_role="DirectAgent")

    acc.step_callback(step)

    assert acc._current_agent == "DirectAgent"


def test_step_callback_reads_nested_agent_role():
    """step_callback() must fall back to step.agent.role."""
    acc = TokenAccountant()
    step = SimpleNamespace(agent=SimpleNamespace(role="NestedAgent"))

    acc.step_callback(step)

    assert acc._current_agent == "NestedAgent"


def test_step_callback_ignores_unrecognized_object():
    """step_callback() must leave context untouched for objects with no role info."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Original")

    acc.step_callback(SimpleNamespace(foo="bar"))

    assert acc._current_agent == "Original"


def test_step_callback_swallows_exceptions():
    """step_callback() must swallow exceptions raised during attribute access."""
    acc = TokenAccountant()

    class Boom:
        @property
        def agent_role(self):
            raise RuntimeError("boom")

    acc.step_callback(Boom())  # must not raise


# ---------------------------------------------------------------------------
# CrewAI task_callback
# ---------------------------------------------------------------------------

def test_task_callback_reads_description_and_agent():
    """task_callback() must derive task name from description and read agent.role."""
    acc = TokenAccountant()
    task = SimpleNamespace(
        description="  Write the introduction section of the paper  ",
        agent=SimpleNamespace(role="Writer"),
    )

    acc.task_callback(task)

    assert acc._current_task == "Write the introduction section of the paper"[:60].strip()
    assert acc._current_agent == "Writer"


def test_task_callback_truncates_long_description():
    """task_callback() must truncate the description to 60 chars."""
    acc = TokenAccountant()
    long_desc = "x" * 200
    acc.task_callback(SimpleNamespace(description=long_desc))

    assert acc._current_task == "x" * 60


def test_task_callback_reads_name_when_no_description():
    """task_callback() must use the name attribute when description is absent."""
    acc = TokenAccountant()
    acc.task_callback(SimpleNamespace(name="named_task"))

    assert acc._current_task == "named_task"


def test_task_callback_swallows_exceptions():
    """task_callback() must swallow exceptions during extraction."""
    acc = TokenAccountant()

    class Boom:
        @property
        def description(self):
            raise RuntimeError("boom")

    acc.task_callback(Boom())  # must not raise


# ---------------------------------------------------------------------------
# record() + per-agent / per-task attribution
# ---------------------------------------------------------------------------

def test_record_attributes_to_current_context():
    """record() under a context must populate total, per_agent and per_task."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Author", task_name="latex_task")
    acc.record(120, 80)

    assert acc.total.total_tokens == 200
    assert acc.per_agent["Author"].input_tokens == 120
    assert acc.per_agent["Author"].output_tokens == 80
    assert acc.per_task["latex_task"].total_tokens == 200


# ---------------------------------------------------------------------------
# _litellm_success_callback
# ---------------------------------------------------------------------------

def test_litellm_callback_object_usage():
    """The callback must extract token counts from an object-shaped usage."""
    acc = TokenAccountant()
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=40, completion_tokens=10)
    )

    acc._litellm_success_callback({}, response, 0, 1)

    assert acc.total.input_tokens == 40
    assert acc.total.output_tokens == 10
    assert acc.total.call_count == 1


def test_litellm_callback_dict_usage():
    """The callback must extract token counts from a dict-shaped completion response."""
    acc = TokenAccountant()
    usage = MagicMock()
    usage.prompt_tokens = 7
    usage.completion_tokens = 3
    response = {"usage": usage}

    acc._litellm_success_callback({}, response, 0, 1)

    assert acc.total.input_tokens == 7
    assert acc.total.output_tokens == 3


def test_litellm_callback_missing_usage_is_noop():
    """The callback must do nothing when no usage info is present."""
    acc = TokenAccountant()

    acc._litellm_success_callback({}, SimpleNamespace(), 0, 1)
    acc._litellm_success_callback({}, {"no_usage": True}, 0, 1)

    assert acc.total.total_tokens == 0
    assert acc.total.call_count == 0


def test_litellm_callback_zero_tokens_is_noop():
    """The callback must skip accumulation when both token counts are zero."""
    acc = TokenAccountant()
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0)
    )

    acc._litellm_success_callback({}, response, 0, 1)

    assert acc.total.call_count == 0


def test_litellm_callback_handles_none_token_fields():
    """The callback must coerce None token fields to 0 without error."""
    acc = TokenAccountant()
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=None, completion_tokens=12)
    )

    acc._litellm_success_callback({}, response, 0, 1)

    assert acc.total.input_tokens == 0
    assert acc.total.output_tokens == 12


def test_litellm_callback_swallows_malformed_usage():
    """The callback must log and swallow errors from malformed usage values."""
    acc = TokenAccountant()
    # prompt_tokens that cannot be int()-ed triggers the except branch.
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens="not-a-number", completion_tokens=5)
    )

    acc._litellm_success_callback({}, response, 0, 1)  # must not raise

    assert acc.total.call_count == 0


# ---------------------------------------------------------------------------
# _accumulate thread safety
# ---------------------------------------------------------------------------

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

    expected_calls = 8 * 200
    assert acc.total.call_count == expected_calls
    assert acc.total.input_tokens == expected_calls * 2
    assert acc.total.output_tokens == expected_calls * 1
    assert acc.per_agent["Worker"].call_count == expected_calls
    assert acc.per_task["job"].call_count == expected_calls


# ---------------------------------------------------------------------------
# finalize()
# ---------------------------------------------------------------------------

def test_finalize_none_is_noop():
    """finalize(None) must leave crew metrics unmerged."""
    acc = TokenAccountant()
    acc.finalize(None)
    assert acc.report()["crew_metrics_merged"] is False
    assert acc.report()["crew_metrics"] is None


def test_finalize_object_metrics():
    """finalize() must read fields from an object-shaped usage metric."""
    acc = TokenAccountant()
    metrics = SimpleNamespace(
        total_tokens=300,
        prompt_tokens=200,
        completion_tokens=100,
        successful_requests=4,
    )

    acc.finalize(metrics)

    report = acc.report()
    assert report["crew_metrics_merged"] is True
    assert report["crew_metrics"] == {
        "total_tokens": 300,
        "prompt_tokens": 200,
        "completion_tokens": 100,
        "successful_requests": 4,
    }


def test_finalize_object_metrics_partial_fields():
    """finalize() must default missing optional fields to None for objects."""
    acc = TokenAccountant()
    metrics = SimpleNamespace(total_tokens=50)  # only total_tokens present

    acc.finalize(metrics)

    cm = acc.report()["crew_metrics"]
    assert cm["total_tokens"] == 50
    assert cm["prompt_tokens"] is None
    assert cm["completion_tokens"] is None
    assert cm["successful_requests"] is None


def test_finalize_dict_metrics():
    """finalize() must copy a dict-shaped usage metric."""
    acc = TokenAccountant()
    metrics = {"total_tokens": 99, "custom": "value"}

    acc.finalize(metrics)

    report = acc.report()
    assert report["crew_metrics_merged"] is True
    assert report["crew_metrics"] == {"total_tokens": 99, "custom": "value"}


def test_finalize_swallows_errors():
    """finalize() must swallow errors raised while reading metric attributes."""
    acc = TokenAccountant()

    class Boom:
        @property
        def total_tokens(self):
            raise RuntimeError("boom")

    acc.finalize(Boom())  # must not raise

    assert acc.report()["crew_metrics_merged"] is False


# ---------------------------------------------------------------------------
# report() / _enrich / report_markdown()
# ---------------------------------------------------------------------------

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
    assert report["per_task"]["t1"]["pct_of_total"] == 75.0
    assert "generated_at" in report


def test_report_markdown_contains_totals_and_breakdowns():
    """report_markdown() must contain summary totals and per-agent/per-task rows."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Director", task_name="Setup")
    acc.record(1000, 500)

    md = acc.report_markdown()

    assert "# NavigatorCrew" in md
    assert "## Summary" in md
    assert "## Tokens per Agent" in md
    assert "## Tokens per Task" in md
    assert "1,500" in md  # grand total formatted with thousands separator
    assert "Director" in md
    assert "Setup" in md


def test_report_markdown_empty_breakdowns():
    """report_markdown() must emit the empty-data placeholders when nothing recorded."""
    acc = TokenAccountant()

    md = acc.report_markdown()

    assert "_No per-agent data recorded._" in md
    assert "_No per-task data recorded._" in md


# ---------------------------------------------------------------------------
# save_report()
# ---------------------------------------------------------------------------

def test_save_report_relative_path(tmp_path, monkeypatch):
    """save_report() with a relative path must write under PROJECT_ROOT."""
    monkeypatch.setattr(ta_module, "PROJECT_ROOT", tmp_path)
    acc = TokenAccountant()
    acc.set_context(agent_role="Author", task_name="latex")
    acc.record(10, 5)

    acc.save_report("outputs/run/token_report.md")

    dest = tmp_path / "outputs" / "run" / "token_report.md"
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "NavigatorCrew" in content
    assert "Author" in content


def test_save_report_absolute_path(tmp_path):
    """save_report() with an absolute path must write to exactly that path."""
    acc = TokenAccountant()
    acc.record(5, 5)
    dest = tmp_path / "abs_report.md"

    acc.save_report(str(dest))

    assert dest.exists()
    assert "Grand total" in dest.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TokenUsageRecord helpers (used indirectly above, asserted directly here)
# ---------------------------------------------------------------------------

def test_token_usage_record_to_dict():
    """TokenUsageRecord.to_dict() must expose all four counters."""
    rec = TokenUsageRecord()
    rec.add(10, 4)
    rec.add(6, 0)

    assert rec.to_dict() == {
        "input_tokens": 16,
        "output_tokens": 4,
        "total_tokens": 20,
        "call_count": 2,
    }
