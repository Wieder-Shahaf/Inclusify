"""
vLLM HTTP client for LGBTQ+ inclusive language analysis.

Provides async client with circuit breaker protection for calling vLLM inference endpoint.
"""

import json
import logging
import math
import re
import time
from typing import Optional

import httpx
from pybreaker import CircuitBreakerError

from app.core.config import settings
from app.modules.analysis.circuit_breaker import vllm_breaker

logger = logging.getLogger(__name__)


# System prompt for the model
SYSTEM_PROMPT = """You are an expert academic editor for the Inclusify project. Analyze sentences for LGBTQ+ inclusive language compliance.

OUTPUT REQUIREMENTS:
You MUST respond with ONLY a valid JSON object. No other text, no markdown, no explanation outside the JSON.

STRICT JSON SCHEMA:
{
  "category": "<rule category: e.g., 'N/A', 'Historical Pathologization', 'Identity Invalidation', 'Tone Policing', 'Medical Misinformation', 'False Causality', etc.>",
  "severity": "<EXACTLY one of: 'Correct', 'Outdated', 'Biased', 'Potentially Offensive', 'Factually Incorrect'>",
  "explanation": "<detailed reasoning for the classification>"
}

RULES:
- If the sentence is inclusive and appropriate, classify as "Correct" with category "N/A"
- Only classify as harmful if there is clear evidence of problematic language
- Provide specific, academic explanations"""


# Severity mapping from LLM output to API severity levels
SEVERITY_MAP = {
    "Outdated": "outdated",
    "Biased": "biased",
    "Potentially Offensive": "potentially_offensive",
    "Factually Incorrect": "factually_incorrect",
}


def extract_severity_confidence(logprobs_content: list, severity_value: str) -> Optional[float]:
    """
    Compute confidence from vLLM logprobs by locating the severity value tokens.

    Finds which tokens in the generated output correspond to the severity value
    (e.g. "Biased"), averages their log-probabilities, and converts to a
    probability via exp(mean_logprob).

    Args:
        logprobs_content: List of {token, logprob} dicts from vLLM response.
        severity_value: The severity string the model produced (e.g. "Biased").

    Returns:
        float in [0.0, 1.0] or None if logprobs unavailable / token not found.
    """
    if not logprobs_content or not severity_value:
        return None

    # Reconstruct generated text and per-token character positions
    tokens = [item["token"] for item in logprobs_content]
    lps = [item["logprob"] for item in logprobs_content]

    char_positions: list[int] = []
    reconstructed = ""
    for token in tokens:
        char_positions.append(len(reconstructed))
        reconstructed += token

    # Locate the severity value inside the JSON output.
    # Try with and without space after the colon.
    value_start: int = -1
    for marker in (f'"severity": "{severity_value}"', f'"severity":"{severity_value}"'):
        idx = reconstructed.find(marker)
        if idx != -1:
            # The value starts after: "severity": "
            value_start = reconstructed.find(severity_value, idx)
            break

    if value_start == -1:
        return None

    value_end = value_start + len(severity_value)

    # Collect logprobs for tokens that overlap with the severity value span
    severity_lps: list[float] = []
    for i, pos in enumerate(char_positions):
        token_end = pos + len(tokens[i])
        if pos < value_end and token_end > value_start:
            severity_lps.append(lps[i])

    if not severity_lps:
        return None

    mean_lp = sum(severity_lps) / len(severity_lps)
    # Clamp to [0.0, 1.0] — exp(0) = 1.0 is the maximum possible logprob
    return max(0.0, min(1.0, math.exp(mean_lp)))


def parse_llm_output(llm_response_text: str) -> Optional[dict]:
    """
    Parse LLM output, extracting JSON from markdown code blocks if present.

    Args:
        llm_response_text: Raw LLM output string

    Returns:
        Parsed dict or None if parsing fails
    """
    # Extract JSON from markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', llm_response_text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = llm_response_text.strip()

    # Find JSON object boundaries
    start_idx = json_str.find('{')
    end_idx = json_str.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = json_str[start_idx:end_idx + 1]
    else:
        return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def map_severity(llm_severity: str) -> Optional[str]:
    """
    Map LLM severity to API severity level.

    Args:
        llm_severity: Severity string from LLM ("Correct", "Outdated", etc.)

    Returns:
        Mapped severity ("outdated", "biased", etc.) or None for "Correct" (skip)
    """
    if llm_severity == "Correct":
        return None
    return SEVERITY_MAP.get(llm_severity)


class VLLMClient:
    """
    Async HTTP client for vLLM inference.

    Uses circuit breaker to protect against cascade failures.
    Returns None on any error (timeout, HTTP error, circuit open).

    A class-level semaphore caps concurrent GPU calls across ALL users.
    Raise VLLM_MAX_CONCURRENT in config when adding GPU capacity.
    """

    # Shared across all instances — limits total concurrent GPU calls globally.
    _semaphore: asyncio.Semaphore | None = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(settings.VLLM_MAX_CONCURRENT)
        return cls._semaphore

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or settings.VLLM_URL
        self.timeout = timeout or settings.VLLM_TIMEOUT

    async def analyze_sentence(self, sentence: str) -> Optional[dict]:
        """
        Analyze a sentence for LGBTQ+ inclusive language compliance.

        Acquires the global semaphore before sending to GPU — excess requests
        queue here instead of hammering vLLM concurrently.

        Returns:
            Parsed response dict with category, severity, explanation.
            Returns None on any error (timeout, HTTP error, circuit open, parse error).
        """
        async with self._get_semaphore():
            try:
                return await self._make_request(sentence)
            except CircuitBreakerError:
                logger.warning("vLLM circuit breaker is open — skipping LLM call")
                return None
            except httpx.TimeoutException:
                logger.error("vLLM request timed out: url=%s timeout_s=%.1f", self.base_url, self.timeout)
                return None
            except httpx.HTTPStatusError as exc:
                logger.error("vLLM HTTP error: status=%d url=%s", exc.response.status_code, self.base_url)
                return None
            except Exception as exc:
                logger.error("vLLM unexpected error: %s", str(exc), exc_info=True)
                return None

    @vllm_breaker
    async def _make_request(self, sentence: str) -> Optional[dict]:
        """
        Make HTTP request to vLLM (protected by circuit breaker).

        Decorated with circuit breaker - will raise CircuitBreakerError if circuit is open.
        """
        logger.info("vLLM request started: url=%s sentence_chars=%d", self.base_url, len(sentence))
        t0 = time.monotonic()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": settings.VLLM_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f'Analyze this sentence for LGBTQ+ inclusive language compliance:\n"{sentence}"'}
                    ],
                    "max_tokens": 256,
                    "temperature": 0.1,
                    "logprobs": True,
                }
            )
            response.raise_for_status()

        elapsed = time.monotonic() - t0
        logger.info("vLLM response received: status=%d elapsed_s=%.3f", response.status_code, elapsed)

        data = response.json()
        choice = data["choices"][0]
        raw_content = choice["message"]["content"]

        parsed = parse_llm_output(raw_content)
        if parsed is None:
            return None

        # Compute confidence from logprobs (overrides any self-reported value)
        logprobs_data = choice.get("logprobs") or {}
        logprobs_content = logprobs_data.get("content") or []
        severity_value = parsed.get("severity", "")
        parsed["confidence"] = extract_severity_confidence(logprobs_content, severity_value)

        return parsed


__all__ = ["VLLMClient", "parse_llm_output", "map_severity", "extract_severity_confidence", "SYSTEM_PROMPT"]
