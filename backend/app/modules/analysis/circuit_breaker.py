"""
Circuit breaker for vLLM API calls.

Uses pybreaker to protect against cascade failures when vLLM is unavailable.
Circuit opens after fail_max consecutive failures, auto-recovers after reset_timeout.
"""

from pybreaker import CircuitBreaker, CircuitBreakerError

from app.core.config import settings


# Create a circuit breaker for vLLM API calls
# - Opens after fail_max (default 3) consecutive failures
# - Auto-recovers after reset_timeout (default 60) seconds
vllm_breaker = CircuitBreaker(
    fail_max=settings.VLLM_CIRCUIT_FAIL_MAX,
    reset_timeout=settings.VLLM_CIRCUIT_RESET_TIMEOUT,
)


# Re-export CircuitBreakerError for convenience
__all__ = ["vllm_breaker", "CircuitBreakerError"]
