"""
vLLM async batch processor for dataset synthesis.

Replaces Claude Batch API with local vLLM inference:
- Batch size: 64 requests (optimal throughput)
- Rate limiting: 30 req/sec (safety margin)
- Retry logic: 3 attempts with exponential backoff
- LoRA adapter support
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI

from ml.data_synthesis.utils.json_extractor import extract_json, validate_sample_schema


logger = logging.getLogger(__name__)


class VLLMProcessor:
    """Async processor for vLLM OpenAI-compatible API."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-3B-Instruct",
        lora_path: Optional[str] = None
    ):
        """
        Initialize vLLM processor.

        Args:
            endpoint: vLLM OpenAI-compatible API endpoint
            model: Model name (e.g., "Qwen/Qwen2.5-3B-Instruct")
            lora_path: Optional path to LoRA adapter weights
        """
        self.client = AsyncOpenAI(
            base_url=endpoint,
            api_key="EMPTY"  # vLLM doesn't require auth
        )
        self.model = model
        self.lora_path = lora_path

        logger.info(f"Initialized VLLMProcessor: endpoint={endpoint}, model={model}")
        if lora_path:
            logger.info(f"LoRA adapter: {lora_path}")

    async def generate_batch(
        self,
        requests: List[Dict],
        batch_size: int = 64,
        max_throughput: int = 30,
        max_tokens: int = 1500,
        temperature: float = 0.9
    ) -> List[Dict]:
        """
        Process requests in batches with rate limiting.

        Args:
            requests: List of request dicts with format:
                {
                    "custom_id": str,
                    "params": {
                        "messages": [{"role": "system", "content": ...}, ...],
                        "max_tokens": int,
                        "temperature": float
                    }
                }
            batch_size: Number of requests per batch (default: 64)
            max_throughput: Max requests per second (default: 30)
            max_tokens: Max tokens per response
            temperature: Sampling temperature

        Returns:
            List of result dicts with format:
                {
                    "custom_id": str,
                    "result": {
                        "type": "succeeded" | "error",
                        "data": {...} | None,
                        "error": str | None
                    }
                }
        """
        total_requests = len(requests)
        logger.info(f"Processing {total_requests} requests in batches of {batch_size}")

        # Split into chunks
        chunks = [
            requests[i:i + batch_size]
            for i in range(0, total_requests, batch_size)
        ]

        # Calculate delay between batches to respect rate limit
        # batch_size / max_throughput = seconds per batch
        batch_delay = batch_size / max_throughput
        logger.info(f"Rate limit: {max_throughput} req/sec → {batch_delay:.2f}s delay between batches")

        all_results = []
        start_time = time.time()

        for chunk_idx, chunk in enumerate(chunks):
            chunk_start = time.time()
            logger.info(f"Processing batch {chunk_idx + 1}/{len(chunks)} ({len(chunk)} requests)...")

            # Process chunk in parallel
            tasks = [
                self._generate_single(
                    request=req,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                for req in chunk
            ]

            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for i, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.error(f"Request {chunk[i]['custom_id']} failed: {result}")
                    all_results.append({
                        "custom_id": chunk[i]["custom_id"],
                        "result": {
                            "type": "error",
                            "error": str(result)
                        }
                    })
                else:
                    all_results.append(result)

            chunk_elapsed = time.time() - chunk_start
            logger.info(f"Batch {chunk_idx + 1} completed in {chunk_elapsed:.2f}s")

            # Rate limiting delay (skip for last batch)
            if chunk_idx < len(chunks) - 1:
                await asyncio.sleep(batch_delay)

        total_elapsed = time.time() - start_time
        actual_throughput = total_requests / total_elapsed
        logger.info(f"Total: {total_requests} requests in {total_elapsed:.2f}s ({actual_throughput:.2f} req/sec)")

        # Log success/error breakdown
        successes = sum(1 for r in all_results if r["result"]["type"] == "succeeded")
        errors = sum(1 for r in all_results if r["result"]["type"] == "error")
        logger.info(f"Results: {successes} succeeded, {errors} errors ({100 * successes / total_requests:.1f}% success rate)")

        return all_results

    async def _generate_single(
        self,
        request: Dict,
        max_tokens: int,
        temperature: float,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate single sample with retry logic.

        Args:
            request: Request dict with custom_id and params
            max_tokens: Max tokens per response
            temperature: Sampling temperature
            max_retries: Maximum retry attempts

        Returns:
            Result dict with custom_id and result (succeeded or error)
        """
        custom_id = request["custom_id"]
        messages = request["params"]["messages"]

        # Override with provided params if present
        max_tokens = request["params"].get("max_tokens", max_tokens)
        temperature = request["params"].get("temperature", temperature)

        for attempt in range(max_retries):
            try:
                # Build API call params
                api_params = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }

                # Inject LoRA adapter if configured
                if self.lora_path:
                    api_params["extra_body"] = {"lora_path": self.lora_path}

                # Call vLLM API
                response = await self.client.chat.completions.create(**api_params)

                # Extract response text
                content = response.choices[0].message.content

                # Parse JSON
                data = extract_json(content)

                # Validate schema
                if not validate_sample_schema(data):
                    raise ValueError(f"Schema validation failed: {data}")

                return {
                    "custom_id": custom_id,
                    "result": {
                        "type": "succeeded",
                        "data": data
                    }
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    logger.warning(f"Request {custom_id} failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(f"Request {custom_id} failed after {max_retries} attempts: {e}")
                    return {
                        "custom_id": custom_id,
                        "result": {
                            "type": "error",
                            "error": str(e)
                        }
                    }

        # Should never reach here, but satisfy type checker
        return {
            "custom_id": custom_id,
            "result": {
                "type": "error",
                "error": "Unknown error"
            }
        }


async def health_check(endpoint: str = "http://localhost:8000/health") -> bool:
    """
    Check if vLLM server is healthy.

    Args:
        endpoint: Health check endpoint

    Returns:
        True if healthy, False otherwise
    """
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, timeout=5) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
