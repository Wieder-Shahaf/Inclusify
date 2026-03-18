"""Tests for Claude Batch API processor.

These tests validate the batch processing workflow:
1. Submit batch requests to Claude API
2. Poll for completion
3. Parse and return results
4. Handle errors and retries
"""

import pytest
import json
from unittest.mock import MagicMock, patch, call
from ml.data_synthesis.utils.batch_processor import (
    BatchProcessor,
    submit_batch,
    poll_results,
    validate_requests,
    parse_batch_results,
)


class TestBatchProcessor:
    """Tests for BatchProcessor class"""

    def test_init_with_api_key(self):
        """Test BatchProcessor initialization with API key"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")
        assert processor.model == "claude-opus-4-20250514"
        assert processor.client is not None

    def test_submit_batch_creates_valid_request(self):
        """Test 1: submit_batch() creates valid request and returns batch_id"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")

        # Mock the Anthropic client
        mock_batch = MagicMock()
        mock_batch.id = "batch_test_12345"
        processor.client.messages.batches.create = MagicMock(return_value=mock_batch)

        # Create sample requests
        requests = [
            {
                "custom_id": "req_1",
                "params": {
                    "model": "claude-opus-4-20250514",
                    "max_tokens": 500,
                    "messages": [
                        {"role": "system", "content": "Test system prompt"},
                        {"role": "user", "content": "Test user message"}
                    ]
                }
            }
        ]

        # Submit batch
        batch_id = processor.submit_batch(requests, custom_id_prefix="test")

        # Assertions
        assert batch_id == "batch_test_12345"
        processor.client.messages.batches.create.assert_called_once()
        call_args = processor.client.messages.batches.create.call_args
        assert "requests" in call_args[1]

    def test_poll_results_waits_for_completion(self):
        """Test 2: poll_results() waits for completion and returns parsed results"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")

        # Mock batch retrieval - first "in_progress", then "ended"
        mock_batch_in_progress = MagicMock()
        mock_batch_in_progress.processing_status = "in_progress"

        mock_batch_ended = MagicMock()
        mock_batch_ended.processing_status = "ended"
        mock_batch_ended.results_url = "https://api.anthropic.com/results/123"

        processor.client.messages.batches.retrieve = MagicMock(
            side_effect=[mock_batch_in_progress, mock_batch_ended]
        )

        # Mock results retrieval
        processor.client.messages.batches.results = MagicMock(
            return_value=[
                {
                    "custom_id": "req_1",
                    "result": {
                        "type": "succeeded",
                        "message": {
                            "content": [{"text": '{"sentence": "Test", "severity_label": "Correct", "explanation": "Test"}'}]
                        }
                    }
                }
            ]
        )

        # Poll results with short interval for testing
        results = processor.poll_results("batch_test_12345", poll_interval=0.1)

        # Assertions
        assert len(results) == 1
        assert results[0]["custom_id"] == "req_1"
        assert results[0]["result"]["type"] == "succeeded"

    def test_retry_logic_handles_transient_failures(self):
        """Test 3: Retry logic handles transient API failures (max 3 retries)"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")

        # Mock client that fails twice then succeeds
        mock_batch = MagicMock()
        mock_batch.id = "batch_retry_test"

        processor.client.messages.batches.create = MagicMock(
            side_effect=[
                Exception("Transient error 1"),
                Exception("Transient error 2"),
                mock_batch  # Third attempt succeeds
            ]
        )

        requests = [{"custom_id": "req_1", "params": {"model": "test", "max_tokens": 100, "messages": [{"role": "user", "content": "test"}]}}]

        # Should succeed after retries
        batch_id = processor.submit_batch(requests, custom_id_prefix="test", max_retries=3)
        assert batch_id == "batch_retry_test"
        assert processor.client.messages.batches.create.call_count == 3

    def test_malformed_jsonl_raises_validation_error(self):
        """Test 4: Malformed request raises clear validation error"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")

        # Missing required fields
        invalid_requests = [
            {"custom_id": "req_1"}  # Missing 'params'
        ]

        with pytest.raises(ValueError, match="Missing required field"):
            processor.submit_batch(invalid_requests, custom_id_prefix="test")

    def test_batch_failure_returns_error_details(self):
        """Test 5: Batch job failure returns error details in results"""
        processor = BatchProcessor(api_key="test_key", model="claude-opus-4-20250514")

        # Mock failed batch
        mock_batch_failed = MagicMock()
        mock_batch_failed.processing_status = "ended"
        processor.client.messages.batches.retrieve = MagicMock(return_value=mock_batch_failed)

        # Mock results with error
        processor.client.messages.batches.results = MagicMock(
            return_value=[
                {
                    "custom_id": "req_1",
                    "result": {
                        "type": "errored",
                        "error": {
                            "type": "invalid_request",
                            "message": "Invalid API request"
                        }
                    }
                }
            ]
        )

        results = processor.poll_results("batch_test_fail")

        # Assertions
        assert len(results) == 1
        assert results[0]["result"]["type"] == "errored"
        assert "error" in results[0]["result"]


class TestHelperFunctions:
    """Tests for standalone helper functions"""

    def test_validate_requests_valid(self):
        """Test validate_requests accepts valid request format"""
        requests = [
            {
                "custom_id": "req_1",
                "params": {
                    "model": "claude-opus-4-20250514",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": "Test"}]
                }
            }
        ]
        # Should not raise
        validate_requests(requests)

    def test_validate_requests_missing_fields(self):
        """Test validate_requests rejects missing required fields"""
        invalid_requests = [
            {"custom_id": "req_1"}  # Missing params
        ]
        with pytest.raises(ValueError, match="Missing required field"):
            validate_requests(invalid_requests)

    def test_parse_batch_results_extracts_content(self):
        """Test parse_batch_results extracts message content"""
        raw_results = [
            {
                "custom_id": "req_1",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"text": '{"sentence": "Test"}'}]
                    }
                }
            }
        ]

        parsed = parse_batch_results(raw_results)
        assert len(parsed) == 1
        assert parsed[0]["custom_id"] == "req_1"


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions"""

    @patch('ml.data_synthesis.utils.batch_processor.BatchProcessor')
    def test_submit_batch_function(self, mock_processor_class):
        """Test submit_batch convenience function"""
        mock_processor = MagicMock()
        mock_processor.submit_batch.return_value = "batch_123"
        mock_processor_class.return_value = mock_processor

        requests = [{"custom_id": "req_1", "params": {"model": "test", "max_tokens": 100, "messages": [{"role": "user", "content": "test"}]}}]
        batch_id = submit_batch(requests, api_key="test_key", model="test_model")

        assert batch_id == "batch_123"
        mock_processor.submit_batch.assert_called_once()

    @patch('ml.data_synthesis.utils.batch_processor.BatchProcessor')
    def test_poll_results_function(self, mock_processor_class):
        """Test poll_results convenience function"""
        mock_processor = MagicMock()
        mock_processor.poll_results.return_value = [{"custom_id": "req_1", "result": {}}]
        mock_processor_class.return_value = mock_processor

        results = poll_results("batch_123", api_key="test_key")

        assert len(results) == 1
        mock_processor.poll_results.assert_called_once_with("batch_123", poll_interval=60, timeout=86400)
