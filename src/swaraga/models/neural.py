"""M1 - neural continuation models (PyTorch).

Two architectures behind one interface:

``GRUModel``
    ~90k params. The small-data workhorse; recurrence gives a useful inductive
    bias when there is not enough data to learn attention patterns.

``TransformerModel``
    ~270k params. What scales to T3's longer context, and what a thesis on
    sequence modelling is expected to include.

Both are sized for **466 training windows**, not for a benchmark. They are
deliberately tiny, and they are expected to overfit; the training loop's job is
to make that visible rather than to hide it.

``torch`` is imported lazily so the preprocessing pipeline and the B0-B2
baselines keep working in an environment without it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..vocab import PAD_INDEX, ConditionVocab, DegreeVocab
from ..windows import Window


class TorchNotAvailable(ImportError):
    """Raised when a neural model is requested without torch installed."""


def _require_torch():
    """Import torch on demand, with an actionable message if it is missing."""
    try:
        import torch  # noqa: F401
        import torch.nn as nn  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise TorchNotAvailable(
            "PyTorch is required for the M1 models. Install it with:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cpu"
        ) from exc
    return torch, nn


def torch_available() -> bool:
    try:
        _require_torch()
        return True
    except TorchNotAvailable:
        return False


# --- network definitions ----------------------------------------------------

def build_gru(vocab_size: int, n_ragas: int, n_talas: int, n_composers: int,
              embed: int = 64, raga_embed: int = 16, tala_embed: int = 8,
              hidden: int = 128, layers: int = 1, dropout: float = 0.3,
              use_composer: bool = False):
    """A conditional GRU language model over scale degrees."""
    torch, nn = _require_torch()

    class GRUNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.use_composer = use_composer
            self.degree = nn.Embedding(vocab_size, embed, padding_idx=PAD_INDEX)
            self.raga = nn.Embedding(n_ragas, raga_embed)
            self.tala = nn.Embedding(n_talas, tala_embed)
            self.composer = (nn.Embedding(n_composers, tala_embed)
                             if use_composer else None)

            width = embed + raga_embed + tala_embed + (tala_embed if use_composer else 0)
            self.gru = nn.GRU(width, hidden, num_layers=layers,
                              batch_first=True,
                              dropout=dropout if layers > 1 else 0.0)
            self.drop = nn.Dropout(dropout)
            self.out = nn.Linear(hidden, vocab_size)

        def forward(self, degrees, raga, tala, composer=None):
            steps = degrees.size(1)
            parts = [self.degree(degrees),
                     self.raga(raga).unsqueeze(1).expand(-1, steps, -1),
                     self.tala(tala).unsqueeze(1).expand(-1, steps, -1)]
            if self.composer is not None and composer is not None:
                parts.append(self.composer(composer).unsqueeze(1).expand(-1, steps, -1))
            hidden_states, _ = self.gru(torch.cat(parts, dim=-1))
            return self.out(self.drop(hidden_states))

    return GRUNet()


def build_transformer(vocab_size: int, n_ragas: int, n_talas: int, n_composers: int,
                      d_model: int = 128, layers: int = 2, heads: int = 4,
                      ff: int = 256, dropout: float = 0.3, max_len: int = 256,
                      use_composer: bool = False):
    """A small causal Transformer decoder over scale degrees."""
    torch, nn = _require_torch()

    class TransformerNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.use_composer = use_composer
            self.degree = nn.Embedding(vocab_size, d_model, padding_idx=PAD_INDEX)
            self.position = nn.Embedding(max_len, d_model)
            self.raga = nn.Embedding(n_ragas, d_model)
            self.tala = nn.Embedding(n_talas, d_model)
            self.composer = nn.Embedding(n_composers, d_model) if use_composer else None

            layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=heads, dim_feedforward=ff,
                dropout=dropout, batch_first=True, norm_first=True,
            )
            # norm_first makes the nested-tensor fast path inapplicable;
            # disabling it explicitly keeps the warning out of every run.
            self.encoder = nn.TransformerEncoder(
                layer, num_layers=layers, enable_nested_tensor=False
            )
            self.norm = nn.LayerNorm(d_model)
            self.out = nn.Linear(d_model, vocab_size)

        def forward(self, degrees, raga, tala, composer=None):
            steps = degrees.size(1)
            positions = torch.arange(steps, device=degrees.device)

            # Conditioning is added rather than concatenated here, which keeps
            # d_model fixed and lets attention see it at every position.
            hidden = self.degree(degrees) + self.position(positions).unsqueeze(0)
            hidden = hidden + self.raga(raga).unsqueeze(1)
            hidden = hidden + self.tala(tala).unsqueeze(1)
            if self.composer is not None and composer is not None:
                hidden = hidden + self.composer(composer).unsqueeze(1)

            mask = nn.Transformer.generate_square_subsequent_mask(
                steps, device=degrees.device
            )
            hidden = self.encoder(hidden, mask=mask, is_causal=True)
            return self.out(self.norm(hidden))

    return TransformerNet()


ARCHITECTURES = {"gru": build_gru, "transformer": build_transformer}


# --- the model wrapper ------------------------------------------------------

class TorchModel:
    """Wraps a network so it satisfies the decoder's ``NextScorer`` protocol.

    The decoder and the whole metric suite are architecture-agnostic; they only
    need ``next_scores`` and ``probability``. Conditioning is held on the
    instance because the decoder's interface deliberately passes only a
    context - a model generates for one (raga, tala) at a time.
    """

    def __init__(self, architecture: str = "gru",
                 degree_vocab: Optional[DegreeVocab] = None,
                 condition_vocab: Optional[ConditionVocab] = None,
                 use_composer: bool = False, seed: int = 42, **kwargs) -> None:
        torch, _ = _require_torch()
        if architecture not in ARCHITECTURES:
            raise ValueError(f"unknown architecture {architecture!r}; "
                             f"expected one of {sorted(ARCHITECTURES)}")

        torch.manual_seed(seed)
        self.architecture = architecture
        self.name = f"M1-{architecture}"
        self.description = f"conditional {architecture}"
        self.seed = seed
        self.use_composer = use_composer
        self.degree_vocab = degree_vocab or DegreeVocab()
        self.condition_vocab = condition_vocab
        self._kwargs = kwargs
        self.net = None
        self.history: List[Dict[str, float]] = []

        # Conditioning for the next generation call.
        self._raga = ""
        self._tala = ""
        self._composer = ""

    # -- construction -------------------------------------------------------

    def build(self, condition_vocab: ConditionVocab):
        torch, _ = _require_torch()
        torch.manual_seed(self.seed)
        self.condition_vocab = condition_vocab
        self.net = ARCHITECTURES[self.architecture](
            vocab_size=self.degree_vocab.size,
            n_ragas=condition_vocab.n_ragas,
            n_talas=condition_vocab.n_talas,
            n_composers=condition_vocab.n_composers,
            use_composer=self.use_composer,
            **self._kwargs,
        )
        return self.net

    @property
    def n_parameters(self) -> int:
        if self.net is None:
            return 0
        return sum(p.numel() for p in self.net.parameters())

    def set_condition(self, raga: str = "", tala: str = "",
                      composer: str = "") -> "TorchModel":
        """Set the (raga, tala) the next generation is conditioned on."""
        self._raga, self._tala, self._composer = raga, tala, composer
        return self

    def condition_from(self, window: Window) -> "TorchModel":
        return self.set_condition(window.raga, window.tala, window.composer)

    # -- inference ----------------------------------------------------------

    def _logits_for(self, context: Sequence[int]):
        torch, _ = _require_torch()
        if self.net is None or self.condition_vocab is None:
            raise RuntimeError("model has not been built or trained yet")

        self.net.eval()
        with torch.no_grad():
            indices = self.degree_vocab.encode_sequence(list(context)) or [PAD_INDEX]
            degrees = torch.tensor([indices], dtype=torch.long)
            raga = torch.tensor([self.condition_vocab.raga(self._raga)], dtype=torch.long)
            tala = torch.tensor([self.condition_vocab.tala(self._tala)], dtype=torch.long)
            composer = (
                torch.tensor([self.condition_vocab.composer(self._composer)],
                             dtype=torch.long)
                if self.use_composer else None
            )
            logits = self.net(degrees, raga, tala, composer)[0, -1]
            # Padding is a tensor-shape device, not a musical event. Masking it
            # before the softmax stops the model leaking probability mass onto
            # a non-event, which would otherwise inflate perplexity and leave
            # `next_scores` summing to slightly under 1.
            logits[PAD_INDEX] = float("-inf")
            return torch.softmax(logits, dim=-1)

    def next_scores(self, context: Sequence[int]) -> Dict[int, float]:
        """Probability over every degree the vocabulary can represent.

        Padding is excluded - it is a tensor-shape device, not a musical event,
        and letting the decoder sample it would be meaningless.
        """
        probabilities = self._logits_for(context)
        scores: Dict[int, float] = {}
        for index in range(1, self.degree_vocab.size):
            degree = self.degree_vocab.decode(index)
            if degree is not None:
                value = float(probabilities[index])
                if value > 0:
                    scores[degree] = value
        return scores

    def probability(self, context: Sequence[int], degree: int) -> float:
        """Normalised P(degree | context), for perplexity."""
        probabilities = self._logits_for(context)
        return float(probabilities[self.degree_vocab.encode(degree)])

    # -- persistence --------------------------------------------------------

    def state_dict(self):
        return None if self.net is None else self.net.state_dict()

    def load_state_dict(self, state) -> None:
        if self.net is None:
            raise RuntimeError("build the model before loading weights")
        self.net.load_state_dict(state)
