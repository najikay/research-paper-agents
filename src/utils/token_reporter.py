"""
src/utils/token_reporter.py
============================
Markdown/dict report formatting for token usage data.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import PROJECT_ROOT, logger

if TYPE_CHECKING:
    from src.utils.token_types import TokenUsageRecord


def build_report(
    total: TokenUsageRecord,
    per_agent: dict[str, TokenUsageRecord],
    per_task: dict[str, TokenUsageRecord],
    crew_metrics: dict | None,
) -> dict:
    """Build a structured report dict from token usage records."""
    total_dict = total.to_dict()
    grand_total = total.total_tokens or 1

    def _enrich(rec: TokenUsageRecord) -> dict:
        d = rec.to_dict()
        d["pct_of_total"] = round(rec.total_tokens / grand_total * 100, 1)
        return d

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "crew_metrics_merged": crew_metrics is not None,
        "total": total_dict,
        "per_agent": {role: _enrich(rec) for role, rec in per_agent.items()},
        "per_task": {task: _enrich(rec) for task, rec in per_task.items()},
        "crew_metrics": crew_metrics,
    }


def format_markdown(data: dict) -> str:
    """Render a token report dict as a Markdown table string."""
    t = data["total"]
    lines = [
        "# NavigatorCrew — Token Usage Report",
        f"Generated: {data['generated_at']}",
        f"CrewAI metrics merged: {'Yes' if data['crew_metrics_merged'] else 'No'}",
        "",
        "## Summary",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total input tokens  | {t['input_tokens']:,} |",
        f"| Total output tokens | {t['output_tokens']:,} |",
        f"| **Grand total**     | **{t['total_tokens']:,}** |",
        f"| LLM calls           | {t['call_count']:,} |",
        "",
        "## Tokens per Agent",
    ]

    if data["per_agent"]:
        lines += [
            "| Agent | Input | Output | Total | % of Run | Calls |",
            "|-------|-------|--------|-------|----------|-------|",
        ]
        for role, rec in sorted(
            data["per_agent"].items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True,
        ):
            lines.append(
                f"| {role} | {rec['input_tokens']:,} | {rec['output_tokens']:,} "
                f"| {rec['total_tokens']:,} | {rec['pct_of_total']:.1f}% | {rec['call_count']} |"
            )
    else:
        lines.append("_No per-agent data recorded._")

    lines += ["", "## Tokens per Task"]
    if data["per_task"]:
        lines += [
            "| Task | Input | Output | Total | % of Run | Calls |",
            "|------|-------|--------|-------|----------|-------|",
        ]
        for task, rec in sorted(
            data["per_task"].items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True,
        ):
            lines.append(
                f"| {task[:50]} | {rec['input_tokens']:,} | {rec['output_tokens']:,} "
                f"| {rec['total_tokens']:,} | {rec['pct_of_total']:.1f}% | {rec['call_count']} |"
            )
    else:
        lines.append("_No per-task data recorded._")

    return "\n".join(lines)


def save_report(data: dict, path: str = "outputs/current/token_report.md") -> None:
    """Save a markdown-formatted token report to disk."""
    raw = Path(path)
    dest = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(format_markdown(data), encoding="utf-8")
    logger.info(f"TokenAccountant: report saved to {dest}")
