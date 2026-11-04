"""Training loop for the M1 neural models.

Deliberately plain: teacher forcing, cross-entropy, Adam, early stopping. The
interesting engineering here is not the optimiser, it is making overfitting
*visible* - at 466 training windows these models will memorise, and the loss
history is kept so that can be shown rather than hidden.

One caution worth repeating wherever these numbers are quoted: stride-1 windows
from 16 compositions overlap almost entirely, so 466 windows carry far less
information than 466 independent examples (~907 swaras in total).
"""

from __future__ import annotations

import random
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .models.neural import TorchModel, _require_torch
from .vocab import PAD_INDEX, ConditionVocab, DegreeVocab
from .windows import Window


@dataclass
class TrainConfig:
    """Hyperparameters. Defaults are sized for a few hundred windows."""

    epochs: int = 200
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 10               # early-stopping patience, in epochs
    seed: int = 42
    verbose: bool = False


@dataclass
class TrainResult:
    """What one training run produced."""

    model: TorchModel
    best_val_loss: float
    best_epoch: int
    epochs_run: int
    history: List[Dict[str, float]] = field(default_factory=list)

    def save_history(self, path: Path, config: TrainConfig, **metadata) -> None:
        """Persist metrics and run settings; epoch indices are zero-based."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "architecture": self.model.architecture,
            "config": config.__dict__,
            "epoch_index_base": 0,
            "accuracy_definition": "100 * correct argmax predictions / unmasked target tokens",
            "train_metrics": "Online training pass, with dropout enabled",
            "validation_metrics": "End-of-epoch evaluation, with dropout disabled",
            "loss_aggregation": "Mean of batch mean cross-entropy losses (existing experiment convention)",
            "best_epoch": self.best_epoch,
            "best_val_loss": self.best_val_loss,
            "epochs_run": self.epochs_run,
            **metadata,
            "history": self.history,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if self.history:
            with path.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(self.history[0]))
                writer.writeheader()
                writer.writerows(self.history)

    @property
    def overfit_gap(self) -> float:
        """Val minus train loss at the best epoch - the overfitting evidence."""
        if not self.history or self.best_epoch >= len(self.history):
            return 0.0
        entry = self.history[self.best_epoch]
        return entry["val_loss"] - entry["train_loss"]


def set_seed(seed: int) -> None:
    """Seed every source of randomness the run touches."""
    torch, _ = _require_torch()
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def encode_batch(windows: Sequence[Window], degree_vocab: DegreeVocab,
                 condition_vocab: ConditionVocab, use_composer: bool = False):
    """Windows -> padded tensors.

    Each example is the full sequence (context + target); the loss is masked to
    the target positions only, so the model is scored on continuation rather
    than on reconstructing the prompt it was given.
    """
    torch, _ = _require_torch()

    sequences, targets, ragas, talas, composers = [], [], [], [], []
    for window in windows:
        full = list(window.context_degrees) + list(window.target_degrees)
        indices = degree_vocab.encode_sequence(full)
        # Next-token prediction: inputs are all but the last, labels all but
        # the first.
        sequences.append(indices[:-1])
        labels = indices[1:]
        # Mask out the context region - only continuation positions score.
        n_context = len(window.context_degrees)
        masked = [PAD_INDEX] * (n_context - 1) + labels[n_context - 1:]
        targets.append(masked)
        ragas.append(condition_vocab.raga(window.raga))
        talas.append(condition_vocab.tala(window.tala))
        composers.append(condition_vocab.composer(window.composer))

    width = max(len(s) for s in sequences)
    pad = lambda rows: [row + [PAD_INDEX] * (width - len(row)) for row in rows]

    return (
        torch.tensor(pad(sequences), dtype=torch.long),
        torch.tensor(pad(targets), dtype=torch.long),
        torch.tensor(ragas, dtype=torch.long),
        torch.tensor(talas, dtype=torch.long),
        torch.tensor(composers, dtype=torch.long) if use_composer else None,
    )


def _epoch(net, batches, loss_fn, optimizer=None) -> Tuple[float, float]:
    """One pass. Passing an optimizer makes it a training pass."""
    torch, _ = _require_torch()
    training = optimizer is not None
    net.train(training)

    total, count = 0.0, 0
    correct, target_count = 0, 0
    for sequences, targets, ragas, talas, composers in batches:
        with torch.set_grad_enabled(training):
            logits = net(sequences, ragas, talas, composers)
            loss = loss_fn(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
        if training:
            optimizer.zero_grad()
            loss.backward()
            # These models are small and the data is tiny; clipping keeps a
            # single odd batch from destabilising a short run.
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            optimizer.step()
        total += float(loss.detach())
        count += 1
        mask = targets != PAD_INDEX
        correct += int(((logits.detach().argmax(dim=-1) == targets) & mask).sum())
        target_count += int(mask.sum())
    return total / max(count, 1), 100.0 * correct / max(target_count, 1)


def _batches(windows: Sequence[Window], degree_vocab, condition_vocab,
             batch_size: int, use_composer: bool, shuffle: bool,
             rng: random.Random):
    order = list(range(len(windows)))
    if shuffle:
        rng.shuffle(order)
    for start in range(0, len(order), batch_size):
        chunk = [windows[i] for i in order[start:start + batch_size]]
        yield encode_batch(chunk, degree_vocab, condition_vocab, use_composer)


def train(model: TorchModel, train_windows: Sequence[Window],
          val_windows: Sequence[Window],
          config: Optional[TrainConfig] = None) -> TrainResult:
    """Train one model with early stopping on validation loss."""
    torch, nn = _require_torch()
    config = config or TrainConfig()
    set_seed(config.seed)
    rng = random.Random(config.seed)

    condition_vocab = ConditionVocab.from_windows(train_windows)
    net = model.build(condition_vocab)

    loss_fn = nn.CrossEntropyLoss(ignore_index=PAD_INDEX)
    optimizer = torch.optim.Adam(net.parameters(), lr=config.learning_rate,
                                 weight_decay=config.weight_decay)

    best_loss = float("inf")
    best_epoch = 0
    best_state = None
    since_improved = 0
    history: List[Dict[str, float]] = []

    for epoch in range(config.epochs):
        train_loss, train_accuracy = _epoch(
            net,
            _batches(train_windows, model.degree_vocab, condition_vocab,
                     config.batch_size, model.use_composer, True, rng),
            loss_fn, optimizer,
        )
        val_loss, val_accuracy = (
            _epoch(net,
                   _batches(val_windows, model.degree_vocab, condition_vocab,
                            config.batch_size, model.use_composer, False, rng),
                   loss_fn)
            if val_windows else (train_loss, train_accuracy)
        )

        history.append({"epoch": epoch, "train_loss": train_loss,
                        "val_loss": val_loss, "train_accuracy": train_accuracy,
                        "val_accuracy": val_accuracy})
        if config.verbose:
            print(f"  epoch {epoch + 1:3d}  train {train_loss:.4f}  val {val_loss:.4f}"
                  f"  train acc {train_accuracy:.2f}%  val acc {val_accuracy:.2f}%",
                  flush=True)

        if val_loss < best_loss - 1e-5:
            best_loss, best_epoch = val_loss, epoch
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
            since_improved = 0
        else:
            since_improved += 1
            if since_improved >= config.patience:
                break

    # Always finish on the best weights, not the last ones.
    if best_state is not None:
        net.load_state_dict(best_state)

    model.history = history
    return TrainResult(model=model, best_val_loss=best_loss,
                       best_epoch=best_epoch, epochs_run=len(history),
                       history=history)


def train_many(architecture: str, train_windows: Sequence[Window],
               val_windows: Sequence[Window], seeds: Sequence[int],
               config: Optional[TrainConfig] = None,
               **model_kwargs) -> List[TrainResult]:
    """Train the same setup across several seeds.

    With 42 validation windows from 2 compositions, early stopping is noisy;
    a single run is not evidence. Every reported number averages these.
    """
    results: List[TrainResult] = []
    for seed in seeds:
        run_config = TrainConfig(**{**(config or TrainConfig()).__dict__,
                                    "seed": seed})
        model = TorchModel(architecture=architecture, seed=seed, **model_kwargs)
        results.append(train(model, train_windows, val_windows, run_config))
    return results


def mean_std(values: Sequence[float]) -> Tuple[float, float]:
    """Mean and population standard deviation."""
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, variance ** 0.5
