"""
src/utils/token_accountant.py
==============================
TokenAccountant — captures and reports LLM token usage for the entire crew run.
"""

from __future__ import annotations

import threading
from typing import Any

from src.config import logger

# Re-export from split modules (backward compatibility)
from src.utils.token_types import REPORT_KEYS, TokenUsageRecord  # noqa: F401
from src.utils.token_reporter import build_report, format_markdown, save_report


class TokenAccountant:
    """Tracks token consumption across all LLM calls made during a crew run."""

    def __init__(self) -> None:
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
        """Set the current agent/task context for attribution."""
        self._current_agent = agent_role
        self._current_task = task_name

    # ------------------------------------------------------------------
    # CrewAI callbacks
    # ------------------------------------------------------------------

    def step_callback(self, step_output: Any) -> None:
        """CrewAI step hook: update the current agent role."""
        try:
            if hasattr(step_output, "agent_role"):
                self._current_agent = str(step_output.agent_role)
            elif hasattr(step_output, "agent") and hasattr(step_output.agent, "role"):
                self._current_agent = str(step_output.agent.role)
        except Exception:
            pass

    def task_callback(self, task_output: Any) -> None:
        """CrewAI task hook: update the current task name."""
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
        """LiteLLM success callback: extract and accumulate token counts."""
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
        """Thread-safely add tokens to the grand total and current agent/task records."""
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
        """Merge CrewAI's own usage metrics into the report."""
        if crew_usage_metrics is None:
            return
        try:
            if hasattr(crew_usage_metrics, "total_tokens"):
                self._crew_metrics = {"total_tokens": crew_usage_metrics.total_tokens, "prompt_tokens": getattr(crew_usage_metrics, "prompt_tokens", None), "completion_tokens": getattr(crew_usage_metrics, "completion_tokens", None), "successful_requests": getattr(crew_usage_metrics, "successful_requests", None)}
            elif isinstance(crew_usage_metrics, dict):
                self._crew_metrics = dict(crew_usage_metrics)
        except Exception as exc:
            logger.warning(f"TokenAccountant: could not parse crew_usage_metrics: {exc}")

    # ------------------------------------------------------------------
    # Reporting (delegates to token_reporter module)
    # ------------------------------------------------------------------

    @property
    def total(self) -> TokenUsageRecord:
        """Return the grand-total token usage record."""
        return self._total

    @property
    def per_agent(self) -> dict[str, TokenUsageRecord]:
        """Return a copy of the per-agent token usage records."""
        return dict(self._per_agent)

    @property
    def per_task(self) -> dict[str, TokenUsageRecord]:
        """Return a copy of the per-task token usage records."""
        return dict(self._per_task)

    def report(self) -> dict:
        """Build a structured report dict."""
        with self._lock:
            return build_report(
                self._total, dict(self._per_agent),
                dict(self._per_task), self._crew_metrics,
            )

    def report_markdown(self) -> str:
        """Render the report as a Markdown document."""
        return format_markdown(self.report())

    def save_report(self, path: str = "outputs/current/token_report.md") -> None:
        """Write the Markdown report to path."""
        save_report(self.report(), path)
