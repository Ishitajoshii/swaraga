import build_guide as g
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib import colors

g.story.clear()
g.pages.clear()
g.qcount = 0
g.OUT = g.ROOT / 'output/pdf/swaraga_basic_viva.pdf'
p,h,code,qa,page = g.p,g.h,g.code,g.qa,g.page

page('Swaraga: basic viva prep', 'Short answers to practise. You do not need to memorize the whole codebase.')
g.callout('<b>Start with this:</b> Our project explores Carnatic melody continuation. Given a short sequence of swaras, it predicts the next sequence. We clean the data, represent notes as scale degrees, and use raga rules to restrict the generated notes. The current demo uses an n-gram model.')
qa('What is the input and output?', 'For the main T2 task, the input is 16 musical positions and the output is the next 8 positions. Positions can include rest markers.')
qa('What is a raga? What is a tala?', 'A raga is a melodic framework involving notes, characteristic phrases and movement. A tala is a rhythmic cycle. An avartana is one complete cycle.')
qa('What is a swara? What is a gamaka?', 'A swara is a musical note category, such as S, R or G. A gamaka is an ornament or expressive pitch movement. Our reference-tone playback does not reproduce gamakas.')
qa('What dataset do we use?', 'The existing symbolic dataset contains 20 composition fragments, 20 ragas, 8 composers and 6 talas. It is very small, and its original notation sources are not independently verified.')
qa('Why do we preprocess the data?', 'To standardize names and notation, check errors and duplicates, and convert the data into consistent sequences. The original tokens had incorrect variants and missing rest positions, so they were rebuilt from notation.')
qa('What are scale degrees?', 'A scale degree is a note\'s position within the raga\'s scale. For Mohanam, S R2 G3 P D2 become 0 1 2 3 4. This lets models share relative melodic patterns across ragas.')
h('Remember these three words')
p('<b>Training:</b> learning from examples. <b>Inference:</b> using the fitted model to predict. <b>Baseline:</b> a simple approach used for comparison.')
p('Based on the local Swaraga implementation and submission notes, 27 October 2026. This is a revision sheet, not a new experimental report.', 'small')

page('Likely project questions', 'Keep each answer to two or three sentences.')
qa('Which models did you explore?', 'Random and direction-based baselines, an n-gram model, symbolic retrieval, a GRU and a Transformer. The current local swara demo uses the n-gram model; it does not train a neural network.')
qa('How does the n-gram model work?', 'It counts which notes tend to follow recent note patterns. It combines longer and shorter contexts so it can still predict when a long pattern is rare or unseen.')
qa('What is a GRU?', 'A Gated Recurrent Unit is a recurrent neural network that processes a sequence using a hidden state. Reset and update gates control how it uses previous information.')
qa('What is a Transformer?', 'A Transformer uses attention to combine information from relevant sequence positions. Our model uses a causal mask so it cannot look at future notes while predicting the next note.')
qa('How do you split the data? Why?', 'Whole compositions are split approximately 80% training, 10% validation and 10% test: 16, 2 and 2 here. Overlapping windows from the same composition stay together to avoid data leakage.')
qa('What is constrained decoding?', 'The model proposes next-note scores, and grammar rules restrict the available choices before selection. Scale-degree mapping keeps ordinary output notes in the chosen scale; being in-scale alone does not guarantee good music.')
qa('How do you evaluate the output?', 'We compare predicted notes with reference notes, compare melodic contours, and measure reference-token probability using perplexity. Listening is also needed because numerical scores do not fully capture musical quality.')
qa('What were the results and limitations?', 'In the saved T2 experiment, the n-gram had better contour distance and token accuracy than the GRU and Transformer. This is only a small-corpus result. We need more verified compositions and musical evaluation.')
qa('Does the demo generate a singer\'s voice?', 'No. Generated swaras use simple reference tones. The separate vocal feature selects existing recordings with manual annotations; it is not voice cloning. The current recording annotations are empty.')

page('Basic ML and PyTorch questions', 'These are the short definitions most useful for a viva.')
qa('What is PyTorch?', 'A Python framework for tensor computation and building neural networks. It provides layers, automatic differentiation and optimizers.')
qa('What is a tensor?', 'A multidimensional array. A scalar has zero dimensions, a vector has one, and a matrix has two. Tensors also have a data type and a device, such as CPU.')
qa('What is an embedding?', 'A learned vector representation of a discrete ID. An embedding converts note IDs into numerical feature vectors that a neural network can process.')
qa('What is a loss function?', 'It measures prediction error. We use cross-entropy for next-token prediction: assigning more probability to the correct note reduces the loss.')
qa('What are backpropagation and an optimizer?', 'Backpropagation computes how the loss changes with each parameter. An optimizer, such as Adam, uses those gradients to update the parameters.')
qa('What are an epoch, batch size and learning rate?', 'An epoch is one pass through the training data. Batch size is the number of examples in one update. Learning rate controls the scale of parameter updates.')
qa('What is overfitting? How can you reduce it?', 'Overfitting means learning training-specific patterns that do not generalize. More varied data, smaller models, dropout and early stopping can help.')
qa('What is teacher forcing?', 'During training, the model receives the true previous notes. During generation, it receives its own predictions, so errors can accumulate.')
qa('What is the difference between train(), eval() and no_grad()?', 'train() enables training behavior such as dropout. eval() switches such layers to evaluation behavior. no_grad() stops gradient recording; it does not automatically call eval().')
g.callout('<b>Most important sequence:</b> clear gradients → forward pass → calculate loss → backward pass → optimizer step.')

page('PyTorch syntax to practise', 'Read the comments, then try writing each example without looking.')
h('1. Create tensors and inspect shapes')
code('''import torch
from torch import nn

x = torch.tensor([[1., 2.], [3., 4.]])
print(x.shape)                       # torch.Size([2, 2])
print(x[0])                          # tensor([1., 2.])
print(x[:, 1])                       # tensor([2., 4.])
print(x.reshape(4).shape)            # torch.Size([4])
zeros = torch.zeros(2, 3)            # 2 rows, 3 columns
random_values = torch.randn(2, 3)    # normal random values''')
h('2. Embedding and a linear layer')
code('''ids = torch.tensor([[1, 2, 3]], dtype=torch.long)
embedding = nn.Embedding(32, 8)       # 32 IDs, 8 features each
features = embedding(ids)
print(features.shape)               # [1, 3, 8]

layer = nn.Linear(8, 32)             # 8 features -> 32 scores
logits = layer(features)
print(logits.shape)                 # [1, 3, 32]
probs = torch.softmax(logits, dim=-1)
predicted_ids = logits.argmax(dim=-1) # shape [1, 3]''')
h('3. GRU syntax and saving weights')
code('''gru = nn.GRU(input_size=8, hidden_size=16, batch_first=True)
output, hidden = gru(features)
print(output.shape)                 # [1, 3, 16]
print(hidden.shape)                 # [1, 1, 16]

torch.save(gru.state_dict(), "gru_weights.pt")''')
p('<b>Know the arguments:</b> batch_first=True means input shape [batch, sequence, features]. dim=-1 means the last axis. argmax returns the highest-scoring index. softmax converts scores into probabilities. torch.long is used for discrete IDs.')
p('<b>Common question:</b> Why no softmax before CrossEntropyLoss? It expects raw logits and handles the normalization internally. Use softmax when you want probabilities for inspection or sampling.')

page('The training loop to remember', 'A small standalone example. Synthetic labels demonstrate syntax, not project results.')
code('''import torch
from torch import nn

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = nn.Linear(4, 3)

    def forward(self, x):
        return self.layer(x)

model = Model()
x = torch.randn(5, 4)                # 5 examples, 4 features
y = torch.tensor([0, 1, 2, 1, 0])    # correct class IDs
loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

model.train()
optimizer.zero_grad()                # 1. clear old gradients
logits = model(x)                    # 2. forward: shape [5,3]
loss = loss_fn(logits, y)            # 3. calculate error
loss.backward()                     # 4. calculate gradients
optimizer.step()                    # 5. update weights
print(loss.item())                   # Python number

model.eval()
with torch.no_grad():
    predictions = model(x).argmax(dim=1)
print(predictions)''')
h('Be ready to explain these lines')
p('<b>nn.Module:</b> base class for neural networks. <b>super().__init__():</b> initializes its machinery.<br/><b>forward():</b> defines how input becomes output. <b>model.parameters():</b> supplies parameters to the optimizer.<br/><b>zero_grad():</b> clears gradients because PyTorch accumulates them.<br/><b>backward():</b> computes gradients. <b>step():</b> changes weights. These are different operations.')
g.callout('<b>Last-minute priorities:</b> explain your project in 30 seconds; know why you split by composition; explain an n-gram, GRU and Transformer; write this training loop; trace [batch, time, features] shapes.')
p('Sources: README.md; docs/SUBMISSION_NOTES.md; src/swaraga/models/neural.py; train.py; vocab.py; evaluate.py. PyTorch API references: <link href="https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html" color="#007E87">Quickstart</link>, <link href="https://docs.pytorch.org/docs/2.14/generated/torch.nn.GRU.html" color="#007E87">GRU</link>, <link href="https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html" color="#007E87">CrossEntropyLoss</link>.', 'small')

def decorate(c, doc):
    c.saveState()
    c.setStrokeColor(g.TEAL)
    c.line(48, g.HEIGHT-34, g.WIDTH-48, g.HEIGHT-34)
    c.setFont('Body', 8)
    c.setFillColor(g.GRAY)
    c.drawString(48, 25, 'SWARAGA  |  BASIC VIVA + PYTORCH')
    c.drawRightString(g.WIDTH-48, 25, str(doc.page))
    c.restoreState()

doc = SimpleDocTemplate(str(g.OUT), pagesize=g.A4, rightMargin=48, leftMargin=48,
                        topMargin=48, bottomMargin=44,
                        title='Swaraga: Basic Viva Questions and PyTorch Syntax',
                        author='Swaraga study notes')
doc.build(g.story, onFirstPage=decorate, onLaterPages=decorate)
print(g.OUT)
print('Questions:',g.qcount)
