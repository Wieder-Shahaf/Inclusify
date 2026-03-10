"""
vLLM HTTP client for LGBTQ+ inclusive language analysis.

Provides async client with circuit breaker protection for calling vLLM inference endpoint.
"""

import json
import re
from typing import Optional

import httpx
from pybreaker import CircuitBreakerError

from app.core.config import settings
from app.modules.analysis.circuit_breaker import vllm_breaker


# System prompt for the model (from ml/inference_demo.py)
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
    "Potentially Offensive": "offensive",
    "Factually Incorrect": "incorrect",
}


def parse_llm_output(raw: str) -> Optional[dict]:
    """
    Parse LLM output, extracting JSON from markdown code blocks if present.

    Args:
        raw: Raw LLM output string

    Returns:
        Parsed dict or None if parsing fails
    """
    # Extract JSON from markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = raw.strip()

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
    """

    def __init__(self, base_url: str = None, timeout: float = None):
        """
        Initialize vLLM client.

        Args:
            base_url: vLLM server URL (default: from settings)
            timeout: Request timeout in seconds (default: from settings)
        """
        self.base_url = base_url or settings.VLLM_URL
        self.timeout = timeout or settings.VLLM_TIMEOUT

    async def analyze_sentence(self, sentence: str) -> Optional[dict]:
        """
        Analyze a sentence for LGBTQ+ inclusive language compliance.

        Args:
            sentence: Text to analyze

        Returns:
            Parsed response dict with category, severity, explanation.
            Returns None on any error (timeout, HTTP error, circuit open, parse error).
        """
        try:
            return await self._make_request(sentence)
        except (httpx.TimeoutException, httpx.HTTPStatusError, CircuitBreakerError):
            return None
        except Exception:
            return None

    @vllm_breaker
    async def _make_request(self, sentence: str) -> Optional[dict]:
        """
        Make HTTP request to vLLM (protected by circuit breaker).

        Decorated with circuit breaker - will raise CircuitBreakerError if circuit is open.
        """
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
                    "temperature": 0.1
                }
            )
            response.raise_for_status()

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            return parse_llm_output(raw_content)


__all__ = ["VLLMClient", "parse_llm_output", "map_severity", "SYSTEM_PROMPT"]
