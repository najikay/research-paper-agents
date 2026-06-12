"""
src/utils/token_accountant.py
==============================
TokenAccountant — captures and reports LLM token usage for the entire crew run.
"""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, logger

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

REPORT_KEYS: frozenset[str] = frozenset(
    {"total", "per_agent", "per_task", "generated_at", "crew_metrics_merged"}
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TokenUsageRecord:
    """Accumulator for a single agent or task."""

    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0

    @property
    def total_tokens(self) -> int:
        """Return the sum of input and output tokens."""
        return self.input_tokens + self.output_tokens

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add one call's input/output tokens and increment the call count."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1

    def to_dict(self) -> dict[str, int]:
        """Return this record's counts as a serializable dict."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
        }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TokenAccountant:
    """
    Tracks token consumption across all LLM calls made during a crew run.
    """

    def __init__(self) -> None:
        """Initialize empty grand-total, per-agent, and per-task token records, the current agent/task context, the installed-callback flag, and optional CrewAI metrics, guarded by a lock."""
        self._lock = threading.Lock()
        self._total = TokenUsageRecord()
        self._per_agent: dict[str, TokenUsageRecord] = {}
        self._per_task: dict[str, TokenUsageRecord] = {}
        self._current_agent: str | None = None
        self._current_task: str | None = None
        self._installed: bool = False
        self._crew_metrics: dict | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Register this accountant as a LiteLLM success callback."""
        if self._installed:
            return
        try:
            import litellm  # type: ignore[import]
            litellm.success_callback.append(self._litellm_success_callback)
            self._installed = True
            logger.info("TokenAccountant: LiteLLM callback installed.")
        except ImportError:
            logger.warning("TokenAccountant: litellm not importable.")

    def uninstall(self) -> None:
        """Remove the LiteLLM callback."""
        if not self._installed:
            return
        try:
            import litellm  # type: ignore[import]
            if self._litellm_success_callback in litellm.success_callback:
                litellm.success_callback.remove(self._litellm_success_callback)
            self._installed = False
            logger.info("TokenAccountant: LiteLLM callback removed.")
        except ImportError:
            pass

    def reset(self) -> None:
        """Clear all accumulated counts."""
        with self._lock:
            self._total = TokenUsageRecord()
            self._per_agent.clear()
            self._per_task.clear()
            self._current_agent = None
            self._current_task = None
            self._crew_metrics = None
        logger.debug("TokenAccountant: counters reset.")

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def set_context(self, agent_role: str | None = None, task_name: str | None = None) -> None:
        """Set the current agent role and task name that subsequent recordings are attributed to."""
        self._current_agent = agent_role
        self._current_task = task_name

    # ------------------------------------------------------------------
    # CrewAI callbacks
    # ------------------------------------------------------------------

    def step_callback(self, step_output: Any) -> None:
        """CrewAI step hook: update the current agent role from the step output, ignoring any extraction errors."""
        try:
            if hasattr(step_output, "agent_role"):
                self._current_agent = str(step_output.agent_role)
            elif hasattr(step_output, "agent") and hasattr(step_output.agent, "role"):
                self._current_agent = str(step_output.agent.role)
        except Exception:
            pass

    def task_callback(self, task_output: Any) -> None:
        """CrewAI task hook: update the current task name (and agent role, if present) from the task output, ignoring any extraction errors."""
        try:
            task_name = None
            if hasattr(task_output, "description"):
                task_name = str(task_output.description)[:60].strip()
            elif hasattr(task_output, "name"):
                task_name = str(task_output.name)

            if task_name:
                self._current_task = task_name

            if hasattr(task_output, "agent") and task_output.agent:
                agent = task_output.agent
                if hasattr(agent, "role"):
                    self._current_agent = str(agent.role)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, input_tokens: int, output_tokens: int) -> None:
        """Manually record token usage for the current agent/task context."""
        self._accumulate(input_tokens, output_tokens)

    def _litellm_success_callback(self, kwargs: dict, completion_response: Any, start_time: Any, end_time: Any) -> None:
        """LiteLLM success callback: extract prompt/completion token counts from the completion response and accumulate them, logging and swallowing any errors."""
        try:
            usage = getattr(completion_response, "usage", None)
            if usage is None and isinstance(completion_response, dict):
                usage = completion_response.get("usage")

            if usage is None:
                return

            input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

            if input_tokens == 0 and output_tokens == 0:
                return

            self._accumulate(input_tokens, output_tokens)
        except Exception as exc:
            logger.warning(f"TokenAccountant: error in LiteLLM callback: {exc}")

    def _accumulate(self, input_tokens: int, output_tokens: int) -> None:
        """Thread-safely add the given tokens to the grand total and to the current agent/task records (creating them on first use)."""
        with self._lock:
            self._total.add(input_tokens, output_tokens)
            if self._current_agent:
                if self._current_agent not in self._per_agent:
                    self._per_agent[self._current_agent] = TokenUsageRecord()
                self._per_agent[self._current_agent].add(input_tokens, output_tokens)
            if self._current_task:
                if self._current_task not in self._per_task:
                    self._per_task[self._current_task] = TokenUsageRecord()
                self._per_task[self._current_task].add(input_tokens, output_tokens)

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def finalize(self, crew_usage_metrics: Any | None = None) -> None:
        """Merge CrewAI's own usage metrics (object or dict) into the report, ignoring errors; does nothing if none are provided."""
        if crew_usage_metrics is None:
            return
        try:
            if hasattr(crew_usage_metrics, "total_tokens"):
                self._crew_metrics = {
                    "total_tokens": crew_usage_metrics.total_tokens,
                    "prompt_tokens": getattr(crew_usage_metrics, "prompt_tokens", None),
                    "completion_tokens": getattr(crew_usage_metrics, "completion_tokens", None),
                    "successful_requests": getattr(crew_usage_metrics, "successful_requests", None),
                }
            elif isinstance(crew_usage_metrics, dict):
                self._crew_metrics = dict(crew_usage_metrics)
        except Exception as exc:
            logger.warning(f"TokenAccountant: could not parse crew_usage_metrics: {exc}")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @property
    def total(self) -> TokenUsageRecord:
        """Return the grand-total token usage record for the run."""
        return self._total

    @property
    def per_agent(self) -> dict[str, TokenUsageRecord]:
        """Return a copy of the per-agent token usage records keyed by role."""
        return dict(self._per_agent)

    @property
    def per_task(self) -> dict[str, TokenUsageRecord]:
        """Return a copy of the per-task token usage records keyed by task name."""
        return dict(self._per_task)

    def report(self) -> dict:
        """Build a structured report dict with totals, per-agent and per-task breakdowns (each enriched with a percent-of-total), a timestamp, and any merged CrewAI metrics."""
        with self._lock:
            total_dict = self._total.to_dict()
            grand_total = self._total.total_tokens or 1

            def _enrich(rec: TokenUsageRecord) -> dict:
                """Return the record as a dict with an added pct_of_total field relative to the grand total."""
                d = rec.to_dict()
                d["pct_of_total"] = round(rec.total_tokens / grand_total * 100, 1)
                return d

            agent_dict = {role: _enrich(rec) for role, rec in self._per_agent.items()}
            task_dict  = {task: _enrich(rec) for task, rec in self._per_task.items()}

            return {
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "crew_metrics_merged": self._crew_metrics is not None,
                "total": total_dict,
                "per_agent": agent_dict,
                "per_task": task_dict,
                "crew_metrics": self._crew_metrics,
            }

    def report_markdown(self) -> str:
        """Render the report as a Markdown document with summary, per-agent, and per-task tables."""
        data = self.report()
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
            lines += ["| Agent | Input | Output | Total | % of Run | Calls |", "|-------|-------|--------|-------|----------|-------|"]
            for role, rec in sorted(data["per_agent"].items(), key=lambda x: x[1]["total_tokens"], reverse=True):
                lines.append(f"| {role} | {rec['input_tokens']:,} | {rec['output_tokens']:,} | {rec['total_tokens']:,} | {rec['pct_of_total']:.1f}% | {rec['call_count']} |")
        else:
            lines.append("_No per-agent data recorded._")

        lines += ["", "## Tokens per Task"]
        if data["per_task"]:
            lines += ["| Task | Input | Output | Total | % of Run | Calls |", "|------|-------|--------|-------|----------|-------|"]
            for task, rec in sorted(data["per_task"].items(), key=lambda x: x[1]["total_tokens"], reverse=True):
                lines.append(f"| {task[:50]} | {rec['input_tokens']:,} | {rec['output_tokens']:,} | {rec['total_tokens']:,} | {rec['pct_of_total']:.1f}% | {rec['call_count']} |")
        else:
            lines.append("_No per-task data recorded._")

        return "\n".join(lines)

    def save_report(self, path: str = "outputs/current/token_report.md") -> None:
        """Write the Markdown report to path (resolved relative to PROJECT_ROOT if not absolute), creating parent directories as needed."""
        raw = Path(path)
        dest = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self.report_markdown(), encoding="utf-8")
        logger.info(f"TokenAccountant: report saved to {dest}")

if __name__ == "__main__":
    acc = TokenAccountant()
    acc.set_context(agent_role="Director", task_name="Setup")
    acc.record(100, 50)
    print(acc.report_markdown())
