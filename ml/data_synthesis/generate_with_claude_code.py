#!/usr/bin/env python3
"""
Generate dataset samples using Claude Code's built-in Opus 4.6 access.

This script coordinates batch generation by creating prompts that can be
executed through Claude Code Task agents, avoiding the need for direct API access.

Usage:
    python ml/data_synthesis/generate_with_claude_code.py --target 10000 --batch-size 100
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_existing_dataset(csv_path: str) -> List[Dict[str, str]]:
    """Load existing dataset to understand patterns."""
    samples = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append(row)
    return samples

def analyze_distribution(samples: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze class distribution and statistics."""
    severity_counts = Counter(row['Severity Label'] for row in samples)
    total = len(samples)

    distribution = {
        label: {
            'count': count,
            'percentage': (count / total) * 100
        }
        for label, count in severity_counts.items()
    }

    return {
        'total_samples': total,
        'distribution': distribution,
        'severity_labels': list(severity_counts.keys())
    }

def calculate_targets(current: int, target: int, distribution: Dict) -> Dict[str, int]:
    """Calculate how many samples to generate per class."""
    current_dist = distribution['distribution']
    targets = {}

    for label, stats in current_dist.items():
        # Maintain proportional distribution
        target_count = int((stats['percentage'] / 100) * target)
        current_count = stats['count']
        needed = max(0, target_count - current_count)
        targets[label] = needed

    return targets

def generate_prompt_for_batch(
    severity_label: str,
    count: int,
    examples: List[Dict[str, str]],
    batch_num: int
) -> str:
    """Generate a prompt for Claude to create a batch of samples."""

    # Get 3-5 examples of this severity label
    label_examples = [ex for ex in examples if ex['Severity Label'] == severity_label][:5]

    examples_text = "\n".join([
        f"- Sentence: {ex['Sentence']}\n  Rule Category: {ex.get('Rule Category', 'N/A')}\n  Explanation: {ex['Explanation']}"
        for ex in label_examples
    ])

    prompt = f"""Generate {count} diverse training samples for LGBTQ+ inclusive language detection.

**Target Severity Label:** {severity_label}

**Schema:**
- Sentence: Academic text sample (1-2 sentences)
- Severity Label: {severity_label}
- Rule Category: Category of issue (or N/A if Correct)
- Explanation: Why this is classified as {severity_label}

**Example format from existing dataset:**
{examples_text}

**Diversity requirements:**
1. **Domain variation:** psychology, sociology, medicine, law, education, anthropology, biology, history
2. **Framing variation:** clinical language, research findings, policy statements, historical claims, comparative analysis, definitional claims
3. **Terminology variation:** different LGBTQ+ terms and contexts
4. **Complexity variation:** simple statements, compound claims, cited statistics, quoted experts

**Output format:**
Return ONLY valid JSON array with exactly {count} objects. Each object must have exactly 4 fields: "Sentence", "Severity Label", "Rule Category", "Explanation".

Example structure:
[
  {{
    "Sentence": "...",
    "Severity Label": "{severity_label}",
    "Rule Category": "...",
    "Explanation": "..."
  }},
  ...
]

**IMPORTANT:**
- Return ONLY the JSON array, no markdown formatting, no ```json``` blocks
- Ensure all {count} samples are unique and diverse
- Maintain academic tone suitable for scholarly analysis
- For Hebrew context: Use culturally-appropriate Israeli LGBTQ+ terminology when relevant

Generate {count} samples now:"""

    return prompt

def save_batch_samples(samples: List[Dict], output_file: str, mode: str = 'a'):
    """Save generated samples to CSV."""
    file_exists = Path(output_file).exists()

    with open(output_file, mode, newline='', encoding='utf-8') as f:
        fieldnames = ['Sentence', 'Severity Label', 'Rule Category', 'Explanation']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists or mode == 'w':
            writer.writeheader()

        writer.writerows(samples)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate dataset using Claude Code')
    parser.add_argument('--target', type=int, default=10000, help='Target total samples')
    parser.add_argument('--batch-size', type=int, default=100, help='Samples per batch')
    parser.add_argument('--input', type=str, default='data/Inclusify_Dataset.csv', help='Input dataset')
    parser.add_argument('--output', type=str, default='data/intermediate/english_raw_11k.jsonl', help='Output file')
    parser.add_argument('--generate-prompts-only', action='store_true', help='Only generate prompts, do not execute')

    args = parser.parse_args()

    # Load existing data
    print(f"Loading existing dataset from {args.input}...")
    existing_samples = load_existing_dataset(args.input)

    # Analyze distribution
    stats = analyze_distribution(existing_samples)
    print(f"\nCurrent dataset: {stats['total_samples']} samples")
    print("\nDistribution:")
    for label, info in stats['distribution'].items():
        print(f"  {label}: {info['count']} ({info['percentage']:.1f}%)")

    # Calculate targets
    targets = calculate_targets(stats['total_samples'], args.target, stats)
    total_needed = sum(targets.values())

    print(f"\nTarget: {args.target} samples")
    print(f"Need to generate: {total_needed} samples")
    print("\nGeneration targets:")
    for label, count in targets.items():
        if count > 0:
            print(f"  {label}: {count} samples")

    # Generate prompts for each class
    print("\n" + "="*80)
    print("PROMPTS FOR CLAUDE CODE")
    print("="*80)

    batch_num = 1
    all_prompts = []

    for label, count in targets.items():
        if count == 0:
            continue

        # Split into batches
        num_batches = (count + args.batch_size - 1) // args.batch_size

        for i in range(num_batches):
            batch_size = min(args.batch_size, count - (i * args.batch_size))
            prompt = generate_prompt_for_batch(label, batch_size, existing_samples, batch_num)

            all_prompts.append({
                'batch_num': batch_num,
                'label': label,
                'count': batch_size,
                'prompt': prompt
            })

            print(f"\n{'='*80}")
            print(f"BATCH {batch_num}: {label} ({batch_size} samples)")
            print(f"{'='*80}\n")
            print(prompt)
            print(f"\n{'='*80}\n")

            batch_num += 1

    # Save prompts to file for reference
    prompts_file = Path(args.output).parent / 'generation_prompts.jsonl'
    prompts_file.parent.mkdir(parents=True, exist_ok=True)

    with open(prompts_file, 'w', encoding='utf-8') as f:
        for p in all_prompts:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    print(f"\n✓ Generated {len(all_prompts)} prompts")
    print(f"✓ Prompts saved to: {prompts_file}")

    if args.generate_prompts_only:
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Copy each prompt above")
        print("2. Run in Claude Code to generate samples")
        print("3. Save responses to data/intermediate/batch_*.json")
        print("4. Run aggregation script to combine results")
        return

    print("\n" + "="*80)
    print("AUTOMATED GENERATION READY")
    print("="*80)
    print("The prompts above can be executed using Claude Code Task agents.")
    print("Each batch will be generated using model='opus' for highest quality.")
    print(f"\nTotal batches: {len(all_prompts)}")
    print(f"Estimated time: ~{len(all_prompts) * 2} minutes (2 min/batch)")

    response = input("\nProceed with automated generation? (y/N): ")
    if response.lower() != 'y':
        print("Aborted. Prompts saved for manual execution.")
        return

    print("\n⚠️  Automated generation requires integration with Claude Code Task API")
    print("This is currently not implemented in this script.")
    print("\nPlease use the prompts above with Claude Code manually, or wait for")
    print("the Claude Code Python SDK integration to enable full automation.")

if __name__ == '__main__':
    main()
