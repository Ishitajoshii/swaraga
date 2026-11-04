"""Rerun the T2 GRU experiment and export publication-quality learning curves.

Usage: python scripts/plot_gru_training.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd
import torch

from run_experiments import load_splits
from swaraga import config
from swaraga.grammar import RagaGrammarLibrary
from swaraga.models.neural import TorchModel
from swaraga.train import TrainConfig, train
from swaraga.windows import build_windows, split_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "gru_training")
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    parts = split_windows(build_windows(frame, rung="T2", library=RagaGrammarLibrary()),
                          load_splits())
    assert parts["train"] and parts["val"], "Both data splits must be nonempty"
    assert all(len(w.target_degrees) == 8 for split in ("train", "val") for w in parts[split])
    settings = TrainConfig(seed=args.seed, verbose=True)
    model = TorchModel(architecture="gru", seed=args.seed)
    print(f"T2: {len(parts['train'])} training and {len(parts['val'])} validation windows", flush=True)
    result = train(model, parts["train"], parts["val"], settings)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    result.save_history(
        output / "gru_epoch_history.json", settings, rung="T2",
        train_windows=len(parts["train"]), val_windows=len(parts["val"]),
        context_positions=16, target_positions=8,
        train_record_ids=sorted({w.record_id for w in parts["train"]}),
        val_record_ids=sorted({w.record_id for w in parts["val"]}),
        torch_version=torch.__version__, torch_threads=args.threads,
    )
    history = pd.DataFrame(result.history)
    epochs = history["epoch"] + 1
    best = result.best_epoch + 1
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.titlesize": 18, "axes.labelsize": 13,
                         "savefig.facecolor": "white"})
    for metric, title, ylabel in (
        ("loss", "GRU training and validation loss", "Cross-entropy loss"),
        ("accuracy", "GRU training and validation accuracy", "Next-token accuracy (%)"),
    ):
        fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
        ax.plot(epochs, history[f"train_{metric}"], color="#1261A0", linewidth=2.5,
                label=f"Training {metric}")
        ax.plot(epochs, history[f"val_{metric}"], color="#D66B18", linewidth=2.5,
                linestyle="--", label=f"Validation {metric}")
        ax.axvline(best, color="#757575", linewidth=1.2, linestyle=":",
                   label=f"Best validation loss (epoch {best})")
        ax.set(title=title, xlabel="Epoch", ylabel=ylabel, xlim=(1, len(history)))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        if metric == "accuracy":
            ax.set_ylim(0, 100)
        else:
            ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#DDE2E8", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=10, loc="best")
        fig.savefig(output / f"gru_{metric}.png", dpi=300)
        plt.close(fig)
    captions = (
        f"Figure 1. GRU training and validation cross-entropy loss versus epoch for the T2 "
        f"next-token prediction task (16 context notes, 8 target notes; seed {args.seed}). "
        f"Loss is computed only over the unmasked target positions. The lowest validation "
        f"loss occurs at epoch {best}; early stopping ends training at epoch {result.epochs_run}.\n\n"
        f"Figure 2. GRU training and validation next-token accuracy versus epoch for the same run. "
        f"Accuracy is 100 times the number of correct argmax predictions divided by the total "
        f"number of unmasked target tokens (8 per window), using teacher forcing. Context and "
        f"padding positions are excluded.\n\n"
        f"Run details: {len(parts['train'])} training windows; {len(parts['val'])} validation windows. "
        f"Training metrics are recorded during optimization with dropout enabled; validation "
        f"metrics are recorded after each epoch with dropout disabled. Loss retains the existing "
        f"experiment's mean-of-batch-means aggregation; accuracy is aggregated over all target tokens. "
        f"The dotted line marks the epoch selected by validation loss, not validation accuracy. "
        f"JSON/CSV epoch indices start at 0; figure epoch numbers start at 1.\n"
    )
    (output / "captions.txt").write_text(captions, encoding="utf-8")
    print(captions)
    print(f"Saved figures and history to {output}")


if __name__ == "__main__":
    main()
