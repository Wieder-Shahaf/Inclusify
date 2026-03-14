"""English dataset synthesis orchestration script.

This script orchestrates the LLM-based generation of 10K+ English samples:
1. Load existing 988-sample dataset
2. Calculate stratified per-class targets (11K total for 10% buffer)
3. Generate batch requests with diverse prompts
4. Submit batches to Claude API and poll for completion
5. Parse results, validate schema, filter invalid samples
6. Save to data/english_10k.csv

Usage:
    python ml/data_synthesis/synthesize_english.py
"""

import os
import json
import logging
import random
import asyncio
from typing import Dict, List, Any
from pathlib import Path
import pandas as pd

from ml.training.prepare_data import load_dataset
from ml.data_synthesis.config import (
    MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    ANTHROPIC_API_KEY,
    BATCH_SIZE,
    INPUT_CSV,
    OUTPUT_CSV,
    INTERMEDIATE_DIR,
    TOTAL_TARGET,
    VLLM_ENABLED,
    VLLM_ENDPOINT,
    VLLM_MODEL,
    VLLM_LORA_PATH,
    VLLM_BATCH_SIZE,
    VLLM_MAX_THROUGHPUT,
)

# Import appropriate processor based on backend
if VLLM_ENABLED:
    from ml.data_synthesis.utils.vllm_processor import VLLMProcessor
else:
    from ml.data_synthesis.utils.batch_processor import BatchProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_existing_dataset() -> pd.DataFrame:
    """Load existing augmented dataset.

    Returns:
        DataFrame with 988 unique samples after deduplication
    """
    logger.info(f"Loading existing dataset from {INPUT_CSV}")
    df = load_dataset(INPUT_CSV)
    logger.info(f"Loaded {len(df)} unique samples")
    return df


def calculate_generation_targets(
    current_df: pd.DataFrame,
    total_target: int = TOTAL_TARGET
) -> Dict[str, int]:
    """Calculate per-class generation targets using stratified sampling.

    Args:
        current_df: Current dataset DataFrame
        total_target: Total target sample count (default 11,000)

    Returns:
        Dictionary mapping severity labels to generation counts
    """
    current_counts = current_df['Severity Label'].value_counts().to_dict()
    total_current = len(current_df)

    targets = {}
    for label, count in current_counts.items():
        # Stratified: maintain same proportion
        proportion = count / total_current
        target_total = int(total_target * proportion)
        # Generate delta (new samples needed)
        to_generate = target_total - count
        targets[label] = max(0, to_generate)  # Ensure non-negative

    logger.info(f"Generation targets: {targets}")
    logger.info(f"Total to generate: {sum(targets.values())}")

    return targets


def generate_batch_requests(
    targets: Dict[str, int],
    seed_df: pd.DataFrame,
    model: str = MODEL,
    system_prompt: str = None
) -> List[Dict[str, Any]]:
    """Generate batch requests for Claude API.

    Args:
        targets: Dictionary of {severity_label: count}
        seed_df: DataFrame with seed samples to vary
        model: Model name
        system_prompt: System prompt (loads from file if None)

    Returns:
        List of batch request dictionaries
    """
    if system_prompt is None:
        # Load appropriate system prompt based on backend
        if VLLM_ENABLED:
            prompt_file = Path(__file__).parent / "prompts" / "english_variations_qwen.txt"
        else:
            prompt_file = Path(__file__).parent / "prompts" / "english_variations.txt"
        with open(prompt_file, 'r') as f:
            system_prompt = f.read().strip()

    requests = []
    request_id = 0

    # Prompt variation templates
    variation_templates = [
        "Generate a variation of this sample in the domain of {domain}. Maintain the same severity classification.",
        "Rewrite this sample using {framing} framing while preserving the severity level.",
        "Create a variation of this sample with different terminology and sentence structure.",
        "Generate a similar sample that would appear in a {domain} research paper.",
        "Rephrase this sample using different academic vocabulary while maintaining its classification.",
    ]

    domains = ["psychology", "sociology", "medicine", "education", "law", "anthropology", "public health", "gender studies"]
    framings = ["clinical", "activist", "descriptive", "critical", "policy-oriented", "historical"]

    for severity_label, count in targets.items():
        # Get seed samples for this severity class
        seed_samples = seed_df[seed_df['Severity Label'] == severity_label]

        if len(seed_samples) == 0:
            logger.warning(f"No seed samples for severity '{severity_label}', skipping")
            continue

        for i in range(count):
            # Sample a seed sentence
            seed_row = seed_samples.sample(n=1).iloc[0]
            seed_sentence = seed_row['Sentence']
            seed_explanation = seed_row['Explanation']

            # Choose random variation template
            template = random.choice(variation_templates)
            domain = random.choice(domains)
            framing = random.choice(framings)

            user_prompt = f"""Seed sample:
Sentence: {seed_sentence}
Severity: {severity_label}
Explanation: {seed_explanation}

{template.format(domain=domain, framing=framing)}

Respond with ONLY valid JSON (no markdown):
{{"sentence": "...", "severity_label": "{severity_label}", "explanation": "..."}}"""

            # Create batch request
            request = {
                "custom_id": f"{severity_label}_{request_id}",
                "params": {
                    "model": model,
                    "max_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
            }

            requests.append(request)
            request_id += 1

    logger.info(f"Generated {len(requests)} batch requests")
    return requests


def parse_and_save_results(
    batch_results: List[Dict[str, Any]],
    output_path: str
) -> int:
    """Parse batch results, validate, and save to CSV.

    Args:
        batch_results: Results from BatchProcessor.poll_results()
        output_path: Path to save output CSV

    Returns:
        Count of valid samples saved
    """
    valid_samples = []
    invalid_count = 0

    allowed_severity_labels = [
        "Correct",
        "Outdated",
        "Biased",
        "Potentially Offensive",
        "Factually Incorrect"
    ]

    for item in batch_results:
        custom_id = item.get('custom_id')
        result = item.get('result', {})

        # Skip errored results
        if result.get('type') == 'errored':
            logger.warning(f"Skipping errored result: {custom_id}")
            invalid_count += 1
            continue

        # Extract message content
        try:
            message = result.get('message', {})
            content_blocks = message.get('content', [])
            if not content_blocks:
                logger.warning(f"No content in result: {custom_id}")
                invalid_count += 1
                continue

            text = content_blocks[0].get('text', '')
            data = json.loads(text)

            # Validate schema
            sentence = data.get('sentence', '').strip()
            severity_label = data.get('severity_label', '').strip()
            explanation = data.get('explanation', '').strip()

            if not sentence:
                logger.warning(f"Empty sentence in result: {custom_id}")
                invalid_count += 1
                continue

            if severity_label not in allowed_severity_labels:
                logger.warning(f"Invalid severity label '{severity_label}' in result: {custom_id}")
                invalid_count += 1
                continue

            if not explanation:
                logger.warning(f"Empty explanation in result: {custom_id}")
                invalid_count += 1
                continue

            # Valid sample
            valid_samples.append({
                'Sentence': sentence,
                'Severity Label': severity_label,
                'Explanation': explanation
            })

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse result {custom_id}: {e}")
            invalid_count += 1
            continue

    # Save to CSV
    df = pd.DataFrame(valid_samples)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    logger.info(f"Saved {len(valid_samples)} valid samples to {output_path}")
    logger.info(f"Filtered out {invalid_count} invalid samples")

    return len(valid_samples)


def main():
    """Main orchestration function."""
    logger.info("=== Starting English dataset synthesis ===")

    # Check API key (only required for Claude backend)
    if not VLLM_ENABLED and not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Step 1: Load existing dataset
    existing_df = load_existing_dataset()

    # Step 2: Calculate generation targets
    targets = calculate_generation_targets(existing_df)

    # Step 3: Generate batch requests
    requests = generate_batch_requests(targets, existing_df)

    # Create intermediate directory
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    intermediate_jsonl = os.path.join(INTERMEDIATE_DIR, "english_raw_11k.jsonl")

    # Step 4: Process requests with appropriate backend
    all_results = []

    if VLLM_ENABLED:
        logger.info(f"Using vLLM backend: {VLLM_ENDPOINT}")
        logger.info(f"Model: {VLLM_MODEL}")
        logger.info(f"Batch size: {VLLM_BATCH_SIZE}, Max throughput: {VLLM_MAX_THROUGHPUT} req/sec")

        # Create vLLM processor
        processor = VLLMProcessor(
            endpoint=VLLM_ENDPOINT,
            model=VLLM_MODEL,
            lora_path=VLLM_LORA_PATH
        )

        # Process all requests in one async call
        logger.info(f"Processing {len(requests)} requests...")
        results = asyncio.run(processor.generate_batch(
            requests=requests,
            batch_size=VLLM_BATCH_SIZE,
            max_throughput=VLLM_MAX_THROUGHPUT,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        ))
        all_results.extend(results)
        logger.info(f"vLLM processing completed with {len(results)} results")

    else:
        logger.info(f"Using Claude Batch API backend")
        logger.info(f"Model: {MODEL}")

        # Create Claude batch processor
        processor = BatchProcessor(api_key=ANTHROPIC_API_KEY, model=MODEL)

        # Split requests into chunks
        chunk_size = BATCH_SIZE
        num_chunks = (len(requests) + chunk_size - 1) // chunk_size
        logger.info(f"Splitting {len(requests)} requests into {num_chunks} batches (size {chunk_size})")

        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(requests))
            chunk = requests[start_idx:end_idx]

            logger.info(f"=== Batch {i + 1}/{num_chunks} ===")
            logger.info(f"Submitting {len(chunk)} requests...")

            # Submit batch
            batch_id = processor.submit_batch(chunk, custom_id_prefix=f"batch_{i}")
            logger.info(f"Batch submitted: {batch_id}")

            # Poll for completion
            logger.info("Polling for completion (this may take several hours)...")
            results = processor.poll_results(batch_id, poll_interval=60)

            all_results.extend(results)
            logger.info(f"Batch {i + 1}/{num_chunks} completed with {len(results)} results")

    # Save intermediate results
    with open(intermediate_jsonl, 'w') as f:
        for result in all_results:
            f.write(json.dumps(result) + '\n')
    logger.info(f"Saved intermediate results to {intermediate_jsonl}")

    # Step 5: Parse and save final results
    valid_count = parse_and_save_results(all_results, OUTPUT_CSV)

    logger.info("=== Synthesis complete ===")
    logger.info(f"Generated: {valid_count} valid samples")
    logger.info(f"Output: {OUTPUT_CSV}")
    logger.info(f"Intermediate: {intermediate_jsonl}")


if __name__ == "__main__":
    main()
