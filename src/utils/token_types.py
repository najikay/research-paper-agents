"""
src/utils/token_types.py
=========================
Shared data structures for the token-accounting subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass

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
        """Sum of input and output tokens."""
        return self.input_tokens + self.output_tokens

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add a single LLM call's token counts."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1

    def to_dict(self) -> dict[str, int]:
        """Serialise to a plain dict."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
        }
