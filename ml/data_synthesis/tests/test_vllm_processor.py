"""Unit tests for vLLM processor."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ml.data_synthesis.utils.vllm_processor import VLLMProcessor


@pytest.fixture
def sample_requests():
    """Sample batch requests."""
    return [
        {
            "custom_id": f"req_{i}",
            "params": {
                "messages": [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": f"Generate variation {i}"}
                ],
                "max_tokens": 1500,
                "temperature": 0.9
            }
        }
        for i in range(5)
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = '''{"sentence": "Test sentence", "severity_label": "Correct", "explanation": "Valid explanation text"}'''
    return response


class TestVLLMProcessor:
    """Test vLLM processor functionality."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = VLLMProcessor(
            endpoint="http://localhost:8000/v1",
            model="Qwen/Qwen2.5-3B-Instruct"
        )
        assert processor.model == "Qwen/Qwen2.5-3B-Instruct"
        assert processor.lora_path is None

    def test_initialization_with_lora(self):
        """Test processor initialization with LoRA adapter."""
        processor = VLLMProcessor(
            endpoint="http://localhost:8000/v1",
            model="Qwen/Qwen2.5-3B-Instruct",
            lora_path="/path/to/lora"
        )
        assert processor.lora_path == "/path/to/lora"

    @pytest.mark.asyncio
    async def test_generate_single_success(self, sample_requests, mock_openai_response):
        """Test successful single request generation."""
        processor = VLLMProcessor()

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response

            result = await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9
            )

            assert result["custom_id"] == "req_0"
            assert result["result"]["type"] == "succeeded"
            assert result["result"]["data"]["sentence"] == "Test sentence"
            assert result["result"]["data"]["severity_label"] == "Correct"

    @pytest.mark.asyncio
    async def test_generate_single_with_retry(self, sample_requests):
        """Test retry logic on failure."""
        processor = VLLMProcessor()

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            # Fail twice, then succeed
            mock_create.side_effect = [
                Exception("Connection error"),
                Exception("Timeout"),
                MagicMock(choices=[MagicMock(message=MagicMock(
                    content='{"sentence": "Test", "severity_label": "Correct", "explanation": "Valid explanation here"}'
                ))])
            ]

            result = await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9,
                max_retries=3
            )

            assert result["result"]["type"] == "succeeded"
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_single_max_retries_exceeded(self, sample_requests):
        """Test that max retries results in error."""
        processor = VLLMProcessor()

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Persistent error")

            result = await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9,
                max_retries=3
            )

            assert result["result"]["type"] == "error"
            assert "Persistent error" in result["result"]["error"]
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_single_with_lora(self, sample_requests, mock_openai_response):
        """Test that LoRA adapter is injected correctly."""
        processor = VLLMProcessor(lora_path="/path/to/lora")

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response

            await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9
            )

            # Verify extra_body contains LoRA path
            call_kwargs = mock_create.call_args.kwargs
            assert "extra_body" in call_kwargs
            assert call_kwargs["extra_body"]["lora_path"] == "/path/to/lora"

    @pytest.mark.asyncio
    async def test_generate_single_handles_markdown_wrapped_json(self, sample_requests):
        """Test extraction of JSON from markdown code blocks."""
        processor = VLLMProcessor()

        markdown_response = MagicMock()
        markdown_response.choices = [MagicMock()]
        markdown_response.choices[0].message.content = '''```json
{"sentence": "Test sentence", "severity_label": "Biased", "explanation": "Valid explanation text"}
```'''

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = markdown_response

            result = await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9
            )

            assert result["result"]["type"] == "succeeded"
            assert result["result"]["data"]["severity_label"] == "Biased"

    @pytest.mark.asyncio
    async def test_generate_single_schema_validation_failure(self, sample_requests):
        """Test that schema validation failure results in error."""
        processor = VLLMProcessor()

        invalid_response = MagicMock()
        invalid_response.choices = [MagicMock()]
        invalid_response.choices[0].message.content = '''{"sentence": "Short", "severity_label": "InvalidLabel", "explanation": "Too short"}'''

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = invalid_response

            result = await processor._generate_single(
                request=sample_requests[0],
                max_tokens=1500,
                temperature=0.9,
                max_retries=1
            )

            assert result["result"]["type"] == "error"
            assert "Schema validation failed" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_generate_batch_splits_correctly(self, sample_requests, mock_openai_response):
        """Test that batch processing splits requests correctly."""
        processor = VLLMProcessor()

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response

            # Process 5 requests with batch size 2
            # Should create 3 batches: [2, 2, 1]
            results = await processor.generate_batch(
                requests=sample_requests,
                batch_size=2,
                max_throughput=100  # High throughput to avoid delays in tests
            )

            assert len(results) == 5
            assert all(r["result"]["type"] == "succeeded" for r in results)

    @pytest.mark.asyncio
    async def test_generate_batch_rate_limiting(self, sample_requests, mock_openai_response):
        """Test that rate limiting introduces appropriate delays."""
        processor = VLLMProcessor()

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response

            # Mock asyncio.sleep to track delays
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                await processor.generate_batch(
                    requests=sample_requests,
                    batch_size=2,
                    max_throughput=10  # 10 req/sec = 0.2s per request, 2 requests = 0.2s delay
                )

                # Should have delays between batches (not after last batch)
                # 5 requests / batch_size 2 = 3 batches → 2 delays
                assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_batch_handles_mixed_results(self, sample_requests):
        """Test that batch processing handles mix of success and failures."""
        processor = VLLMProcessor()

        responses = [
            # Success
            MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"sentence": "Valid sentence", "severity_label": "Correct", "explanation": "Valid explanation text"}'
            ))]),
            # Failure (will retry and fail)
            Exception("API Error"),
            # Success
            MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"sentence": "Another valid sentence", "severity_label": "Biased", "explanation": "Valid explanation text"}'
            ))]),
        ]

        with patch.object(processor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            # Use side_effect to return different responses
            # Need to account for retries (3 attempts for middle request)
            mock_create.side_effect = [
                responses[0],  # req_0 success
                responses[1], responses[1], responses[1],  # req_1 fails 3 times
                responses[2],  # req_2 success
            ]

            results = await processor.generate_batch(
                requests=sample_requests[:3],
                batch_size=10,
                max_throughput=100
            )

            assert len(results) == 3
            assert results[0]["result"]["type"] == "succeeded"
            assert results[1]["result"]["type"] == "error"
            assert results[2]["result"]["type"] == "succeeded"


@pytest.mark.asyncio
async def test_health_check_success():
    """Test health check with successful response."""
    from ml.data_synthesis.utils.vllm_processor import health_check

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

        result = await health_check("http://localhost:8000/health")
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure():
    """Test health check with failed response."""
    from ml.data_synthesis.utils.vllm_processor import health_check

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

        result = await health_check("http://localhost:8000/health")
        assert result is False


@pytest.mark.asyncio
async def test_health_check_exception():
    """Test health check with connection exception."""
    from ml.data_synthesis.utils.vllm_processor import health_check

    with patch('aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Connection failed")

        result = await health_check("http://localhost:8000/health")
        assert result is False
