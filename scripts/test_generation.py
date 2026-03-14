#!/usr/bin/env python3
"""
Test dataset generation with a small batch to validate approach and estimate costs.
"""

import csv
import json
import os
from pathlib import Path
from anthropic import Anthropic

def load_examples():
    """Load example samples for each severity label."""
    examples = {}
    with open('data/Inclusify_Dataset.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row['Severity Label']
            if label not in examples:
                examples[label] = []
            if len(examples[label]) < 5:
                examples[label].append(row)
    return examples

def create_generation_prompt(label, count, examples):
    """Create prompt for generating samples."""
    examples_text = "\n".join([
        f"- Sentence: {ex['Sentence']}\n  Rule Category: {ex.get('Rule Category', 'N/A')}\n  Explanation: {ex['Explanation']}"
        for ex in examples[:5]
    ])

    return f"""Generate {count} diverse training samples for LGBTQ+ inclusive language detection in academic texts.

**Target Severity Label:** {label}

**Schema (4 fields required):**
- Sentence: Academic text sample (1-2 sentences)
- Severity Label: {label}
- Rule Category: Category of issue (or N/A if Correct)
- Explanation: Why this is classified as {label}

**Examples from existing dataset:**
{examples_text}

**Diversity requirements:**
1. Domain variation: psychology, sociology, medicine, law, education, anthropology
2. Framing variation: clinical language, research findings, policy statements, historical claims
3. Terminology variation: different LGBTQ+ terms and contexts
4. Academic tone suitable for scholarly analysis

**Output format:**
Return ONLY a valid JSON array with exactly {count} objects. Each object must have exactly these 4 fields: "Sentence", "Severity Label", "Rule Category", "Explanation".

Do NOT include markdown formatting or ```json``` blocks. Return raw JSON only.

Generate {count} unique samples now:"""

def test_generation():
    """Run a small test generation."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    client = Anthropic(api_key=api_key)

    # Load examples
    print("Loading examples...")
    examples = load_examples()

    # Test with ONE small batch: 10 samples of "Correct" label
    test_label = "Correct"
    test_count = 10

    print(f"\n🧪 TEST GENERATION")
    print(f"Label: {test_label}")
    print(f"Count: {test_count}")
    print(f"Model: claude-opus-4-20250514")

    prompt = create_generation_prompt(test_label, test_count, examples[test_label])

    print(f"\n📤 Sending request to Claude Opus 4.5...")

    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        result_text = response.content[0].text.strip()

        # Try to parse as JSON
        try:
            samples = json.loads(result_text)
            print(f"\n✅ Generated {len(samples)} samples")

            # Validate schema
            required_fields = {'Sentence', 'Severity Label', 'Rule Category', 'Explanation'}
            valid = all(set(s.keys()) == required_fields for s in samples)

            if valid:
                print("✅ Schema validation passed")

                # Show first 2 samples
                print("\n📋 Sample outputs:")
                for i, sample in enumerate(samples[:2], 1):
                    print(f"\n{i}. {sample['Sentence']}")
                    print(f"   Category: {sample['Rule Category']}")
                    print(f"   Explanation: {sample['Explanation'][:80]}...")

                # Save test results
                output_dir = Path('data/intermediate')
                output_dir.mkdir(parents=True, exist_ok=True)

                output_file = output_dir / 'test_batch.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(samples, f, indent=2, ensure_ascii=False)

                print(f"\n✅ Test results saved to: {output_file}")

                # Estimate costs
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

                # Opus pricing (approximate)
                input_cost = (input_tokens / 1_000_000) * 15
                output_cost = (output_tokens / 1_000_000) * 75
                total_cost = input_cost + output_cost

                print(f"\n💰 COST ANALYSIS")
                print(f"Input tokens: {input_tokens:,} (${input_cost:.4f})")
                print(f"Output tokens: {output_tokens:,} (${output_cost:.4f})")
                print(f"Total cost: ${total_cost:.4f}")

                # Extrapolate to full dataset
                cost_per_sample = total_cost / test_count
                samples_for_2k = 2000
                samples_for_10k = 10000

                cost_2k = cost_per_sample * samples_for_2k
                cost_10k = cost_per_sample * samples_for_10k

                print(f"\n📊 EXTRAPOLATED COSTS")
                print(f"Cost per sample: ${cost_per_sample:.4f}")
                print(f"For 2,000 samples: ${cost_2k:.2f}")
                print(f"For 10,000 samples: ${cost_10k:.2f}")

                print(f"\n⚠️  Your balance: $5.00")
                if cost_2k > 5:
                    max_samples = int(5 / cost_per_sample)
                    print(f"💡 Recommended: Generate up to {max_samples} samples with current balance")
                else:
                    print(f"✅ Sufficient for {int(5 / cost_per_sample)} samples")

            else:
                print("❌ Schema validation failed")
                print("Samples:", json.dumps(samples[:2], indent=2))

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Response (first 500 chars): {result_text[:500]}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_generation()
