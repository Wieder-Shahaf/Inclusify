"""Utility modules for data synthesis."""

# Conditional imports to avoid requiring anthropic package when using vLLM
try:
    from .batch_processor import BatchProcessor, submit_batch, poll_results
    _has_batch_processor = True
except ImportError:
    _has_batch_processor = False
    BatchProcessor = None
    submit_batch = None
    poll_results = None

# Always available imports
from .json_extractor import extract_json, validate_sample_schema
from .vllm_processor import VLLMProcessor, health_check

__all__ = [
    "extract_json",
    "validate_sample_schema",
    "VLLMProcessor",
    "health_check"
]

if _has_batch_processor:
    __all__.extend(["BatchProcessor", "submit_batch", "poll_results"])
