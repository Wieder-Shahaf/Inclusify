#!/usr/bin/env python3
"""
Orchestrate dataset generation using Claude Code Task agents.

This script is meant to be run FROM Claude Code, not as a standalone script.
It outputs commands that Claude Code can execute using Task agents with model="opus".
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

def load_existing_dataset(csv_path: str) -> List[Dict[str, str]]:
    """Load existing dataset to understand patterns."""
    samples = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append(row)
    return samples

def analyze_distribution(samples: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze class distribution."""
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
    """Calculate samples needed per class to reach target."""
    current_dist = distribution['distribution']
    targets = {}

    for label, stats in current_dist.items():
        target_count = int((stats['percentage'] / 100) * target)
        current_count = stats['count']
        needed = max(0, target_count - current_count)
        targets[label] = needed

    return targets

def main():
    # Configuration
    INPUT_CSV = 'data/Inclusify_Dataset.csv'
    TARGET_TOTAL = 11000  # Generate extra for deduplication
    BATCH_SIZE = 50  # Smaller batches for reliability

    # Load and analyze
    print("📊 Analyzing existing dataset...")
    samples = load_existing_dataset(INPUT_CSV)
    stats = analyze_distribution(samples)

    print(f"\n✓ Current dataset: {stats['total_samples']} samples")
    print("\nDistribution:")
    for label, info in stats['distribution'].items():
        print(f"  {label}: {info['count']} ({info['percentage']:.1f}%)")

    # Calculate targets
    targets = calculate_targets(stats['total_samples'], TARGET_TOTAL, stats)
    total_needed = sum(targets.values())

    print(f"\n🎯 Target: {TARGET_TOTAL} total samples")
    print(f"📝 Need to generate: {total_needed} samples\n")

    # Create batch plan
    batches = []
    batch_id = 1

    for label, count in sorted(targets.items()):
        if count == 0:
            continue

        num_batches = (count + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(num_batches):
            batch_size = min(BATCH_SIZE, count - (i * BATCH_SIZE))
            batches.append({
                'id': batch_id,
                'label': label,
                'count': batch_size,
                'output_file': f'data/intermediate/batch_{batch_id:03d}.json'
            })
            batch_id += 1

    print(f"📦 Generation plan: {len(batches)} batches")
    print("\nBatch breakdown:")
    for label in sorted(set(b['label'] for b in batches)):
        label_batches = [b for b in batches if b['label'] == label]
        label_count = sum(b['count'] for b in label_batches)
        print(f"  {label}: {len(label_batches)} batches ({label_count} samples)")

    # Output Claude Code execution plan
    print("\n" + "="*80)
    print("CLAUDE CODE EXECUTION PLAN")
    print("="*80)
    print("\nCopy the following JSON array and provide it to Claude Code:")
    print("Claude Code will execute Task agents in parallel to generate all batches.\n")

    execution_plan = {
        'total_batches': len(batches),
        'total_samples': total_needed,
        'batches': batches,
        'source_samples': [
            {
                'Sentence': s['Sentence'],
                'Severity Label': s['Severity Label'],
                'Rule Category': s.get('Rule Category', 'N/A'),
                'Explanation': s['Explanation']
            }
            for s in samples[:20]  # Include 20 examples for reference
        ]
    }

    print(json.dumps(execution_plan, indent=2, ensure_ascii=False))

    print("\n" + "="*80)
    print("\n💡 NEXT STEP:")
    print("="*80)
    print("Provide this plan to Claude Code and ask it to:")
    print("1. Spawn Task agents with model='opus' for each batch")
    print("2. Generate samples according to the batch specifications")
    print("3. Save each batch to its output_file")
    print("4. Aggregate all batches into data/english_10k.csv")

if __name__ == '__main__':
    main()
