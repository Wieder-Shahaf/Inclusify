"""
Per-request vLLM inference metrics collector.

A CallMetrics instance is created at the start of each analysis request,
passed into every analyze_sentence() call, and returned up to the router
for DB persistence. It is never shared across requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CallMetrics:
    """Accumulates vLLM call statistics for a single analysis request."""

    total_sentences: int = 0
    llm_calls: int = 0
    llm_successes: int = 0
    llm_errors: int = 0
    llm_timeouts: int = 0
    circuit_breaker_trips: int = 0
    _latencies_ms: list[float] = field(default_factory=list, repr=False)

    def record_call(
        self,
        latency_ms: float,
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        """Record the outcome of one vLLM call.

        Args:
            latency_ms: Wall-clock time for the call in milliseconds.
            success: True if the call returned a usable result.
            error_type: One of "timeout", "circuit_breaker", "http_error",
                        "parse_error", or None (general error). Ignored when
                        success=True.
        """
        self.llm_calls += 1
        if success:
            self.llm_successes += 1
            self._latencies_ms.append(latency_ms)
        else:
            self.llm_errors += 1
            if error_type == "timeout":
                self.llm_timeouts += 1
            elif error_type == "circuit_breaker":
                self.circuit_breaker_trips += 1

    # ------------------------------------------------------------------
    # Derived stats
    # ------------------------------------------------------------------

    def avg_latency_ms(self) -> Optional[float]:
        if not self._latencies_ms:
            return None
        return sum(self._latencies_ms) / len(self._latencies_ms)

    def min_latency_ms(self) -> Optional[float]:
        return min(self._latencies_ms) if self._latencies_ms else None

    def max_latency_ms(self) -> Optional[float]:
        return max(self._latencies_ms) if self._latencies_ms else None

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_insert_dict(
        self,
        analysis_mode: str,
        total_runtime_ms: Optional[int],
    ) -> dict:
        """Return a dict ready for INSERT into model_metrics.

        Args:
            analysis_mode: 'llm', 'hybrid', or 'rules_only'.
            total_runtime_ms: End-to-end wall-clock time for the full request.
        """
        return {
            "analysis_mode": analysis_mode,
            "total_sentences": self.total_sentences,
            "llm_calls": self.llm_calls,
            "llm_successes": self.llm_successes,
            "llm_errors": self.llm_errors,
            "llm_timeouts": self.llm_timeouts,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "avg_latency_ms": self.avg_latency_ms(),
            "min_latency_ms": self.min_latency_ms(),
            "max_latency_ms": self.max_latency_ms(),
            "total_runtime_ms": total_runtime_ms,
        }


__all__ = ["CallMetrics"]
