"""Tiny PyTorch demo: learn next-swara prediction, then generate a phrase.

Trains a one-layer GRU on the swara sequences in data/splits/train.jsonl for a
few seconds on CPU, then continues a seed phrase. 
Intentionally minimal - the
real M1 models live in src/swaraga/models/neural.py.
"""

import json
from pathlib import Path

import torch
import torch.nn as nn

torch.manual_seed(0)
ROOT = Path(__file__).resolve().parents[1]

# --- data: every training composition's swara_sequence -----------------------
seqs = [json.loads(line)["swara_sequence"]
        for line in open(ROOT / "data/splits/train.jsonl", encoding="utf-8")]
vocab = sorted({s for seq in seqs for s in seq})
stoi = {s: i for i, s in enumerate(vocab)}
data = [torch.tensor([stoi[s] for s in seq]) for seq in seqs if len(seq) > 1]


# --- model: embedding -> GRU -> logits over the next swara --------------------
class TinySwaraModel(nn.Module):
    def __init__(self, n_vocab, dim=32):
        super().__init__()
        self.embed = nn.Embedding(n_vocab, dim)
        self.gru = nn.GRU(dim, dim, batch_first=True)
        self.head = nn.Linear(dim, n_vocab)

    def forward(self, x, h=None):
        out, h = self.gru(self.embed(x), h)
        return self.head(out), h


model = TinySwaraModel(len(vocab))
opt = torch.optim.Adam(model.parameters(), lr=1e-2)
loss_fn = nn.CrossEntropyLoss()
print(f"{len(data)} sequences, {len(vocab)} swaras, "
      f"{sum(p.numel() for p in model.parameters())} params\n")

# --- train ---------------------------------------------------------------------
for epoch in range(1, 31):
    total = 0.0
    for seq in data:
        x, y = seq[:-1].unsqueeze(0), seq[1:].unsqueeze(0)
        logits, _ = model(x)
        loss = loss_fn(logits.squeeze(0), y.squeeze(0))
        opt.zero_grad()
        loss.backward()
        opt.step()
        total += loss.item()
    if epoch % 5 == 0:
        print(f"epoch {epoch:2d}  loss {total / len(data):.3f}")

# --- generate ------------------------------------------------------------------
seed = ["S", "R2", "G2"] if all(s in stoi for s in ["S", "R2", "G2"]) else vocab[:3]
model.eval()
with torch.no_grad():
    out = list(seed)
    logits, h = model(torch.tensor([[stoi[s] for s in seed]]))
    for _ in range(24):
        probs = torch.softmax(logits[0, -1] / 0.8, dim=-1)  # temperature 0.8
        nxt = vocab[torch.multinomial(probs, 1).item()]
        out.append(nxt)
        logits, h = model(torch.tensor([[stoi[nxt]]]), h)

print("\nseed:     ", " ".join(seed))
print("generated:", " ".join(out))
