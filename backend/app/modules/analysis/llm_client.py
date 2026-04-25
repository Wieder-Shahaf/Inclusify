"""
vLLM HTTP client for LGBTQ+ inclusive language analysis.

Provides async client with circuit breaker protection for calling vLLM inference endpoint.
"""

import asyncio
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
from app.modules.analysis.call_metrics import CallMetrics

logger = logging.getLogger(__name__)


# System prompt for the model
SYSTEM_PROMPT = """You are an expert academic editor for the Inclusify project, specializing in LGBTQ+ inclusive language analysis in academic texts.

You will receive a passage of academic text. Identify ALL phrases in the passage that contain problematic LGBTQ+ language.

STRICT OUTPUT FORMAT — respond with ONLY a valid JSON object, no other text, no markdown:
{
  "issues": [
    {
      "phrase": "<exact substring copied character-for-character from the passage>",
      "category": "<exactly one of: 'Medicalization' | 'Generalization' | 'Demeaning Terminology'>",
      "severity": "<exactly one of: 'Outdated' | 'Biased' | 'Potentially Offensive' | 'Factually Incorrect'>",
      "explanation": "<why this phrase is problematic in an academic context>",
      "suggestion": "<an inclusive replacement for this specific phrase only>"
    }
  ]
}

SEVERITY DEFINITIONS (sources: APA Publication Manual 7th ed., GLAAD Media Reference Guide 11th ed., PFLAG Glossary, WHO ICD-11 2022, APA SOCE Resolution 2021):

Outdated — Language formerly accepted in academic or clinical use but formally superseded by scientific consensus, APA style standards, or community self-determination due to pathologizing or inaccurate connotations. Apply even when used without malicious intent.
  Common markers: "homosexual/homosexuals" (→ gay, lesbian, bisexual, queer people); "transsexual" (→ transgender); "sexual preference" (→ sexual orientation, which is not a choice); "gender identity disorder" (→ gender dysphoria).

Biased — Language encoding stereotypes, false hierarchies, or prejudicial assumptions — including treating heterosexuality or cisgender identity as the unmarked norm against which LGBTQ+ people are measured or found lacking, or collapsing diverse identities into homogeneous stereotyped groups. (APA: "do not imply that one group is superior… avoid designating the standard group by omitting it from a comparison.")
  Common markers: "normal women/men" compared to LGBTQ+ subjects; listing an identity category alongside disorder categories as a "special population"; attributing personality or behavioral traits (emotional expressiveness, instability) to sexual orientation as a causal mechanism.

Potentially Offensive — Language experienced as hurtful or invalidating by LGBTQ+ people even without malicious intent, because it implies the identity is shameful, deceptive, or merely claimed rather than real. (GLAAD 11th ed.; PFLAG Glossary; HRC Glossary of Terms.)
  Common markers: "passing as their gender" (implies deception — GLAAD flags this outside self-referential use); "disclosed their sexual orientation" (implies shame requiring deliberate revelation — PFLAG); "identifies as non-binary/transgender" (→ "is non-binary/transgender"; GLAAD: "identifies as" implies the identity is merely asserted, not real).

Factually Incorrect — Statements that contradict current scientific and medical consensus established by WHO ICD-11 (2022), DSM-5, and APA — including claims that LGBTQ+ identities are disorders, have pathological etiologies, or are changeable through intervention.
  Common markers: framing same-sex orientation as a "deviation from normal development"; calling gender incongruence a psychiatric disorder (ICD-11 explicitly relocated it outside mental disorders in 2022); asserting that sexual or gender identity change efforts are effective (APA Resolution 2021: no evidence of efficacy, documented harm).

CATEGORY DEFINITIONS (sources: WHO ICD-11 2022; PMC depathologization review PMC11272317; APA SOCE/GICE Resolutions 2021; GLAAD 11th ed.; APA Publication Manual 7th ed.; GLSEN educator guidance):

Medicalization — Framing LGBTQ+ sexual orientations, gender identities, or gender expressions as diseases, disorders, pathologies, syndromes, or conditions requiring clinical diagnosis and treatment. Explicitly rejected by WHO ICD-11 (2022), DSM-5, and APA.
  Common markers: diagnostic vocabulary applied to identity (disorder, syndrome, pathology, deviance, dysfunction, etiology, cure, treatment); conversion/reparative therapy rationale; framing identity as having a clinical cause requiring a clinical remedy (e.g., "ego-dystonic homosexuality treatment arm"; "gender identity disorder etiology in adolescents").

Generalization — Broad, unfounded, essentialist claims about LGBTQ+ people as a uniform group, attributing shared traits, behaviors, or outcomes to all members without empirical support and without acknowledging diversity across culture, race, socioeconomic status, and individual variation. (APA: "avoid collapsing diverse communities into single terms; specify identities and genders." GLSEN: "avoid representations that fail to acknowledge ethnic, racial, and other forms of diversity.")
  Common markers: universal quantifiers without citation (all, most, typically, tend to, are known to); group-level trait attribution (e.g., "gay men are more emotional"); conflating distinct subgroups (treating "LGBT" as homogeneous); absent acknowledgment of within-group variance. NOTE: empirically supported epidemiological findings with proper qualification are NOT generalizations.

Demeaning Terminology — Words or phrases that reduce, insult, dehumanize, or stigmatize LGBTQ+ people — including clinical-era terms now used as slurs, reductive nouns stripping personhood, and vocabulary of deviance or moral failure applied to identity. (GLAAD 11th ed.: "Words such as 'deviant,' 'diseased,' and 'disordered' often portray LGBTQ people as less than human." APA: "do not use adjectives as nouns — 'the gays' — which dehumanizes.")
  Common markers: slurs or epithets (trannies, perverts) in any framing; reductive nouns replacing person-first language ("homosexuals", "the gays", "transgenders"); vocabulary of deviance, perversion, or moral failure applied to orientation or identity ("deviant attachment patterns"; "perverted sexual behavior including same-sex acts").

RULES:
- SCOPE: Flag ONLY phrases that are themselves LGBTQ+-specific problematic language — terms, labels, or descriptors applied to LGBTQ+ people, their identities, or their relationships. Do NOT flag general academic vocabulary, research methodology terms, statistical language, authorship notes, or common English words that appear in an LGBTQ+ paper but are not themselves problematic LGBTQ+ terminology.
- A phrase qualifies ONLY if the phrase itself (not just its surrounding context) contains or constitutes LGBTQ+ stigmatizing, outdated, or demeaning language.
- DO NOT FLAG words like: "relationships", "behavior", "participants", "study", "data", "manuscript", "author", "results", "findings", "research", "analysis", "population", "group", "sample", or any neutral academic term.
- If the passage contains no LGBTQ+-specific problematic language, return: {"issues": []}
- "phrase" MUST be an exact copy of text from the input passage — never paraphrase or modify it
- If multiple distinct phrases are problematic, include one entry per phrase
- When in doubt, do NOT flag — only flag phrases with clear, well-established LGBTQ+ language problems

EXAMPLE:
Passage: "Research on homosexuals showed that gender identity disorder was widespread, confirming earlier claims that the homosexual lifestyle leads to psychological instability."

Output:
{"issues":[{"phrase":"homosexuals","category":"Demeaning Terminology","severity":"Outdated","explanation":"'Homosexuals' is a dehumanizing clinical noun; APA and GLAAD recommend person-first language. Use 'gay and lesbian people' instead.","suggestion":"gay and lesbian people"},{"phrase":"gender identity disorder","category":"Medicalization","severity":"Outdated","explanation":"Removed from DSM-5 (2013) and relocated out of mental disorders in ICD-11 (2022); the term falsely frames transgender identity as a pathology.","suggestion":"gender dysphoria"},{"phrase":"homosexual lifestyle","category":"Demeaning Terminology","severity":"Biased","explanation":"'Lifestyle' frames sexual orientation as a deliberate behavioral choice, directly contradicting scientific consensus. GLAAD explicitly flags this phrase.","suggestion":"sexual orientation"}]}"""


# Severity mapping from LLM output to API severity levels
SEVERITY_MAP = {
    "Outdated": "outdated",
    "Biased": "biased",
    "Potentially Offensive": "potentially_offensive",
    "Factually Incorrect": "factually_incorrect",
}


def _build_token_index(logprobs_content: list) -> tuple[str, list[int], list[float]]:
    """Reconstruct the generated text and build parallel char-position and logprob arrays."""
    tokens = [item["token"] for item in logprobs_content]
    lps = [item["logprob"] for item in logprobs_content]
    char_positions: list[int] = []
    reconstructed = ""
    for token in tokens:
        char_positions.append(len(reconstructed))
        reconstructed += token
    return reconstructed, char_positions, tokens, lps


def _logprob_for_span(
    reconstructed: str,
    char_positions: list[int],
    tokens: list[str],
    lps: list[float],
    value_start: int,
    value_end: int,
) -> Optional[float]:
    """Average logprob for tokens overlapping [value_start, value_end], converted to probability."""
    span_lps: list[float] = []
    for i, pos in enumerate(char_positions):
        token_end = pos + len(tokens[i])
        if pos < value_end and token_end > value_start:
            span_lps.append(lps[i])
    if not span_lps:
        return None
    mean_lp = sum(span_lps) / len(span_lps)
    return max(0.0, min(1.0, math.exp(mean_lp)))


def extract_severity_confidence(logprobs_content: list, severity_value: str) -> Optional[float]:
    """
    Compute confidence from vLLM logprobs for a single-object response.

    Finds the first occurrence of the severity value token in the generated output,
    averages its log-probabilities, and converts via exp(mean_logprob).
    Used for the legacy single-object response format.
    """
    if not logprobs_content or not severity_value:
        return None

    reconstructed, char_positions, tokens, lps = _build_token_index(logprobs_content)

    value_start: int = -1
    for marker in (f'"severity": "{severity_value}"', f'"severity":"{severity_value}"'):
        idx = reconstructed.find(marker)
        if idx != -1:
            value_start = reconstructed.find(severity_value, idx)
            break

    if value_start == -1:
        return None

    return _logprob_for_span(
        reconstructed, char_positions, tokens, lps,
        value_start, value_start + len(severity_value),
    )


def extract_all_severity_confidences(
    logprobs_content: list,
    issues: list[dict],
) -> list[Optional[float]]:
    """
    Per-issue confidence = exp(logprob of the FIRST token of THIS issue's severity value).

    Severity labels are multi-token (e.g. "Factually Incorrect" → ['Fact','ually',' Incorrect']).
    Only the first token is a real choice — once the model picks 'Fact', the rest is forced
    at p≈1.0. Averaging all tokens inflates the score. The first token's logprob is the
    probability the model assigned to this label over all alternatives at the decision point.

    For the Nth issue we locate the Nth occurrence of `"severity": "<value>"` in the
    generated text and take the logprob of the first overlapping token.
    Returns None when the severity marker cannot be found, with a debug log explaining why.
    """
    if not logprobs_content:
        logger.warning("confidence=None: logprobs_content is empty")
        return [None] * len(issues)
    if not issues:
        return []

    reconstructed, char_positions, tokens, lps = _build_token_index(logprobs_content)

    def nth_severity_span(value: str, n: int) -> Optional[tuple[int, int]]:
        cursor = 0
        for _ in range(n):
            span = None
            for marker in (f'"severity": "{value}"', f'"severity":"{value}"'):
                idx = reconstructed.find(marker, cursor)
                if idx != -1:
                    vs = reconstructed.find(value, idx)
                    if vs != -1:
                        span = (vs, vs + len(value))
                        break
            if span is None:
                return None
            cursor = span[1]
        return span

    severity_occurrence: dict[str, int] = {}
    confidences: list[Optional[float]] = []

    for issue_idx, issue in enumerate(issues):
        severity = issue.get("severity")
        if not isinstance(severity, str) or not severity:
            logger.warning(
                "confidence=None issue=%d: missing or non-string severity field (got %r)",
                issue_idx, severity,
            )
            confidences.append(None)
            continue

        severity_occurrence[severity] = severity_occurrence.get(severity, 0) + 1
        n = severity_occurrence[severity]
        span = nth_severity_span(severity, n)

        if span is None:
            logger.warning(
                "confidence=None issue=%d: could not locate occurrence %d of "
                '"severity": "%s" in generated text (len=%d). '
                "First 200 chars of output: %r",
                issue_idx, n, severity, len(reconstructed), reconstructed[:200],
            )
            confidences.append(None)
            continue

        vs, ve = span
        # First token overlapping the severity value span — the actual label-selection token.
        # Confidence = p(chosen) / (p(chosen) + p(runner-up)) so we measure how dominant
        # this label was over the best alternative, not just its raw probability.
        chosen_lp: Optional[float] = None
        runner_up_lp: Optional[float] = None
        for i, pos in enumerate(char_positions):
            tok_end = pos + len(tokens[i])
            if pos < ve and tok_end > vs:
                chosen_lp = lps[i]
                top = logprobs_content[i].get("top_logprobs") or []
                if len(top) >= 2:
                    runner_up_lp = top[1]["logprob"]
                logger.debug(
                    "confidence issue=%d severity=%r occurrence=%d: "
                    "first_token=%r chosen_lp=%.4f runner_up_lp=%s",
                    issue_idx, severity, n, tokens[i], lps[i],
                    f"{runner_up_lp:.4f}" if runner_up_lp is not None else "n/a",
                )
                break

        if chosen_lp is None:
            logger.warning(
                "confidence=None issue=%d severity=%r: span found (%d,%d) "
                "but no token overlaps it",
                issue_idx, severity, vs, ve,
            )
            confidences.append(None)
        elif runner_up_lp is not None:
            p_chosen = math.exp(chosen_lp)
            p_runner = math.exp(runner_up_lp)
            confidences.append(p_chosen / (p_chosen + p_runner))
        else:
            # top_logprobs unavailable — fall back to raw first-token probability
            logger.debug(
                "confidence issue=%d severity=%r: no runner-up available, using raw prob",
                issue_idx, severity,
            )
            confidences.append(max(0.0, min(1.0, math.exp(chosen_lp))))

    return confidences


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
    _semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(settings.VLLM_MAX_CONCURRENT)
        return cls._semaphore

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or settings.VLLM_URL
        self.timeout = timeout or settings.VLLM_TIMEOUT

    def _get_mock_response(self) -> dict:
        """Provide a simulated JSON response when vLLM is unreachable for load testing."""
        return {
            "issues": [
                {
                    "phrase": "[MOCK] problematic phrase",
                    "category": "Demeaning Terminology",
                    "severity": "Outdated",
                    "explanation": "[MOCK] Simulated response — vLLM server unreachable.",
                    "suggestion": "[MOCK] Please use inclusive and affirming language.",
                }
            ]
        }

    async def analyze_sentence(
        self,
        sentence: str,
        metrics: Optional[CallMetrics] = None,
    ) -> Optional[dict]:
        """
        Analyze a sentence for LGBTQ+ inclusive language compliance.

        Acquires the global semaphore before sending to GPU — excess requests
        queue here instead of hammering vLLM concurrently.

        Args:
            sentence: The sentence text to analyze.
            metrics: Optional CallMetrics accumulator. When provided, each call
                     outcome (latency, success/error type) is recorded on it.

        Returns:
            Parsed response dict with category, severity, explanation.
            Returns None on any error (timeout, HTTP error, circuit open, parse error).
        """
        async with self._get_semaphore():
            t0 = time.monotonic()
            try:
                result = await self._make_request(sentence)
                latency_ms = (time.monotonic() - t0) * 1000
                if metrics is not None:
                    metrics.record_call(latency_ms, success=result is not None)
                return result
            except CircuitBreakerError:
                if metrics is not None:
                    metrics.record_call(0.0, success=False, error_type="circuit_breaker")
                logger.warning("vLLM circuit breaker is open — skipping LLM call")
                return self._get_mock_response() if settings.VLLM_LOAD_TEST_MODE else None
            except httpx.TimeoutException:
                latency_ms = (time.monotonic() - t0) * 1000
                if metrics is not None:
                    metrics.record_call(latency_ms, success=False, error_type="timeout")
                logger.error("vLLM request timed out: url=%s timeout_s=%.1f", self.base_url, self.timeout)
                return self._get_mock_response() if settings.VLLM_LOAD_TEST_MODE else None
            except httpx.HTTPStatusError as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                if metrics is not None:
                    metrics.record_call(latency_ms, success=False, error_type="http_error")
                try:
                    body = exc.response.text[:500]
                except Exception:
                    body = "<unreadable>"
                logger.error("vLLM HTTP error: status=%d url=%s body=%s", exc.response.status_code, self.base_url, body)
                return self._get_mock_response() if settings.VLLM_LOAD_TEST_MODE else None
            except Exception as exc:
                if metrics is not None:
                    metrics.record_call(0.0, success=False)
                logger.error("vLLM unexpected error: %s", str(exc), exc_info=True)
                return self._get_mock_response() if settings.VLLM_LOAD_TEST_MODE else None

    async def get_suggestion(
        self,
        sentence: str,
        severity: str,
        category: str,
        metrics: Optional[CallMetrics] = None,
    ) -> Optional[str]:
        """
        Focused retry: ask the model only for an inclusive rephrasing of a sentence
        that was already classified as problematic. Returns the suggestion string or None.
        """
        async with self._get_semaphore():
            t0 = time.monotonic()
            try:
                prompt = (
                    f'The following sentence was classified as [{severity}] ({category}):\n'
                    f'"{sentence}"\n\n'
                    f'Provide ONLY an inclusive, corrected rephrasing of this sentence. '
                    f'No explanation. No JSON. Just the rephrased sentence.'
                )
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json={
                            "model": settings.VLLM_MODEL_NAME,
                            "messages": [
                                {"role": "system", "content": "You are an expert academic editor specializing in LGBTQ+ inclusive language."},
                                {"role": "user", "content": prompt},
                            ],
                            "max_tokens": 200,
                            "temperature": 0.2,
                        },
                    )
                    response.raise_for_status()
                latency_ms = (time.monotonic() - t0) * 1000
                if metrics is not None:
                    metrics.record_call(latency_ms, success=True)
                data = response.json()
                suggestion = data["choices"][0]["message"]["content"].strip()
                return suggestion if suggestion else None
            except Exception as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                if metrics is not None:
                    metrics.record_call(latency_ms, success=False)
                logger.warning("Suggestion retry failed: %s", exc)
                return None

    @vllm_breaker
    async def _make_request(self, sentence: str) -> Optional[dict]:
        """
        Make HTTP request to vLLM (protected by circuit breaker).

        Decorated with circuit breaker - will raise CircuitBreakerError if circuit is open.
        """
        logger.debug("vLLM request started: url=%s sentence_chars=%d", self.base_url, len(sentence))
        t0 = time.monotonic()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": settings.VLLM_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f'Analyze this passage for LGBTQ+ inclusive language compliance:\n"{sentence}"'}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "logprobs": True,
                    "top_logprobs": 5,
                }
            )
            response.raise_for_status()

        elapsed = time.monotonic() - t0
        logger.debug("vLLM response received: status=%d elapsed_s=%.3f", response.status_code, elapsed)

        data = response.json()
        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            logger.warning("vLLM malformed response: missing or empty 'choices' field")
            return None
        choice = choices[0]
        if not isinstance(choice, dict):
            logger.warning("vLLM malformed response: choice is not a dict")
            return None
        message = choice.get("message")
        if not isinstance(message, dict):
            logger.warning("vLLM malformed response: missing or invalid 'message' in choice")
            return None
        raw_content = message.get("content")
        if raw_content is None:
            logger.warning("vLLM malformed response: missing 'content' in message")
            return None

        parsed = parse_llm_output(raw_content)
        if parsed is None:
            return None

        logprobs_data = choice.get("logprobs") or {}
        logprobs_content = logprobs_data.get("content") or []

        issues = parsed.get("issues")
        if isinstance(issues, list):
            # Array format: attach per-issue confidence from Nth severity token
            confidences = extract_all_severity_confidences(logprobs_content, issues)
            for issue_data, conf in zip(issues, confidences):
                issue_data["confidence"] = conf
        else:
            # Legacy single-object format
            severity_value = parsed.get("severity", "")
            parsed["confidence"] = extract_severity_confidence(logprobs_content, severity_value)

        return parsed


def extract_chunk_issues(parsed: Optional[dict]) -> list[dict]:
    """
    Extract the list of per-phrase issues from a parsed LLM response.

    Handles the current array format {"issues": [...]} as well as the legacy
    single-object format {"phrase": ..., "severity": ...} that the LoRA
    fine-tuned model may still produce on some inputs.
    """
    if not parsed:
        return []

    issues = parsed.get("issues")
    if isinstance(issues, list):
        return [i for i in issues if isinstance(i, dict)]

    # Legacy single-object fallback: wrap if the model returned one classification
    severity = parsed.get("severity", "")
    if severity and severity != "Correct":
        return [parsed]

    return []


__all__ = ["VLLMClient", "parse_llm_output", "map_severity", "extract_severity_confidence", "extract_chunk_issues", "SYSTEM_PROMPT", "CallMetrics"]
