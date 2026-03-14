#!/usr/bin/env python3
"""Create comprehensive visualization of vLLM optimization results."""

import json
import matplotlib.pyplot as plt
import numpy as np

# Load data
with open('ml/analysis/vllm_throughput_results.json', 'r') as f:
    vllm_results = json.load(f)

with open('ml/analysis/throughput_optimization_results.json', 'r') as f:
    manual_results = json.load(f)

# Create figure
fig = plt.figure(figsize=(18, 10))
gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

# Main title
fig.suptitle('Qwen2.5-3B Inference Optimization: vLLM vs Manual Batching',
             fontsize=16, fontweight='bold')

# 1. Throughput Comparison (top left)
ax1 = fig.add_subplot(gs[0, 0])

methods = ['Single\n(baseline)', 'Manual\nBatch-4', 'Manual\nBatch-8', 'Manual\nBatch-16',
           'vLLM\nBatch-16', 'vLLM\nBatch-32', 'vLLM\nBatch-64']
throughputs = [
    manual_results['baseline']['throughput_req_per_sec'],
    manual_results['batched']['4']['throughput_req_per_sec'],
    manual_results['batched']['8']['throughput_req_per_sec'],
    manual_results['batched']['16']['throughput_req_per_sec'],
    vllm_results['configurations']['16']['throughput_req_per_sec'],
    vllm_results['configurations']['32']['throughput_req_per_sec'],
    vllm_results['configurations']['64']['throughput_req_per_sec'],
]

colors = ['#2E86AB', '#2E86AB', '#2E86AB', '#2E86AB', '#F18F01', '#F18F01', '#F18F01']
bars = ax1.bar(methods, throughputs, color=colors, alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax1.set_ylabel('Throughput (requests/sec)', fontweight='bold')
ax1.set_title('Throughput Comparison', fontweight='bold', fontsize=12)
ax1.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 2. Latency Comparison (top middle)
ax2 = fig.add_subplot(gs[0, 1])

latencies = [
    manual_results['baseline']['mean_latency_ms'],
    manual_results['batched']['4']['mean_latency_ms'],
    manual_results['batched']['8']['mean_latency_ms'],
    manual_results['batched']['16']['mean_latency_ms'],
    vllm_results['configurations']['16']['mean_latency_ms'],
    vllm_results['configurations']['32']['mean_latency_ms'],
    vllm_results['configurations']['64']['mean_latency_ms'],
]

bars = ax2.bar(methods, latencies, color=colors, alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax2.set_ylabel('Latency (ms/request)', fontweight='bold')
ax2.set_title('Latency Comparison (Lower is Better)', fontweight='bold', fontsize=12)
ax2.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.0f}ms',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 3. Speedup Chart (top right)
ax3 = fig.add_subplot(gs[0, 2])

baseline = manual_results['baseline']['throughput_req_per_sec']
speedups = [t / baseline for t in throughputs]

bars = ax3.bar(methods, speedups, color=colors, alpha=0.8, edgecolor='black')
bars[-1].set_edgecolor('gold')
bars[-1].set_linewidth(3)

ax3.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline')
ax3.set_ylabel('Speedup (x)', fontweight='bold')
ax3.set_title('Speedup vs Baseline', fontweight='bold', fontsize=12)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}x',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 4. vLLM Scaling Curve (bottom left)
ax4 = fig.add_subplot(gs[1, 0])

vllm_configs = sorted(vllm_results['configurations'].keys(), key=int)
vllm_throughputs = [vllm_results['configurations'][str(c)]['throughput_req_per_sec'] for c in vllm_configs]

ax4.plot(vllm_configs, vllm_throughputs, 'o-', linewidth=2.5, markersize=8, color='#F18F01')
ax4.set_xlabel('max_num_seqs (Batch Size)', fontweight='bold')
ax4.set_ylabel('Throughput (requests/sec)', fontweight='bold')
ax4.set_title('vLLM Throughput Scaling', fontweight='bold', fontsize=12)
ax4.grid(True, alpha=0.3)

# Annotate best
best_idx = vllm_throughputs.index(max(vllm_throughputs))
ax4.scatter([vllm_configs[best_idx]], [vllm_throughputs[best_idx]],
           s=200, color='gold', edgecolor='black', linewidth=2, zorder=10)

# 5. Summary Table (bottom middle and right)
ax5 = fig.add_subplot(gs[1, 1:])
ax5.axis('off')

summary_data = [
    ['Single Request (baseline)', f"{manual_results['baseline']['throughput_req_per_sec']:.1f}",
     f"{manual_results['baseline']['mean_latency_ms']:.0f} ms", '1.0x'],
    ['Manual Batch 16', f"{manual_results['batched']['16']['throughput_req_per_sec']:.1f}",
     f"{manual_results['batched']['16']['mean_latency_ms']:.0f} ms",
     f"{manual_results['batched']['16']['speedup_vs_baseline']:.1f}x"],
    ['vLLM Batch 16', f"{vllm_results['configurations']['16']['throughput_req_per_sec']:.1f}",
     f"{vllm_results['configurations']['16']['mean_latency_ms']:.0f} ms",
     f"{vllm_results['configurations']['16']['throughput_req_per_sec'] / baseline:.1f}x"],
    ['vLLM Batch 32', f"{vllm_results['configurations']['32']['throughput_req_per_sec']:.1f}",
     f"{vllm_results['configurations']['32']['mean_latency_ms']:.0f} ms",
     f"{vllm_results['configurations']['32']['throughput_req_per_sec'] / baseline:.1f}x"],
    ['vLLM Batch 64 (BEST)', f"{vllm_results['configurations']['64']['throughput_req_per_sec']:.1f}",
     f"{vllm_results['configurations']['64']['mean_latency_ms']:.0f} ms",
     f"{vllm_results['speedup_vs_single']:.1f}x"],
]

table = ax5.table(cellText=summary_data,
                 colLabels=['Configuration', 'Throughput\n(req/sec)', 'Latency\n(ms/req)', 'Speedup'],
                 cellLoc='center',
                 loc='center',
                 colWidths=[0.35, 0.22, 0.22, 0.21])

table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Style header
for i in range(4):
    table[(0, i)].set_facecolor('#40466e')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Highlight best
for i in range(4):
    table[(5, i)].set_facecolor('#FFD700')
    table[(5, i)].set_text_props(weight='bold')

# Color code methods
for i in range(1, 3):  # Manual methods
    table[(i, 0)].set_facecolor('#D6EAF8')

for i in range(3, 6):  # vLLM methods
    table[(i, 0)].set_facecolor('#FCF3CF')

ax5.set_title('Performance Summary: All Configurations', fontweight='bold', fontsize=13, pad=15)

# Add key findings
fig.text(0.5, 0.02,
         f"🚀 vLLM with batch 64: 34.5 req/sec (7.7x faster) | 29ms latency | 3,110 tokens/sec",
         ha='center', fontsize=12, fontweight='bold', color='#F18F01',
         bbox=dict(boxstyle='round', facecolor='#FFD700', alpha=0.3))

plt.tight_layout()

# Save
output_path = 'ml/analysis/vllm_optimization_complete.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✓ Visualization saved to: {output_path}")

# Print summary
baseline = manual_results['baseline']['throughput_req_per_sec']

print("\n" + "="*70)
print("FINAL OPTIMIZATION RESULTS")
print("="*70)
print(f"\nBaseline (single request): {baseline:.2f} req/sec")
print(f"Manual Batch 16: {manual_results['batched']['16']['throughput_req_per_sec']:.2f} req/sec ({manual_results['batched']['16']['speedup_vs_baseline']:.1f}x)")
print(f"vLLM Batch 64: {vllm_results['best_throughput']:.2f} req/sec ({vllm_results['speedup_vs_single']:.1f}x) ⭐")

print(f"\n🎯 Achieved {vllm_results['speedup_vs_single']:.1f}x throughput improvement!")
print(f"🎯 Latency reduced from 223ms → 29ms (7.7x faster)")
print("="*70 + "\n")
