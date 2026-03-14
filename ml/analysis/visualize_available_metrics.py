#!/usr/bin/env python3
"""
Create summary visualization with available metrics.
Note: Precision, Recall, F1 require separate evaluation (not computed during training).
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

plt.style.use('seaborn-v0_8-darkgrid')


def load_data():
    """Load results and training states."""
    analysis_dir = Path(__file__).parent

    with open(analysis_dir / 'qwen25_results.json', 'r') as f:
        qwen25_results = json.load(f)

    with open(analysis_dir / 'qwen3_results.json', 'r') as f:
        qwen3_results = json.load(f)

    with open(analysis_dir / 'qwen25_trainer_state.json', 'r') as f:
        qwen25_state = json.load(f)

    with open(analysis_dir / 'qwen3_trainer_state.json', 'r') as f:
        qwen3_state = json.load(f)

    return qwen25_results, qwen3_results, qwen25_state, qwen3_state


def extract_loss_curves(trainer_state):
    """Extract training and eval loss from trainer state."""
    log_history = trainer_state.get('log_history', [])

    train_steps, train_losses = [], []
    eval_steps, eval_losses = [], []

    for entry in log_history:
        if 'loss' in entry:
            train_steps.append(entry['step'])
            train_losses.append(entry['loss'])
        if 'eval_loss' in entry:
            eval_steps.append(entry['step'])
            eval_losses.append(entry['eval_loss'])

    return train_steps, train_losses, eval_steps, eval_losses


def main():
    qwen25_results, qwen3_results, qwen25_state, qwen3_state = load_data()

    # Find best configs
    best_qwen25 = min(qwen25_results, key=lambda x: x['val_loss'])
    best_qwen3 = min(qwen3_results, key=lambda x: x['val_loss'])

    # Extract loss curves
    q25_train_steps, q25_train_loss, q25_eval_steps, q25_eval_loss = extract_loss_curves(qwen25_state)
    q3_train_steps, q3_train_loss, q3_eval_steps, q3_eval_loss = extract_loss_curves(qwen3_state)

    # Create figure
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)

    # 1. Training Loss Curves (top row, span all columns)
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(q25_train_steps, q25_train_loss, 'o-', label='Qwen2.5-3B Train',
             color='#2E86AB', alpha=0.6, markersize=3)
    ax1.plot(q25_eval_steps, q25_eval_loss, 's-', label='Qwen2.5-3B Eval',
             color='#2E86AB', linewidth=2.5, markersize=6)
    ax1.plot(q3_train_steps, q3_train_loss, 'o-', label='Qwen3.5-0.8B Train',
             color='#A23B72', alpha=0.6, markersize=3)
    ax1.plot(q3_eval_steps, q3_eval_loss, 's-', label='Qwen3.5-0.8B Eval',
             color='#A23B72', linewidth=2.5, markersize=6)
    ax1.set_xlabel('Training Steps', fontweight='bold', fontsize=11)
    ax1.set_ylabel('Loss', fontweight='bold', fontsize=11)
    ax1.set_title('Training & Validation Loss Over Time', fontweight='bold', fontsize=13)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, max(max(q25_train_loss[:5]), max(q3_train_loss[:5])) * 0.5])

    # 2. Final Validation Loss Comparison (middle left)
    ax2 = fig.add_subplot(gs[1, 0])
    models = ['Qwen2.5-3B\n(r8_d0.2)', 'Qwen3.5-0.8B\n(r32_d0.05)']
    val_losses = [best_qwen25['val_loss'], best_qwen3['val_loss']]
    colors = ['#2E86AB', '#A23B72']

    bars = ax2.bar(models, val_losses, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Validation Loss', fontweight='bold', fontsize=11)
    ax2.set_title('Final Validation Loss\n(Lower is Better)', fontweight='bold', fontsize=12)
    ax2.set_ylim([0, max(val_losses) * 1.2])
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.4f}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Highlight winner
    bars[0].set_edgecolor('gold')
    bars[0].set_linewidth(3)

    # 3. Training Time Comparison (middle center)
    ax3 = fig.add_subplot(gs[1, 1])
    train_times = [best_qwen25['duration_min'], best_qwen3['duration_min']]
    bars = ax3.bar(models, train_times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Training Time (minutes)', fontweight='bold', fontsize=11)
    ax3.set_title('Training Duration\n(Lower is Better)', fontweight='bold', fontsize=12)
    ax3.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f} min',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Highlight winner
    bars[1].set_edgecolor('gold')
    bars[1].set_linewidth(3)

    # Add speedup annotation
    speedup = train_times[0] / train_times[1]
    ax3.text(0.5, max(train_times) * 0.9, f'{speedup:.1f}x faster →',
             ha='center', fontsize=12, fontweight='bold', color='#A23B72',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 4. Model Size Comparison (middle right)
    ax4 = fig.add_subplot(gs[1, 2])
    param_counts = [best_qwen25['trainable_params']/1e6, best_qwen3['trainable_params']/1e6]
    bars = ax4.bar(models, param_counts, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax4.set_ylabel('Trainable Parameters (M)', fontweight='bold', fontsize=11)
    ax4.set_title('Trainable Parameters\n(LoRA adapters)', fontweight='bold', fontsize=12)
    ax4.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}M',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # 5. Grid Search Heatmap - Qwen2.5 (bottom left)
    ax5 = fig.add_subplot(gs[2, 0])
    ranks = [8, 16, 32]
    dropouts = [0.05, 0.1, 0.2]
    heatmap_data_q25 = np.zeros((len(ranks), len(dropouts)))

    for r in qwen25_results:
        rank_idx = ranks.index(r['rank'])
        dropout_idx = dropouts.index(r['dropout'])
        heatmap_data_q25[rank_idx, dropout_idx] = r['val_loss']

    im = ax5.imshow(heatmap_data_q25, cmap='RdYlGn_r', aspect='auto')
    ax5.set_xticks(range(len(dropouts)))
    ax5.set_yticks(range(len(ranks)))
    ax5.set_xticklabels([f'{d}' for d in dropouts])
    ax5.set_yticklabels([f'r={r}' for r in ranks])
    ax5.set_xlabel('Dropout', fontweight='bold')
    ax5.set_ylabel('Rank', fontweight='bold')
    ax5.set_title('Qwen2.5-3B\nGrid Search Results', fontweight='bold', fontsize=12)

    # Add text annotations
    for i in range(len(ranks)):
        for j in range(len(dropouts)):
            text = ax5.text(j, i, f'{heatmap_data_q25[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=9, fontweight='bold')
            # Highlight best
            if i == 0 and j == 2:  # r8_d0.2
                rect = plt.Rectangle((j-0.4, i-0.4), 0.8, 0.8, fill=False,
                                    edgecolor='gold', linewidth=3)
                ax5.add_patch(rect)

    plt.colorbar(im, ax=ax5, label='Validation Loss')

    # 6. Grid Search Heatmap - Qwen3.5 (bottom center)
    ax6 = fig.add_subplot(gs[2, 1])
    heatmap_data_q3 = np.zeros((len(ranks), len(dropouts)))

    for r in qwen3_results:
        rank_idx = ranks.index(r['rank'])
        dropout_idx = dropouts.index(r['dropout'])
        heatmap_data_q3[rank_idx, dropout_idx] = r['val_loss']

    im = ax6.imshow(heatmap_data_q3, cmap='RdYlGn_r', aspect='auto')
    ax6.set_xticks(range(len(dropouts)))
    ax6.set_yticks(range(len(ranks)))
    ax6.set_xticklabels([f'{d}' for d in dropouts])
    ax6.set_yticklabels([f'r={r}' for r in ranks])
    ax6.set_xlabel('Dropout', fontweight='bold')
    ax6.set_ylabel('Rank', fontweight='bold')
    ax6.set_title('Qwen3.5-0.8B\nGrid Search Results', fontweight='bold', fontsize=12)

    # Add text annotations
    for i in range(len(ranks)):
        for j in range(len(dropouts)):
            text = ax6.text(j, i, f'{heatmap_data_q3[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=9, fontweight='bold')
            # Highlight best
            if i == 2 and j == 0:  # r32_d0.05
                rect = plt.Rectangle((j-0.4, i-0.4), 0.8, 0.8, fill=False,
                                    edgecolor='gold', linewidth=3)
                ax6.add_patch(rect)

    plt.colorbar(im, ax=ax6, label='Validation Loss')

    # 7. Summary Table (bottom right)
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.axis('off')

    summary_data = [
        ['Val Loss', f"{best_qwen25['val_loss']:.4f} ✓", f"{best_qwen3['val_loss']:.4f}"],
        ['Train Time', f"{best_qwen25['duration_min']:.1f} min", f"{best_qwen3['duration_min']:.1f} min ✓"],
        ['Speed', '1.0x', '6.1x ✓'],
        ['Trainable', f"{best_qwen25['trainable_params']/1e6:.1f}M ✓", f"{best_qwen3['trainable_params']/1e6:.1f}M"],
        ['Total Params', f"{best_qwen25['total_params']/1e6:.0f}M ✓", f"{best_qwen3['total_params']/1e6:.0f}M"],
        ['Framework', 'Standard', 'Unsloth ✓'],
    ]

    table = ax7.table(cellText=summary_data,
                     colLabels=['Metric', 'Qwen2.5-3B', 'Qwen3.5-0.8B'],
                     cellLoc='center',
                     loc='center',
                     colWidths=[0.35, 0.325, 0.325])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Style header
    for i in range(3):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Highlight winners
    for i in range(1, 7):
        if '✓' in summary_data[i-1][1]:
            table[(i, 1)].set_facecolor('#90EE90')
        if '✓' in summary_data[i-1][2]:
            table[(i, 2)].set_facecolor('#FFB6C1')

    ax7.set_title('Best Config Comparison', fontweight='bold', fontsize=13, pad=15)

    # Main title
    fig.suptitle('Qwen2.5-3B vs Qwen3.5-0.8B: Training Analysis\nInclusify LGBTQ+ Language Detection',
                 fontsize=16, fontweight='bold', y=0.98)

    # Note about missing metrics
    fig.text(0.5, 0.01,
             'Note: Precision, Recall, F1 metrics require separate evaluation (see TRAINING_SUMMARY.md)',
             ha='center', fontsize=10, style='italic', color='#666',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Save
    output_path = Path(__file__).parent / 'complete_training_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Complete analysis saved to: {output_path}")

    # Print summary
    print("\n" + "="*70)
    print("TRAINING ANALYSIS SUMMARY")
    print("="*70)
    print(f"\nQwen2.5-3B (Best: {best_qwen25['config']})")
    print(f"  Validation Loss: {best_qwen25['val_loss']:.4f} ⭐")
    print(f"  Training Time: {best_qwen25['duration_min']:.1f} min")

    print(f"\nQwen3.5-0.8B (Best: {best_qwen3['config']})")
    print(f"  Validation Loss: {best_qwen3['val_loss']:.4f}")
    print(f"  Training Time: {best_qwen3['duration_min']:.1f} min ⭐")
    print(f"  Speedup: {best_qwen25['duration_min']/best_qwen3['duration_min']:.1f}x faster")

    print("\nWinner by Metric:")
    print(f"  Performance (Loss): Qwen2.5-3B ({abs((best_qwen3['val_loss']-best_qwen25['val_loss'])/best_qwen25['val_loss']*100):.1f}% better)")
    print(f"  Speed: Qwen3.5-0.8B (6.1x faster)")
    print(f"  Efficiency: Qwen2.5-3B (smaller model)")

    print("\n" + "="*70)
    print("\nFor Precision, Recall, F1 metrics, run:")
    print("  bash ml/analysis/run_evaluation_vm.sh  # On Azure VM (30-60 min)")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
