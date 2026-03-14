#!/usr/bin/env python3
"""
Generate a starter dataset (2K samples) using Claude Code.
This is a practical first step before committing to full 11K generation.
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

    # Create STARTER plan: 2,000 total samples (more practical for first run)
    # 10 batches of 200 samples each (2 batches per label)

    TARGET = 2100  # 2000 + buffer
    BATCHES_PER_LABEL = 2
    SAMPLES_PER_BATCH = 200

    batches = []
    batch_id = 1

    for label in sorted(severity_counts.keys()):
        for i in range(BATCHES_PER_LABEL):
            batches.append({
                'batch_id': batch_id,
                'label': label,
                'count': SAMPLES_PER_BATCH,
                'domain_focus': 'psychology,sociology,medicine' if i == 0 else 'law,education,anthropology',
                'output_file': f'data/intermediate/batch_{batch_id:02d}_{label.lower().replace(" ", "_")}.json'
            })
            batch_id += 1

    # Get example samples for each label
    examples_by_label = {}
    for label in severity_counts.keys():
        examples_by_label[label] = [
            s for s in samples if s['Severity Label'] == label
        ][:5]

    # Output execution plan
    plan = {
        'metadata': {
            'current_samples': total,
            'target_samples': TARGET,
            'samples_to_generate': sum(b['count'] for b in batches),
            'num_batches': len(batches),
            'estimated_time_minutes': len(batches) * 5,  # ~5 min per batch with Opus
            'estimated_cost_usd': '10-20'
        },
        'batches': batches,
        'examples': examples_by_label
    }

    # Save plan
    plan_file = Path('data/intermediate/starter_plan.json')
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan, indent=2, fp=f, ensure_ascii=False)

    print(f"✓ STARTER PLAN: {len(batches)} batches, {sum(b['count'] for b in batches)} samples")
    print(f"✓ Estimated time: ~{plan['metadata']['estimated_time_minutes']} minutes")
    print(f"✓ Estimated cost: ${plan['metadata']['estimated_cost_usd']}")
    print(f"✓ Plan saved to: {plan_file}\n")

    print("="*80)
    print("BATCH PLAN")
    print("="*80)
    for batch in batches:
        print(f"Batch {batch['batch_id']:2d}: {batch['label']:25s} {batch['count']:3d} samples")

    return plan

if __name__ == '__main__':
    plan = main()
