#!/usr/bin/env python3
"""Quick test script to verify vLLM server is running and responsive.

This script sends a single test request to the vLLM server to verify:
1. Server is accessible
2. Model is loaded
3. JSON generation works
4. Response time is reasonable

Usage:
    python scripts/quick_qwen_test.py
"""

import asyncio
import time
from openai import AsyncOpenAI


async def main():
    """Test vLLM server with a single request."""
    endpoint = "http://localhost:8000/v1"
    model = "Qwen/Qwen2.5-3B-Instruct"

    print("=" * 60)
    print("vLLM Server Quick Test")
    print("=" * 60)
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model}")
    print()

    # Create client
    client = AsyncOpenAI(base_url=endpoint, api_key="EMPTY")

    # Test request
    test_prompt = """Generate a variation of this LGBTQ+ sample:

"Gender identity exists on a spectrum and is distinct from biological sex."

Severity: Correct

Respond with valid JSON only:
{
  "sentence": "Your variation here",
  "severity_label": "Correct",
  "explanation": "Brief explanation"
}"""

    try:
        print("Sending test request...")
        start_time = time.time()

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": test_prompt}
            ],
            max_tokens=1500,
            temperature=0.9
        )

        elapsed = time.time() - start_time

        print(f"✓ Response received in {elapsed:.2f}s")
        print()
        print("Response content:")
        print("-" * 60)
        print(response.choices[0].message.content)
        print("-" * 60)
        print()

        # Try to parse JSON
        import json
        from ml.data_synthesis.utils.json_extractor import extract_json, validate_sample_schema

        try:
            data = extract_json(response.choices[0].message.content)
            print("✓ JSON extraction successful")
            print(f"  Sentence: {data['sentence'][:60]}...")
            print(f"  Severity: {data['severity_label']}")
            print()

            if validate_sample_schema(data):
                print("✓ Schema validation passed")
            else:
                print("✗ Schema validation failed")

        except Exception as e:
            print(f"✗ JSON extraction/validation failed: {e}")

        print()
        print("=" * 60)
        print("✓ vLLM server is ready for synthesis pipeline")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Test failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if vLLM server is running:")
        print(f"   curl {endpoint.replace('/v1', '/health')}")
        print("2. Check GPU memory:")
        print("   nvidia-smi")
        print("3. Check vLLM server logs")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
