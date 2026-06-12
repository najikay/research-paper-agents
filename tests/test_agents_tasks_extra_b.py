"""
test_agents_tasks_extra_b.py
============================
Split from test_agents_tasks_extra.py.
"""

from __future__ import annotations
import pytest
from src.agents import (
from src.tasks.tasks_assemble import (
from src.tasks.tasks_domain import create_task_domain_expert, create_task_fix_domain
from src.tasks.tasks_latex_split import (
from src.tasks.tasks_remediate import create_remediation_task, create_task_review
from src.tasks.tasks_smoke import create_smoke_tasks, create_task_latex_smoke


def test_create_remediation_task_no_run_folder(real_agent):
    """No run_folder -> paths_note stays empty (covers the falsy branch)."""
    task = create_remediation_task(
        real_agent,
        failed_sections=["methodology", "equations"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
    )
    _assert_valid_task(task)
    assert "methodology" in task.description
    assert "equations" in task.description


def test_create_remediation_task_with_run_folder(real_agent, tmp_path):
    """run_folder set -> paths_note is built (covers lines 54-80)."""
    task = create_remediation_task(
        real_agent,
        failed_sections=["algorithms"],
        quality_report_path="outputs/current/quality_report.md",
        output_file="outputs/current/remediation_status.md",
        run_folder=tmp_path,
    )
    _assert_valid_task(task)
    assert str(tmp_path) in task.description
    assert "algorithms" in task.description


# ---------------------------------------------------------------------------
# (b) tasks_smoke.py — single combined smoke task + 2-task pipeline.
# ---------------------------------------------------------------------------

def test_create_task_latex_smoke_default(real_agent):
    task = create_task_latex_smoke(real_agent, context=[])
    _assert_valid_task(task)


def test_create_task_latex_smoke_run_folder(real_agent, tmp_path):
    task = create_task_latex_smoke(real_agent, context=[], run_folder=tmp_path)
    _assert_valid_task(task)
    assert str(tmp_path) in task.description


def test_create_smoke_tasks(real_agent, tmp_path):
    """2-task smoke pipeline: outline -> latex_all (covers lines 96-98)."""
    tasks = create_smoke_tasks(
        real_agent, real_agent, topic="bat-inspired drone navigation", run_folder=tmp_path
    )
    assert len(tasks) == 2
    for task in tasks:
        _assert_valid_task(task)


# ---------------------------------------------------------------------------
# (b) tasks_domain.py — domain expert + domain fix.
# ---------------------------------------------------------------------------

def test_create_task_domain_expert(real_agent):
    task = create_task_domain_expert(
        real_agent, "algorithms", "EKF/UKF/particle filters", context=[]
    )
    _assert_valid_task(task)


def test_create_task_fix_domain(real_agent):
    """Covers lines 99-100 — _DOMAIN_DESCRIPTIONS lookup + Task build."""
    task = create_task_fix_domain(
        real_agent,
        domain_key="physics",
        topic="bat-inspired drone navigation",
        outline_content="# Outline\nChapter 1 ...",
    )
    _assert_valid_task(task)
    assert "physics" in task.description.lower() or "physics" in task.expected_output


# ---------------------------------------------------------------------------
# (b) tasks_assemble.py — crew-building helpers.
# ---------------------------------------------------------------------------

def test_create_research_tasks(real_agent):
    """outline -> research -> N domain expert tasks (covers lines 35-44)."""
    domain_experts = {
        "vision_ai": real_agent,
        "physics": real_agent,
        "algorithms": real_agent,
        "aerospace": real_agent,
        "biology": real_agent,
    }
    tasks = create_research_tasks(
        real_agent, real_agent, domain_experts, topic="bat navigation"
    )
    # outline + research + 5 domain tasks
    assert len(tasks) == 2 + len(domain_experts)
    for task in tasks:
        _assert_valid_task(task)


def test_create_writing_tasks(real_agent, tmp_path):
    """figures -> hebrew_prose -> latex_a/b/c (covers lines 56-61)."""
    tasks = create_writing_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, run_folder=tmp_path
    )
    assert len(tasks) == 5
    for task in tasks:
        _assert_valid_task(task)


def test_create_all_tasks_fast_mode(real_agent, tmp_path):
    """fast_mode=True skips domain experts (covers lines 95-96)."""
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation",
        run_folder=tmp_path,
        fast_mode=True,
    )
    # outline, research, figures, hebrew, latex1, latex2 = 6 tasks (no domain experts)
    assert len(tasks) == 6
    for task in tasks:
        _assert_valid_task(task)


def test_create_all_tasks_full_mode(real_agent, tmp_path):
    """fast_mode=False builds the full 11-task pipeline including domain experts."""
    tasks = create_all_tasks(
        real_agent, real_agent, real_agent, real_agent, real_agent, real_agent,
        real_agent, real_agent, real_agent, real_agent,
        topic="bat navigation",
        run_folder=tmp_path,
        fast_mode=False,
    )
    # outline, research, 5 domain, figures, hebrew, latex1, latex2 = 11 tasks
    assert len(tasks) == 11
    for task in tasks:
        _assert_valid_task(task)
