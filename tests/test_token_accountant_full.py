"""
tests/test_token_accountant_full.py
====================================
Unit tests for TokenAccountant: lifecycle, CrewAI callbacks, step/task hooks.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

from src.utils.token_accountant import TokenAccountant


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
    monkeypatch.setitem(sys.modules, "litellm", None)
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
    acc.uninstall()
    assert acc._installed is False


def test_uninstall_handles_missing_litellm(monkeypatch):
    """uninstall() must swallow ImportError when litellm vanishes after install."""
    fake = _make_fake_litellm(monkeypatch)
    acc = TokenAccountant()
    acc.install()
    monkeypatch.setitem(sys.modules, "litellm", None)
    acc.uninstall()
    assert acc._installed is True
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


def test_set_context_sets_both_fields():
    """set_context() must store agent_role and task_name verbatim."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Researcher", task_name="outline")
    assert acc._current_agent == "Researcher"
    assert acc._current_task == "outline"


def test_step_callback_reads_agent_role_attribute():
    """step_callback() must read a direct agent_role attribute."""
    acc = TokenAccountant()
    acc.step_callback(SimpleNamespace(agent_role="DirectAgent"))
    assert acc._current_agent == "DirectAgent"


def test_step_callback_reads_nested_agent_role():
    """step_callback() must fall back to step.agent.role."""
    acc = TokenAccountant()
    acc.step_callback(SimpleNamespace(agent=SimpleNamespace(role="NestedAgent")))
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

    acc.step_callback(Boom())


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
    acc.task_callback(SimpleNamespace(description="x" * 200))
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

    acc.task_callback(Boom())
