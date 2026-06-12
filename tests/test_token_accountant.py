"""
tests/test_token_accountant.py
===============================
Unit tests for TokenAccountant in src/utils/token_accountant.py.
"""

from __future__ import annotations

import threading

from src.utils.token_accountant import REPORT_KEYS, TokenAccountant


def test_record_accumulates():
    """record() must add input and output tokens to the running total."""
    acc = TokenAccountant()
    acc.record(100, 50)
    assert acc.total.input_tokens == 100
    assert acc.total.output_tokens == 50
    assert acc.total.total_tokens == 150


def test_record_multiple_calls():
    """Multiple record() calls must accumulate across all calls."""
    acc = TokenAccountant()
    acc.record(100, 50)
    acc.record(200, 100)
    assert acc.total.input_tokens == 300
    assert acc.total.output_tokens == 150
    assert acc.total.total_tokens == 450
    assert acc.total.call_count == 2


def test_reset_clears_total():
    """reset() must zero out the total token counters."""
    acc = TokenAccountant()
    acc.record(500, 250)
    acc.reset()
    assert acc.total.input_tokens == 0
    assert acc.total.output_tokens == 0
    assert acc.total.total_tokens == 0
    assert acc.total.call_count == 0


def test_reset_clears_per_agent():
    """reset() must clear all per-agent tracking data."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Director")
    acc.record(100, 50)
    acc.reset()
    assert acc.per_agent == {}


def test_total_tokens_property():
    """The total property must return a TokenUsageRecord with correct totals."""
    acc = TokenAccountant()
    acc.record(300, 150)
    total = acc.total
    assert total.total_tokens == 450
    assert total.input_tokens == 300
    assert total.output_tokens == 150


def test_per_agent_tracking():
    """set_context() + record() must populate per_agent with the correct role."""
    acc = TokenAccountant()
    acc.set_context(agent_role="ResearchDirector")
    acc.record(100, 50)

    per_agent = acc.per_agent
    assert "ResearchDirector" in per_agent
    assert per_agent["ResearchDirector"].input_tokens == 100
    assert per_agent["ResearchDirector"].output_tokens == 50


def test_per_task_tracking():
    """set_context() with task_name must populate per_task correctly."""
    acc = TokenAccountant()
    acc.set_context(agent_role="Researcher", task_name="outline_task")
    acc.record(200, 100)

    per_task = acc.per_task
    assert "outline_task" in per_task
    assert per_task["outline_task"].input_tokens == 200


def test_report_structure():
    """report() must return a dict with all keys in REPORT_KEYS."""
    acc = TokenAccountant()
    acc.record(100, 50)
    report = acc.report()

    for key in REPORT_KEYS:
        assert key in report, f"report() missing key: {key!r}"


def test_report_markdown_contains_header():
    """report_markdown() must contain 'NavigatorCrew' as the report title."""
    acc = TokenAccountant()
    acc.record(100, 50)
    md = acc.report_markdown()
    assert "NavigatorCrew" in md


def test_report_markdown_has_tables():
    """report_markdown() must contain markdown table separators ('|')."""
    acc = TokenAccountant()
    acc.set_context(agent_role="LaTeXAuthor", task_name="latex_task")
    acc.record(100, 50)
    md = acc.report_markdown()
    assert "|" in md


def test_thread_safety():
    """10 threads each recording 100 input tokens must yield total_input == 1000."""
    acc = TokenAccountant()

    def record_tokens():
        for _ in range(100):
            acc.record(1, 0)

    threads = [threading.Thread(target=record_tokens) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert acc.total.input_tokens == 1000
    assert acc.total.call_count == 1000
