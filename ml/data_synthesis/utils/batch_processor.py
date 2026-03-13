"""Claude Batch API processor with retry logic.

This module provides a wrapper around Claude's Message Batches API:
- Submit batch requests (up to 10,000 requests per batch)
- Poll for completion (batches process within 24 hours)
- Parse results and handle errors
- Retry transient failures

See: https://docs.anthropic.com/en/docs/message-batches
"""

import time
import logging
from typing import List, Dict, Any, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


def validate_requests(requests: List[Dict[str, Any]]) -> None:
    """Validate batch request format before submission.

    Args:
        requests: List of batch request dictionaries

    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = ["custom_id", "params"]
    required_param_fields = ["model", "max_tokens", "messages"]

    for i, req in enumerate(requests):
        # Check top-level fields
        for field in required_fields:
            if field not in req:
                raise ValueError(f"Missing required field '{field}' in request {i}")

        # Check params fields
        params = req.get("params", {})
        for field in required_param_fields:
            if field not in params:
                raise ValueError(f"Missing required field 'params.{field}' in request {i}")

        # Validate messages format
        messages = params.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError(f"'params.messages' must be a non-empty list in request {i}")


def parse_batch_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse batch results from Claude API response.

    Args:
        raw_results: Raw results from client.messages.batches.results()

    Returns:
        List of parsed result dictionaries with custom_id and result
    """
    parsed = []
    for item in raw_results:
        parsed.append({
            "custom_id": item.get("custom_id"),
            "result": item.get("result", {})
        })
    return parsed


class BatchProcessor:
    """Wrapper for Claude Message Batches API with retry logic."""

    def __init__(self, api_key: str, model: str):
        """Initialize BatchProcessor with API credentials.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., "claude-opus-4-20250514")
        """
        self.api_key = api_key
        self.model = model
        self.client = Anthropic(api_key=api_key)

    def submit_batch(
        self,
        requests: List[Dict[str, Any]],
        custom_id_prefix: str = "req",
        max_retries: int = 3
    ) -> str:
        """Submit batch requests to Claude API with retry logic.

        Args:
            requests: List of batch request dictionaries
            custom_id_prefix: Prefix for custom IDs (for tracking)
            max_retries: Maximum number of retry attempts

        Returns:
            Batch ID string

        Raises:
            ValueError: If request format is invalid
            Exception: If all retries fail
        """
        # Validate before submission
        validate_requests(requests)

        # Retry loop
        last_exception = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Submitting batch with {len(requests)} requests (attempt {attempt + 1}/{max_retries})")

                # Create batch via Claude API
                batch = self.client.messages.batches.create(requests=requests)

                logger.info(f"Batch created successfully: {batch.id}")
                return batch.id

            except Exception as e:
                last_exception = e
                logger.warning(f"Batch submission failed (attempt {attempt + 1}/{max_retries}): {e}")

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    time.sleep(wait_time)

        # All retries failed
        raise Exception(f"Batch submission failed after {max_retries} attempts: {last_exception}")

    def poll_results(
        self,
        batch_id: str,
        poll_interval: int = 60,
        timeout: int = 86400  # 24 hours default
    ) -> List[Dict[str, Any]]:
        """Poll batch status until completion and retrieve results.

        Args:
            batch_id: Batch ID returned from submit_batch()
            poll_interval: Seconds between status checks (default 60)
            timeout: Maximum wait time in seconds (default 24 hours)

        Returns:
            List of parsed result dictionaries

        Raises:
            TimeoutError: If batch doesn't complete within timeout
            Exception: If batch is cancelled or fails
        """
        start_time = time.time()
        logger.info(f"Polling batch {batch_id} for completion (interval: {poll_interval}s)")

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Batch {batch_id} did not complete within {timeout}s")

            # Retrieve batch status
            batch = self.client.messages.batches.retrieve(batch_id)
            status = batch.processing_status

            logger.debug(f"Batch {batch_id} status: {status}")

            if status == "ended":
                # Batch completed - retrieve results
                logger.info(f"Batch {batch_id} completed. Retrieving results...")
                results = self.client.messages.batches.results(batch_id)

                # Convert iterator to list and parse
                results_list = list(results)
                parsed = parse_batch_results(results_list)

                logger.info(f"Retrieved {len(parsed)} results from batch {batch_id}")
                return parsed

            elif status == "cancelled":
                raise Exception(f"Batch {batch_id} was cancelled")

            elif status == "in_progress" or status == "processing":
                # Still processing - wait and poll again
                time.sleep(poll_interval)

            else:
                # Unknown status
                logger.warning(f"Unknown batch status: {status}")
                time.sleep(poll_interval)


# Module-level convenience functions

def submit_batch(
    requests: List[Dict[str, Any]],
    api_key: str,
    model: str,
    custom_id_prefix: str = "req",
    max_retries: int = 3
) -> str:
    """Convenience function to submit a batch without creating BatchProcessor instance.

    Args:
        requests: List of batch request dictionaries
        api_key: Anthropic API key
        model: Model name
        custom_id_prefix: Prefix for custom IDs
        max_retries: Maximum retry attempts

    Returns:
        Batch ID string
    """
    processor = BatchProcessor(api_key=api_key, model=model)
    return processor.submit_batch(requests, custom_id_prefix=custom_id_prefix, max_retries=max_retries)


def poll_results(
    batch_id: str,
    api_key: str,
    poll_interval: int = 60,
    timeout: int = 86400
) -> List[Dict[str, Any]]:
    """Convenience function to poll batch results without creating BatchProcessor instance.

    Args:
        batch_id: Batch ID from submit_batch()
        api_key: Anthropic API key
        poll_interval: Seconds between status checks
        timeout: Maximum wait time in seconds

    Returns:
        List of parsed result dictionaries
    """
    # Use a placeholder model since we only need client for retrieval
    processor = BatchProcessor(api_key=api_key, model="claude-opus-4-20250514")
    return processor.poll_results(batch_id, poll_interval=poll_interval, timeout=timeout)
