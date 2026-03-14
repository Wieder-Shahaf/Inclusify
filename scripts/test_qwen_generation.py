#!/usr/bin/env python3
"""
Test dataset generation using Qwen 2.5 on vLLM VM.
Compare quality with Claude Opus samples.
"""

import csv
import json
import requests
from pathlib import Path

# vLLM endpoint (adjust if different)
VLLM_ENDPOINT = "http://localhost:8000/v1/completions"  # or your VM IP
VLLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # or 14B if available

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

    return f"""You are an expert in LGBTQ+ inclusive language and academic writing. Generate {count} diverse training samples for detecting non-inclusive language in academic texts.

**Task:** Generate {count} samples with Severity Label = "{label}"

**Required JSON Schema:**
Each sample must have exactly 4 fields:
- "Sentence": Academic text (1-2 sentences)
- "Severity Label": "{label}"
- "Rule Category": Category of issue (or "N/A" if Correct)
- "Explanation": Why this is classified as {label}

**Examples from dataset:**
{examples_text}

**Diversity requirements:**
1. Domain variation: psychology, sociology, medicine, law, education, anthropology
2. Framing variation: clinical, research findings, policy, historical claims
3. Terminology: use varied LGBTQ+ terms
4. Academic tone suitable for scholarly papers

**Critical:** Output ONLY valid JSON array. No markdown, no ```json```, no explanations. Just the raw JSON array.

Generate exactly {count} unique samples now:"""

def test_qwen_generation(vllm_url=None):
    """Test generation with Qwen 2.5 via vLLM."""

    if vllm_url is None:
        print("⚠️  vLLM endpoint not provided. Using default: http://localhost:8000")
        print("   To use your VM, pass the VM IP as argument.")
        vllm_url = "http://localhost:8000/v1/completions"

    # Load examples
    print("Loading examples...")
    examples = load_examples()

    # Test with same config as Claude: 10 samples of "Correct"
    test_label = "Correct"
    test_count = 10

    print(f"\n🧪 TEST GENERATION (Qwen 2.5)")
    print(f"Label: {test_label}")
    print(f"Count: {test_count}")
    print(f"Endpoint: {vllm_url}")

    prompt = create_generation_prompt(test_label, test_count, examples[test_label])

    print(f"\n📤 Sending request to vLLM...")

    try:
        response = requests.post(
            vllm_url,
            json={
                "model": VLLM_MODEL,
                "prompt": prompt,
                "max_tokens": 4000,
                "temperature": 0.8,
                "top_p": 0.9,
            },
            timeout=120
        )

        if response.status_code != 200:
            print(f"❌ vLLM request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return

        result = response.json()
        result_text = result['choices'][0]['text'].strip()

        # Try to parse as JSON
        try:
            samples = json.loads(result_text)
            print(f"\n✅ Generated {len(samples)} samples")

            # Validate schema
            required_fields = {'Sentence', 'Severity Label', 'Rule Category', 'Explanation'}
            valid_samples = [s for s in samples if set(s.keys()) == required_fields]

            print(f"✅ Valid samples: {len(valid_samples)}/{len(samples)}")

            if valid_samples:
                print("\n📋 Sample outputs:")
                for i, sample in enumerate(valid_samples[:2], 1):
                    print(f"\n{i}. {sample['Sentence']}")
                    print(f"   Category: {sample['Rule Category']}")
                    print(f"   Explanation: {sample['Explanation'][:80]}...")

                # Save test results
                output_dir = Path('data/intermediate')
                output_dir.mkdir(parents=True, exist_ok=True)

                output_file = output_dir / 'test_batch_qwen.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(valid_samples, f, indent=2, ensure_ascii=False)

                print(f"\n✅ Qwen test results saved to: {output_file}")

                # Load Claude samples for comparison
                claude_file = output_dir / 'test_batch.json'
                if claude_file.exists():
                    print("\n" + "="*80)
                    print("QUALITY COMPARISON")
                    print("="*80)
                    print("\nTo compare quality:")
                    print(f"1. Claude Opus samples: {claude_file}")
                    print(f"2. Qwen 2.5 samples: {output_file}")
                    print("\nReview for:")
                    print("- Academic tone quality")
                    print("- Terminology accuracy")
                    print("- Explanation depth")
                    print("- Sample diversity")

                print("\n💰 COST: $0.00 (local inference)")
                print("⚡ Speed: Can generate thousands of samples quickly")

                return valid_samples

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Response (first 500 chars): {result_text[:500]}")

            # Try to extract JSON if wrapped in markdown
            if "```json" in result_text:
                try:
                    json_start = result_text.index("[")
                    json_end = result_text.rindex("]") + 1
                    samples = json.loads(result_text[json_start:json_end])
                    print(f"✅ Extracted JSON from markdown: {len(samples)} samples")
                    # Continue with validation...
                except:
                    print("❌ Could not extract JSON")

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to vLLM at {vllm_url}")
        print("\n💡 To set up vLLM on your VM:")
        print("1. SSH to your Azure VM")
        print("2. Run: vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000")
        print("3. Then run this script with: python scripts/test_qwen_generation.py --vllm http://YOUR_VM_IP:8000/v1/completions")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    import sys

    vllm_url = None
    if len(sys.argv) > 1:
        vllm_url = sys.argv[1]

    test_qwen_generation(vllm_url)
