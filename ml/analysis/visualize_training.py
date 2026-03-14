#!/usr/bin/env python3
"""
Visualize training results and compare Qwen2.5-3B vs Qwen3.5-0.8B models.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10


def load_trainer_state(filepath):
    """Load trainer state JSON and extract loss history."""
    with open(filepath, 'r') as f:
        state = json.load(f)
    return state


def load_results(filepath):
    """Load grid search results JSON."""
    with open(filepath, 'r') as f:
        results = json.load(f)
    return results


def plot_loss_progression(ax, trainer_state, model_name, color):
    """Plot training and validation loss over steps."""
    log_history = trainer_state.get('log_history', [])

    train_steps = []
    train_losses = []
    eval_steps = []
    eval_losses = []

    for entry in log_history:
        if 'loss' in entry:
            train_steps.append(entry['step'])
            train_losses.append(entry['loss'])
        if 'eval_loss' in entry:
            eval_steps.append(entry['step'])
            eval_losses.append(entry['eval_loss'])

    # Plot training loss
    ax.plot(train_steps, train_losses,
            label=f'{model_name} - Training Loss',
            color=color, linewidth=2, alpha=0.7)

    # Plot validation loss
    ax.plot(eval_steps, eval_losses,
            label=f'{model_name} - Validation Loss',
            color=color, linewidth=2.5, linestyle='--', marker='o', markersize=5)

    return train_steps, train_losses, eval_steps, eval_losses


def plot_grid_search_comparison(ax, qwen25_results, qwen3_results):
    """Plot validation loss comparison across all configs."""

    # Qwen2.5 results
    qwen25_configs = [r['config'] for r in qwen25_results]
    qwen25_losses = [r['val_loss'] for r in qwen25_results]

    # Qwen3 results
    qwen3_configs = [r['config'] for r in qwen3_results]
    qwen3_losses = [r['val_loss'] for r in qwen3_results]

    x_qwen25 = np.arange(len(qwen25_configs))
    x_qwen3 = np.arange(len(qwen3_configs))

    width = 0.35

    bars1 = ax.bar(x_qwen25 - width/2, qwen25_losses, width,
                   label='Qwen2.5-3B', color='#2E86AB', alpha=0.8)
    bars2 = ax.bar(x_qwen3 + width/2, qwen3_losses, width,
                   label='Qwen3.5-0.8B', color='#A23B72', alpha=0.8)

    # Highlight best configs
    best_qwen25_idx = qwen25_losses.index(min(qwen25_losses))
    best_qwen3_idx = qwen3_losses.index(min(qwen3_losses))

    bars1[best_qwen25_idx].set_edgecolor('gold')
    bars1[best_qwen25_idx].set_linewidth(3)
    bars2[best_qwen3_idx].set_edgecolor('gold')
    bars2[best_qwen3_idx].set_linewidth(3)

    ax.set_xlabel('Configuration', fontweight='bold')
    ax.set_ylabel('Validation Loss', fontweight='bold')
    ax.set_title('Grid Search: Validation Loss Comparison', fontweight='bold', fontsize=12)
    ax.set_xticks(x_qwen25)
    ax.set_xticklabels([c.replace('qwen_', '').replace('qwen3_', '') for c in qwen25_configs],
                       rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3)

    return qwen25_configs[best_qwen25_idx], qwen3_configs[best_qwen3_idx]


def plot_model_comparison_table(ax, qwen25_results, qwen3_results, best_qwen25, best_qwen3):
    """Create a comparison table for best configs."""

    # Find best config details
    qwen25_best = next(r for r in qwen25_results if r['config'] == best_qwen25)
    qwen3_best = next(r for r in qwen3_results if r['config'] == best_qwen3)

    # Prepare table data
    metrics = [
        'Model',
        'Config',
        'Val Loss',
        'Rank',
        'Dropout',
        'Trainable Params',
        'Total Params',
        'Training Time (min)',
        'Speed vs Qwen2.5'
    ]

    qwen25_data = [
        'Qwen2.5-3B',
        qwen25_best['config'],
        f"{qwen25_best['val_loss']:.4f}",
        str(qwen25_best['rank']),
        str(qwen25_best['dropout']),
        f"{qwen25_best['trainable_params']:,}",
        f"{qwen25_best['total_params']:,}",
        f"{qwen25_best['duration_min']:.2f}",
        '1.0x (baseline)'
    ]

    speedup = qwen25_best['duration_min'] / qwen3_best['duration_min']
    qwen3_data = [
        'Qwen3.5-0.8B',
        qwen3_best['config'],
        f"{qwen3_best['val_loss']:.4f}",
        str(qwen3_best['rank']),
        str(qwen3_best['dropout']),
        f"{qwen3_best['trainable_params']:,}",
        f"{qwen3_best['total_params']:,}",
        f"{qwen3_best['duration_min']:.2f}",
        f'{speedup:.1f}x faster'
    ]

    ax.axis('tight')
    ax.axis('off')

    table = ax.table(cellText=[qwen25_data, qwen3_data],
                     rowLabels=['Qwen2.5-3B', 'Qwen3.5-0.8B'],
                     colLabels=metrics,
                     cellLoc='center',
                     loc='center',
                     colWidths=[0.12] * len(metrics))

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Color header
    for i in range(len(metrics)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Color row labels
    table[(1, -1)].set_facecolor('#2E86AB')
    table[(1, -1)].set_text_props(weight='bold', color='white')
    table[(2, -1)].set_facecolor('#A23B72')
    table[(2, -1)].set_text_props(weight='bold', color='white')

    # Highlight best loss
    best_loss_idx = 2  # Val Loss column
    if qwen25_best['val_loss'] < qwen3_best['val_loss']:
        table[(1, best_loss_idx)].set_facecolor('#90EE90')  # Light green
        table[(1, best_loss_idx)].set_text_props(weight='bold')
    else:
        table[(2, best_loss_idx)].set_facecolor('#90EE90')
        table[(2, best_loss_idx)].set_text_props(weight='bold')

    ax.set_title('Best Configuration Comparison', fontweight='bold', fontsize=12, pad=20)


def main():
    analysis_dir = Path(__file__).parent

    # Load data
    print("Loading training data...")
    qwen25_state = load_trainer_state(analysis_dir / 'qwen25_trainer_state.json')
    qwen3_state = load_trainer_state(analysis_dir / 'qwen3_trainer_state.json')
    qwen25_results = load_results(analysis_dir / 'qwen25_results.json')
    qwen3_results = load_results(analysis_dir / 'qwen3_results.json')

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. Training Loss Progression (top, spanning both columns)
    ax1 = fig.add_subplot(gs[0, :])
    print("Plotting loss progression...")
    qwen25_train_steps, qwen25_train_losses, qwen25_eval_steps, qwen25_eval_losses = \
        plot_loss_progression(ax1, qwen25_state, 'Qwen2.5-3B', '#2E86AB')
    qwen3_train_steps, qwen3_train_losses, qwen3_eval_steps, qwen3_eval_losses = \
        plot_loss_progression(ax1, qwen3_state, 'Qwen3.5-0.8B', '#A23B72')

    ax1.set_xlabel('Training Steps', fontweight='bold')
    ax1.set_ylabel('Loss', fontweight='bold')
    ax1.set_title('Training Loss Progression: Qwen2.5-3B vs Qwen3.5-0.8B (Best Configs)',
                  fontweight='bold', fontsize=14)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # 2. Grid Search Comparison (middle left)
    ax2 = fig.add_subplot(gs[1, :])
    print("Plotting grid search comparison...")
    best_qwen25, best_qwen3 = plot_grid_search_comparison(ax2, qwen25_results, qwen3_results)

    # 3. Best Config Comparison Table (bottom)
    ax3 = fig.add_subplot(gs[2, :])
    print("Creating comparison table...")
    plot_model_comparison_table(ax3, qwen25_results, qwen3_results, best_qwen25, best_qwen3)

    # Main title
    fig.suptitle('Inclusify Model Training Analysis: Qwen2.5-3B vs Qwen3.5-0.8B',
                 fontsize=16, fontweight='bold', y=0.98)

    # Save figure
    output_path = analysis_dir / 'training_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Plot saved to: {output_path}")

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    qwen25_best_data = next(r for r in qwen25_results if r['config'] == best_qwen25)
    qwen3_best_data = next(r for r in qwen3_results if r['config'] == best_qwen3)

    print(f"\nQwen2.5-3B Best Config: {best_qwen25}")
    print(f"  Validation Loss: {qwen25_best_data['val_loss']:.4f}")
    print(f"  Training Time: {qwen25_best_data['duration_min']:.2f} min")
    print(f"  Trainable Params: {qwen25_best_data['trainable_params']:,}")

    print(f"\nQwen3.5-0.8B Best Config: {best_qwen3}")
    print(f"  Validation Loss: {qwen3_best_data['val_loss']:.4f}")
    print(f"  Training Time: {qwen3_best_data['duration_min']:.2f} min")
    print(f"  Trainable Params: {qwen3_best_data['trainable_params']:,}")

    speedup = qwen25_best_data['duration_min'] / qwen3_best_data['duration_min']
    loss_diff = ((qwen3_best_data['val_loss'] - qwen25_best_data['val_loss']) /
                 qwen25_best_data['val_loss'] * 100)

    print(f"\nComparison:")
    print(f"  Qwen3.5 is {speedup:.1f}x faster to train")
    print(f"  Qwen2.5 has {abs(loss_diff):.2f}% lower validation loss")
    print(f"  {'Qwen2.5' if qwen25_best_data['val_loss'] < qwen3_best_data['val_loss'] else 'Qwen3.5'} performs better")

    print("\n" + "="*70)

    plt.show()


if __name__ == '__main__':
    main()
