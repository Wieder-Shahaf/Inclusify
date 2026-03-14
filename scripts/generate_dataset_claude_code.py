#!/usr/bin/env python3
"""
Generate dataset samples efficiently using Claude Code.

This creates a practical batch plan (10-15 batches) that can be executed
via Claude Code Task agents with model='opus'.
"""

import csv
import json
from pathlib import Path
from collections import Counter

def main():
    # Load existing dataset
    input_csv = Path('data/Inclusify_Dataset.csv')
    samples = []

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        samples = list(reader)

    # Analyze distribution
    severity_counts = Counter(row['Severity Label'] for row in samples)
    total = len(samples)

    print(f"Current dataset: {total} samples")
    print("\nDistribution:")
    for label, count in severity_counts.items():
        pct = (count / total) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")

    # Create practical batch plan
    # Target: 11,000 samples total (10k + 10% buffer for deduplication)
    # Strategy: 10 batches of ~1,000 samples each (2 batches per severity label)

    TARGET = 11000
    BATCHES_PER_LABEL = 2

    batches = []
    batch_id = 1

    for label, current_count in sorted(severity_counts.items()):
        # Calculate target for this label (maintain proportions)
        label_target = int((current_count / total) * TARGET)
        needed = label_target - current_count
        samples_per_batch = needed // BATCHES_PER_LABEL

        # Create 2 batches for this label
        for i in range(BATCHES_PER_LABEL):
            # Last batch gets remainder
            if i == BATCHES_PER_LABEL - 1:
                batch_size = needed - (samples_per_batch * (BATCHES_PER_LABEL - 1))
            else:
                batch_size = samples_per_batch

            if batch_size > 0:
                batches.append({
                    'batch_id': batch_id,
                    'label': label,
                    'count': batch_size,
                    'domain_focus': 'psychology,sociology,medicine' if i == 0 else 'law,education,anthropology',
                    'output_file': f'data/intermediate/batch_{batch_id:03d}_{label.lower().replace(" ", "_")}.json'
                })
                batch_id += 1

    # Get example samples for each label
    examples_by_label = {}
    for label in severity_counts.keys():
        examples_by_label[label] = [
            {
                'Sentence': s['Sentence'],
                'Severity Label': s['Severity Label'],
                'Rule Category': s.get('Rule Category', 'N/A'),
                'Explanation': s['Explanation']
            }
            for s in samples if s['Severity Label'] == label
        ][:5]  # 5 examples per label

    # Output execution plan
    plan = {
        'metadata': {
            'current_samples': total,
            'target_samples': TARGET,
            'samples_to_generate': sum(b['count'] for b in batches),
            'num_batches': len(batches),
            'estimated_time_minutes': len(batches) * 3  # ~3 min per 1k samples
        },
        'batches': batches,
        'examples': examples_by_label
    }

    # Save plan
    plan_file = Path('data/intermediate/generation_plan.json')
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan, indent=2, fp=f, ensure_ascii=False)

    print(f"\n✓ Plan created: {len(batches)} batches")
    print(f"✓ Total to generate: {sum(b['count'] for b in batches)} samples")
    print(f"✓ Saved to: {plan_file}")

    print("\n" + "="*80)
    print("BATCH PLAN")
    print("="*80)
    for batch in batches:
        print(f"Batch {batch['batch_id']:2d}: {batch['label']:25s} {batch['count']:4d} samples  ({batch['domain_focus']})")

    print("\n" + "="*80)
    print("READY FOR CLAUDE CODE EXECUTION")
    print("="*80)
    print(f"\nPlan saved to: {plan_file}")
    print(f"Estimated time: ~{plan['metadata']['estimated_time_minutes']} minutes")
    print("\nNext: Ask Claude Code to execute this plan using Task agents with model='opus'")

if __name__ == '__main__':
    main()
