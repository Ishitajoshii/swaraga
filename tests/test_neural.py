"""M1 neural models and the training loop.

Every test here skips cleanly without torch, so the baseline suite stays
runnable in a light environment (PRD section 8.2).

The two that matter most:

- :func:`test_overfits_a_single_batch` proves the training loop is actually
  wired - a model that cannot memorise one batch has a broken gradient path,
  and no amount of tuning will fix it.
- :func:`test_generated_output_is_always_in_raga` extends the architecture's
  central guarantee to the neural models.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from swaraga import config
from swaraga.grammar import RagaGrammarLibrary
from swaraga.models.neural import (
    ARCHITECTURES,
    TorchModel,
    TorchNotAvailable,
    torch_available,
)
from swaraga.vocab import PAD_INDEX, ConditionVocab, DegreeVocab
from swaraga.windows import build_windows

pytestmark = pytest.mark.skipif(not torch_available(), reason="torch not installed")

ARCHS = sorted(ARCHITECTURES)


@pytest.fixture(scope="module")
def data():
    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    library = RagaGrammarLibrary()
    windows = build_windows(frame, rung="T2", library=library)
    return frame, library, windows


@pytest.fixture(scope="module")
def trained(data):
    """One cheap run per architecture, shared across tests."""
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    models = {}
    for architecture in ARCHS:
        model = TorchModel(architecture=architecture, seed=42)
        train(model, windows[:120], windows[120:150],
              TrainConfig(epochs=6, patience=6, seed=42))
        models[architecture] = model
    return models


# --- construction -----------------------------------------------------------

@pytest.mark.parametrize("architecture", ARCHS)
def test_models_build(architecture) -> None:
    model = TorchModel(architecture=architecture, seed=1)
    model.build(ConditionVocab.from_windows([]))
    assert model.n_parameters > 0


def test_models_are_small(trained) -> None:
    """Sized for a few hundred windows, not for a benchmark."""
    assert trained["gru"].n_parameters < 200_000
    assert trained["transformer"].n_parameters < 600_000


def test_unknown_architecture_is_rejected() -> None:
    with pytest.raises(ValueError):
        TorchModel(architecture="mamba")


def test_using_an_untrained_model_is_an_error() -> None:
    model = TorchModel(architecture="gru")
    with pytest.raises(RuntimeError):
        model.next_scores([0, 1, 2])


# --- the NextScorer contract ------------------------------------------------

@pytest.mark.parametrize("architecture", ARCHS)
def test_next_scores_matches_the_decoder_protocol(trained, data, architecture) -> None:
    _, _, windows = data
    model = trained[architecture].condition_from(windows[0])
    scores = model.next_scores(windows[0].context_degrees)
    assert scores
    assert all(isinstance(k, int) for k in scores)
    assert all(v > 0 for v in scores.values())


@pytest.mark.parametrize("architecture", ARCHS)
def test_probability_is_a_distribution(trained, data, architecture) -> None:
    _, _, windows = data
    model = trained[architecture].condition_from(windows[0])
    context = windows[0].context_degrees
    total = sum(model.probability(context, d)
                for d in model.degree_vocab.degrees)
    assert total == pytest.approx(1.0, abs=1e-4)


@pytest.mark.parametrize("architecture", ARCHS)
def test_padding_is_never_offered_as_a_note(trained, data, architecture) -> None:
    """Padding is a tensor-shape device, not a musical event."""
    _, _, windows = data
    model = trained[architecture].condition_from(windows[0])
    scores = model.next_scores(windows[0].context_degrees)
    assert model.degree_vocab.decode(PAD_INDEX) not in scores


# --- the architecture's central guarantee -----------------------------------

@pytest.mark.parametrize("architecture", ARCHS)
def test_generated_output_is_always_in_raga(trained, data, architecture) -> None:
    from swaraga.decode import ConstrainedDecoder

    frame, library, windows = data
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    model = trained[architecture]

    for seed in range(5):
        window = windows[seed * 53 % len(windows)]
        grammar = library.for_row(by_id[window.record_id])
        model.condition_from(window)
        result = ConstrainedDecoder(grammar, rng=random.Random(seed)).decode(
            model, window.context_degrees, 8
        )
        assert len(result.degrees) == 8
        for swara in result.swaras:
            if swara != config.REST:
                assert swara.rstrip("'.") in grammar.swaras


# --- training ---------------------------------------------------------------

@pytest.mark.parametrize("architecture", ARCHS)
def test_overfits_a_single_batch(data, architecture) -> None:
    """A broken gradient path cannot memorise one batch; a working one can."""
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    batch = windows[:8]
    model = TorchModel(architecture=architecture, seed=0, dropout=0.0)
    result = train(model, batch, batch,
                   TrainConfig(epochs=150, patience=150, seed=0,
                               learning_rate=3e-3, weight_decay=0.0))
    assert result.history[-1]["train_loss"] < 0.5 * result.history[0]["train_loss"]


def test_training_reduces_loss(data) -> None:
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    model = TorchModel(architecture="gru", seed=3)
    result = train(model, windows[:120], windows[120:150],
                   TrainConfig(epochs=12, patience=12, seed=3))
    assert result.history[-1]["train_loss"] < result.history[0]["train_loss"]


def test_early_stopping_restores_the_best_weights(data) -> None:
    """The run must end on its best epoch, not on its last."""
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    model = TorchModel(architecture="gru", seed=5)
    result = train(model, windows[:100], windows[100:130],
                   TrainConfig(epochs=40, patience=3, seed=5))
    assert result.best_epoch < result.epochs_run
    losses = [h["val_loss"] for h in result.history]
    assert result.best_val_loss == pytest.approx(min(losses), abs=1e-6)


def test_loss_is_masked_to_the_continuation(data) -> None:
    """Context positions must not score, or the model is graded on the prompt."""
    from swaraga.train import encode_batch

    _, _, windows = data
    window = windows[0]
    _, targets, _, _, _ = encode_batch(
        [window], DegreeVocab(), ConditionVocab.from_windows([window])
    )
    n_context = len(window.context_degrees)
    assert (targets[0][:n_context - 1] == PAD_INDEX).all()
    assert (targets[0][n_context - 1:] != PAD_INDEX).any()
    assert int((targets != PAD_INDEX).sum()) == 8


def test_accuracy_excludes_masked_positions_and_weights_tokens() -> None:
    """Unequal batches must be pooled by token count, ignoring context/padding."""
    import torch
    from swaraga.train import _epoch

    class FixedNet(torch.nn.Module):
        def forward(self, sequences, *conditions):
            return torch.nn.functional.one_hot(sequences, num_classes=3).float() * 4

    # 2/2 correct targets in the first batch, 0/1 in the second: 66.67%, not 50%.
    batches = [
        (torch.tensor([[2, 1, 2]]), torch.tensor([[PAD_INDEX, 1, 2]]), None, None, None),
        (torch.tensor([[2, 2, 2]]), torch.tensor([[PAD_INDEX, 1, PAD_INDEX]]), None, None, None),
    ]
    _, accuracy = _epoch(FixedNet(), batches,
                         torch.nn.CrossEntropyLoss(ignore_index=PAD_INDEX))
    assert accuracy == pytest.approx(100 * 2 / 3)


def test_same_seed_is_reproducible(data) -> None:
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    outputs = []
    for _ in range(2):
        model = TorchModel(architecture="gru", seed=7)
        train(model, windows[:80], windows[80:100],
              TrainConfig(epochs=5, patience=5, seed=7))
        model.condition_from(windows[0])
        outputs.append(model.next_scores(windows[0].context_degrees))
    assert outputs[0].keys() == outputs[1].keys()
    for degree in outputs[0]:
        assert outputs[0][degree] == pytest.approx(outputs[1][degree], abs=1e-9)


def test_different_seeds_diverge(data) -> None:
    from swaraga.train import TrainConfig, train

    _, _, windows = data
    results = []
    for seed in (11, 12):
        model = TorchModel(architecture="gru", seed=seed)
        train(model, windows[:80], windows[80:100],
              TrainConfig(epochs=5, patience=5, seed=seed))
        model.condition_from(windows[0])
        results.append(model.next_scores(windows[0].context_degrees))
    assert results[0] != results[1]


def test_conditioning_changes_the_prediction(trained, data) -> None:
    """If raga conditioning did nothing, the whole premise would be broken."""
    _, _, windows = data
    model = trained["gru"]
    context = windows[0].context_degrees

    model.set_condition(raga="Mohanam", tala="Adi")
    mohanam = model.next_scores(context)
    model.set_condition(raga="Hindolam", tala="Adi")
    hindolam = model.next_scores(context)

    assert any(abs(mohanam.get(d, 0) - hindolam.get(d, 0)) > 1e-6
               for d in set(mohanam) | set(hindolam))


def test_mean_std() -> None:
    from swaraga.train import mean_std

    mean, std = mean_std([1.0, 1.0, 1.0])
    assert (mean, std) == (1.0, 0.0)
    mean, _ = mean_std([1.0, 3.0])
    assert mean == 2.0
    assert mean_std([]) == (0.0, 0.0)


# --- optional-dependency behaviour ------------------------------------------

def test_torch_available_is_truthful() -> None:
    assert torch_available() is True


def test_missing_torch_raises_an_actionable_error() -> None:
    """The error must tell the reader how to fix it."""
    assert issubclass(TorchNotAvailable, ImportError)
