#!/usr/bin/env python3
"""
Quick test for DictaLM Hebrew translation.

Tests translation of 5 samples to verify:
1. Server is running
2. Hebrew output quality
3. No mixed-language artifacts
4. Proper JSON parsing

Usage:
    python scripts/test_dictalm_translation.py
"""

import asyncio
from openai import AsyncOpenAI


DICTALM_ENDPOINT = "http://localhost:8001/v1"


TEST_SAMPLES = [
    ("Gender identity exists on a spectrum.", "Correct"),
    ("Conversion therapy is harmful and unethical.", "Correct"),
    ("Transgender individuals face discrimination.", "Biased"),
    ("Homosexuality was classified as mental illness.", "Outdated"),
    ("LGBTQ+ people recruit children.", "Factually Incorrect")
]


async def test_translation():
    """Test DictaLM translation with 5 samples."""
    print("=" * 70)
    print("DictaLM Hebrew Translation Test")
    print("=" * 70)
    print(f"Endpoint: {DICTALM_ENDPOINT}")
    print(f"Model: DictaLM-3.0-Nemotron-12B-Instruct")
    print()

    client = AsyncOpenAI(base_url=DICTALM_ENDPOINT, api_key="EMPTY")

    for i, (sentence, severity) in enumerate(TEST_SAMPLES, 1):
        print(f"\n--- Test {i}/5 ({severity}) ---")
        print(f"English: {sentence}")

        prompt = f"""אתה מתרגם עברי מקצועי. תרגם לעברית אקדמית:

"{sentence}"

פלט JSON בלבד:
{{
  "hebrew": "תרגום כאן"
}}"""

        try:
            response = await client.chat.completions.create(
                model="dicta-il/DictaLM-3.0-Nemotron-12B-Instruct",
                messages=[
                    {"role": "system", "content": "אתה מתרגם מומחה לעברית."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            content = response.choices[0].message.content
            print(f"Response: {content[:200]}...")

            # Try to extract JSON
            import json
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                data = json.loads(content)
                hebrew = data.get('hebrew', content)
            except:
                hebrew = content

            print(f"Hebrew: {hebrew}")

            # Check for mixed languages
            has_english = any(c.isascii() and c.isalpha() for c in hebrew if c not in "LGBTQ+")
            has_chinese = any(ord(c) >= 0x4E00 and ord(c) <= 0x9FFF for c in hebrew)

            if has_english:
                print("⚠️  WARNING: English characters detected")
            if has_chinese:
                print("⚠️  WARNING: Chinese characters detected")
            if not (has_english or has_chinese):
                print("✓ Clean Hebrew output")

        except Exception as e:
            print(f"✗ Error: {e}")

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_translation())
