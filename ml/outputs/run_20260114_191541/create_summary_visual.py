
#!/usr/bin/env python3
"""
Create a summary visual (PNG) from summary.json for an evaluation run.

Output:
  - summary_visual.png in the same directory as summary.json (unless overridden)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary-json",
        default=str(Path(__file__).with_name("summary.json")),
        help="Path to summary.json",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output PNG path (default: alongside summary.json as summary_visual.png)",
    )
    args = parser.parse_args()

    summary_path = Path(args.summary_json).expanduser().resolve()
    if not summary_path.exists():
        raise FileNotFoundError(f"summary.json not found: {summary_path}")

    out_path = Path(args.out).expanduser().resolve() if args.out else summary_path.with_name("summary_visual.png")

    with summary_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Lazy import so script can still run basic validation without plotting deps.
    import matplotlib.pyplot as plt
    import numpy as np

    model_name = data.get("model_name", "model")
    embedding_model = data.get("embedding_model", "embedding_model")
    run_ts = data.get("run_timestamp", "")

    train = data.get("train", {})
    test = data.get("test", {})

    # User requested: no exact-match metrics. Keep similarity metrics only.
    overall_keys = [
        ("semantic_sim_pred_gold_mean", "Sim(pred, gold)"),
        ("semantic_sim_pred_nearest_mean", "Sim(pred, nearest-train)"),
    ]

    train_metrics = train.get("metrics", {}) or {}
    test_metrics = test.get("metrics", {}) or {}

    overall_labels = [lbl for _, lbl in overall_keys]
    overall_train = [_safe_float(train_metrics.get(k)) for k, _ in overall_keys]
    overall_test = [_safe_float(test_metrics.get(k)) for k, _ in overall_keys]

    # Per-severity comparison
    train_by = train.get("by_severity", {}) or {}
    test_by = test.get("by_severity", {}) or {}
    severities = list(train_by.keys() or test_by.keys())
    if not severities:
        severities = []

    # Keep a stable, human-friendly order when possible.
    preferred = ["Correct", "Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"]
    severities = [s for s in preferred if s in severities] + [s for s in severities if s not in preferred]

    train_sim = [_safe_float((train_by.get(s) or {}).get("sim_pred_gold_mean")) for s in severities]
    test_sim = [_safe_float((test_by.get(s) or {}).get("sim_pred_gold_mean")) for s in severities]
    # User requested: no sample-counts shown.

    def annotate_percent(ax, x_positions, values, *, dy=0.02):
        """Annotate bars with percent labels (assumes metric values in [0, 1])."""
        for x0, v in zip(x_positions, values):
            if v is None:
                continue
            ax.text(
                x0,
                v + dy,
                f"{(v * 100):.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="#111111",
            )

    # --- Plot ---
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(14, 8), dpi=160)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.25], hspace=0.35)

    # Vibrant, high-contrast colors (Train vs Test)
    TRAIN_COLOR = "#00A6FB"  # vivid blue
    TEST_COLOR = "#FF006E"   # vivid magenta

    # Title
    title = f"Run {run_ts} — {model_name}\nEmbedding: {embedding_model}"
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.98)

    # Panel A: Overall metrics (train vs test)
    ax0 = fig.add_subplot(gs[0, 0])
    x = np.arange(len(overall_labels))
    width = 0.36
    ax0.bar(x - width / 2, overall_train, width, label="Train", color=TRAIN_COLOR)
    ax0.bar(x + width / 2, overall_test, width, label="Test", color=TEST_COLOR)
    ax0.set_xticks(x)
    ax0.set_xticklabels(overall_labels, rotation=15, ha="right")
    ax0.set_ylim(0.0, 1.0)
    ax0.set_title("Overall Similarity Metrics", fontsize=12, fontweight="bold")
    ax0.legend(frameon=True, loc="lower right")

    # annotate bars with %
    annotate_percent(ax0, x - width / 2, overall_train, dy=0.02)
    annotate_percent(ax0, x + width / 2, overall_test, dy=0.02)

    # Panel B: Per-severity semantic similarity (pred vs gold mean)
    ax1 = fig.add_subplot(gs[1, 0])
    xs = np.arange(len(severities))
    ax1.bar(xs - width / 2, train_sim, width, label="Train", color=TRAIN_COLOR)
    ax1.bar(xs + width / 2, test_sim, width, label="Test", color=TEST_COLOR)
    ax1.set_xticks(xs)
    ax1.set_xticklabels(severities, rotation=20, ha="right")
    ax1.set_ylim(0.0, 1.0)
    ax1.set_title("Per-Severity: Sim(pred, gold)", fontsize=12, fontweight="bold")
    ax1.legend(frameon=True, loc="lower right")

    # annotate bars with %
    annotate_percent(ax1, xs - width / 2, train_sim, dy=0.02)
    annotate_percent(ax1, xs + width / 2, test_sim, dy=0.02)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

