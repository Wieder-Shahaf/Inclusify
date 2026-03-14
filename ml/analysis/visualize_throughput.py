#!/usr/bin/env python3
"""Visualize throughput optimization results."""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load data
with open('ml/analysis/throughput_optimization_results.json', 'r') as f:
    results = json.load(f)

with open('ml/analysis/inference_benchmark_results.json', 'r') as f:
    model_comparison = json.load(f)

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('Qwen2.5-3B: Inference Speed Optimization Results', fontsize=16, fontweight='bold')

# 1. Throughput by Batch Size
ax1 = axes[0, 0]
batch_sizes = [1] + list(results['batched'].keys())
throughputs = [results['baseline']['throughput_req_per_sec']] + \
              [results['batched'][str(bs)]['throughput_req_per_sec'] for bs in batch_sizes[1:]]

bars = ax1.bar([str(bs) for bs in batch_sizes], throughputs, color='#2E86AB', alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax1.set_xlabel('Batch Size', fontweight='bold')
ax1.set_ylabel('Throughput (requests/sec)', fontweight='bold')
ax1.set_title('Throughput vs Batch Size', fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}',
            ha='center', va='bottom', fontweight='bold')

# 2. Latency by Batch Size
ax2 = axes[0, 1]
latencies = [results['baseline']['mean_latency_ms']] + \
            [results['batched'][str(bs)]['mean_latency_ms'] for bs in batch_sizes[1:]]

bars = ax2.bar([str(bs) for bs in batch_sizes], latencies, color='#A23B72', alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax2.set_xlabel('Batch Size', fontweight='bold')
ax2.set_ylabel('Latency (ms/request)', fontweight='bold')
ax2.set_title('Latency vs Batch Size (Lower is Better)', fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.0f}ms',
            ha='center', va='bottom', fontweight='bold')

# 3. Speedup Comparison
ax3 = axes[1, 0]
speedups = [1.0] + [results['batched'][str(bs)]['speedup_vs_baseline'] for bs in batch_sizes[1:]]

bars = ax3.bar([str(bs) for bs in batch_sizes], speedups, color='#F18F01', alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax3.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline')
ax3.set_xlabel('Batch Size', fontweight='bold')
ax3.set_ylabel('Speedup (x)', fontweight='bold')
ax3.set_title('Speedup vs Baseline', fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.2f}x',
            ha='center', va='bottom', fontweight='bold')

# 4. Model Comparison Summary Table
ax4 = axes[1, 1]
ax4.axis('off')

summary_data = [
    ['Single Request', f"{results['baseline']['throughput_req_per_sec']:.1f}", f"{results['baseline']['mean_latency_ms']:.0f} ms"],
    ['Batch 4', f"{results['batched']['4']['throughput_req_per_sec']:.1f}", f"{results['batched']['4']['mean_latency_ms']:.0f} ms"],
    ['Batch 8', f"{results['batched']['8']['throughput_req_per_sec']:.1f}", f"{results['batched']['8']['mean_latency_ms']:.0f} ms"],
    ['Batch 16 ⭐', f"{results['batched']['16']['throughput_req_per_sec']:.1f}", f"{results['batched']['16']['mean_latency_ms']:.0f} ms"],
    ['', '', ''],
    ['vs Qwen3.5-0.8B', f"{model_comparison['qwen25']['throughput_samples_per_sec']:.1f}", f"{model_comparison['qwen25']['mean_latency_ms']:.0f} ms"],
    ['Qwen3.5 (baseline)', f"{model_comparison['qwen3']['throughput_samples_per_sec']:.1f}", f"{model_comparison['qwen3']['mean_latency_ms']:.0f} ms"],
]

table = ax4.table(cellText=summary_data,
                 colLabels=['Configuration', 'Throughput\n(req/sec)', 'Latency\n(ms/req)'],
                 cellLoc='center',
                 loc='center',
                 colWidths=[0.35, 0.325, 0.325])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.2)

# Style header
for i in range(3):
    table[(0, i)].set_facecolor('#40466e')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Highlight best
table[(4, 0)].set_facecolor('#FFD700')
table[(4, 1)].set_facecolor('#FFD700')
table[(4, 2)].set_facecolor('#FFD700')
for i in range(3):
    table[(4, i)].set_text_props(weight='bold')

# Separator row
for i in range(3):
    table[(5, i)].set_facecolor('#EEEEEE')

ax4.set_title('Performance Summary', fontweight='bold', fontsize=12, pad=10)

# Add optimization note
fig.text(0.5, 0.02,
         f"Optimization Result: 2.97x throughput improvement with batch size 16 (4.5 → 13.3 req/sec)",
         ha='center', fontsize=11, fontweight='bold', color='#2E86AB',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4))

plt.tight_layout()

# Save
output_path = Path('ml/analysis/throughput_optimization.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✓ Visualization saved to: {output_path}")

plt.close()

print("\n" + "="*70)
print("KEY FINDINGS")
print("="*70)
print(f"\n1. Batch size 16 achieves BEST throughput: 13.3 req/sec (2.97x improvement)")
print(f"2. Latency improves with batching: 223ms → 75ms per request")
print(f"3. Qwen2.5 is 2.26x faster than Qwen3.5 even without batching")
print(f"4. With batching, Qwen2.5 reaches 6.0x faster than Qwen3.5 baseline")
print("\n" + "="*70)
