from pathlib import Path
import html
import json
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/swaraga_concepts_pytorch_viva_guide.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
for name, filename in [('Body','arial.ttf'),('BodyBold','arialbd.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/' + filename))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='Body', boldItalic='BodyBold')
INK = colors.HexColor('#15283B')
TEAL = colors.HexColor('#007E87')
PALE = colors.HexColor('#EDF5F6')
GRAY = colors.HexColor('#5D6B77')
WIDTH, HEIGHT = A4
CW = WIDTH - 96
styles = {
    'body': ParagraphStyle('body', fontName='Body', fontSize=9.6, leading=14, textColor=INK, spaceAfter=7),
    'small': ParagraphStyle('small', fontName='Body', fontSize=8.3, leading=11.7, textColor=GRAY, spaceAfter=5),
    'h': ParagraphStyle('h', fontName='BodyBold', fontSize=12, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=6),
    'title': ParagraphStyle('title', fontName='BodyBold', fontSize=23, leading=28, textColor=INK, spaceAfter=15),
    'deck': ParagraphStyle('deck', fontName='Body', fontSize=11.2, leading=16, textColor=GRAY, spaceAfter=14),
    'code': ParagraphStyle('code', fontName='Mono', fontSize=8.2, leading=11.5, textColor=INK, backColor=PALE, borderPadding=9, spaceBefore=5, spaceAfter=12),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=8.8, leading=12.1, textColor=INK),
    'thead': ParagraphStyle('thead', fontName='BodyBold', fontSize=8.8, leading=12.1, textColor=colors.white),
    'q': ParagraphStyle('q', fontName='BodyBold', fontSize=9.6, leading=13.1, textColor=TEAL, spaceBefore=7, spaceAfter=3),
}
story = []
pages = []
qcount = 0
def p(text, style='body'):
    story.append(Paragraph(text, styles[style]))
def h(text): p(text, 'h')
def code(text):
    text = text.strip('\n')
    assert max(map(len,text.splitlines()),default=0) <= 88, text
    story.append(Preformatted(text, styles['code']))
def table(headers, rows, widths=None):
    data = [[Paragraph(str(c), styles['thead']) for c in headers]]
    data += [[Paragraph(str(c), styles['cell']) for c in row] for row in rows]
    t = Table(data, colWidths=[CW*x for x in widths] if widths else None, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[PALE,colors.white]),
        ('LINEBELOW',(0,0),(-1,0),.6,TEAL),
    ]))
    story.extend([t, Spacer(1,8)])
def callout(text):
    t=Table([[Paragraph(text,styles['body'])]],colWidths=[CW])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.6,TEAL),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([t,Spacer(1,8)])
def page(title, subtitle=''):
    if pages: story.append(PageBreak())
    pages.append(title)
    p(f'{len(pages):02d} / STUDY NOTES', 'small')
    p(title, 'title')
    if subtitle: p(subtitle, 'deck')
def qa(question, answer):
    global qcount
    qcount += 1
    story.append(KeepTogether([Paragraph(f'{qcount}. {question}', styles['q']),Paragraph(answer,styles['body'])]))

page('Swaraga\nConcepts + viva guide'.replace('\n','<br/>'), 'Project-specific explanations, PyTorch essentials, and short answers to rehearse aloud.')
callout('<b>Your 30-second introduction</b><br/>Swaraga explores short Carnatic melodic continuation. It cleans symbolic notation, represents notes as raga-relative scale degrees, compares simple baselines with conditional GRU and Transformer models, and applies grammar rules during decoding. The current local demo uses an n-gram model for swaras and a separate system for retrieving recorded vocal responses.')
h('How to use this guide')
p('Start with pages 2-13 to understand the project. Practise pages 14-20 with a Python interpreter. Use the viva bank on pages 21-26 without looking at the answers, then attempt the coding drills. Page 29 is the last-minute revision sheet.')
table(['Pages','What you will learn'],[
('2-5','Carnatic terms, preprocessing, representations, splits and windowing'),
('6-10','Baselines, constrained decoding, GRU, Transformer and training'),
('11-13','Metrics, saved results, audio and the current demo'),
('14-20','Tensors, shapes, autograd, modules, training and inference syntax'),
('21-26','64 potential viva questions with model answers'),
('27-28','Eight coding drills and worked solutions'),
('29-30','Revision sheet, source map and next steps'),
],[.16,.84])
h('Scope and evidence')
p('Prepared from the local Swaraga repository on 27 October 2026, including implementation files and submission notes. Saved experimental results are labelled as historical; this guide does not claim a fresh training run. Basic PyTorch API usage was checked against official documentation.')
p('<b>Keep these distinctions clear:</b> symbolic generation is separate from audio retrieval; structural validity is separate from musical quality; overlapping windows are separate from independent compositions. The existing notation corpus has unverified provenance.')

page('Carnatic concepts you need', 'Explain the musical problem before explaining the network.')
table(['Term','Meaning in this project'],[
('Swara','A note category: S, R, G, M, P, D, N. Variant labels such as R1/R2 and G2/G3 distinguish note choices.'),
('Raga','A melodic framework involving permitted notes, characteristic phrases, movement and ornamentation. A note set alone is insufficient.'),
('Arohanam / avarohanam','Ascending / descending paths. They may use different notes or non-straight movement.'),
('Vakra / prayoga','Zigzag motion / characteristic phrase. These motivate grammar beyond pitch membership.'),
('Nyasa / jeeva / graha','Resting note / prominent identity-bearing note / phrase-start note, respectively.'),
('Gamaka','Expressive ornamentation, often involving pitch movement. Discrete fixed pitches cannot capture it fully.'),
('Tala / avartana','Rhythmic cycle framework / one complete cycle. Aksharas and subdivision determine the project\'s position count.'),
('Tonic / octave','Sa is the pitch reference. An octave doubles frequency; upper and lower registers are encoded explicitly.'),
],[.26,.74])
h('Melakarta and variant resolution')
p('The 72-melakarta scheme provides parent-scale variants. The code combines 6 allowed R/G pairs, 6 D/N pairs and 2 M choices: 6 x 6 x 2 = 72. S and P are fixed. For example, mela 29 resolves to S R2 G3 M1 P D2 N3.')
p('The pipeline uses the declared mela rather than letter case because case is inconsistent in the source. Parent-scale resolution is a useful rule, but it cannot reconstruct every janya or bhashanga exception: the recorded Bhairavi limitation is a concrete example.')
h('Positions are a modelling simplification')
p('The code models an avartana as <b>aksharas x kala</b> notated positions. With Adi represented as 8 aksharas and kala=2, one cycle has 16 positions. Eight positions are half a cycle only under that setup. T2 is always 16 positions in and 8 out, not a universal half-avartana task.')
callout('<b>Say carefully:</b> the corpus maps karvai positions to [REST]. In musical usage a karvai may indicate a sustained duration; the code\'s rest/silence treatment is a simplification, not a full duration model.')

page('Data and preprocessing', 'A model is only as trustworthy as its input representation.')
code('raw parquet -> clean -> normalize -> validate/report\n            -> composition split -> training windows')
table(['Snapshot','Count'],[
('Composition fragments / composers / ragas / talas','20 / 8 / 20 / 6'),
('Trinity compositions / distinct melakartas','8 / 10'),
('All sequence positions / pitched swaras / rest markers','1,018 / 907 / 111'),
('Mean sequence length / observed swara vocabulary','50.9 / 24, including [REST]'),
('Whole-composition train / validation / test','16 / 2 / 2'),
],[.72,.28])
h('What each stage does')
p('<b>Cleaning:</b> standardize Unicode, whitespace and punctuation; check record integrity, duplicates and notation. Preserve raw values and record repairs in a quality log. Cleaning is not permission to invent missing musical facts.')
p('<b>Normalization:</b> use controlled dictionaries for composer, raga and tala aliases. Keep uncertain attribution explicit. Derive period/century fields where possible. Trinity membership comes from an explicit dictionary, not fuzzy name similarity.')
p('<b>Representation rebuilding:</b> parse sections_json and recover section/bar boundaries and note positions. Resolve swara variants using the mela and preserve the source note spelling for traceability.')
h('Why the original tokens were rejected')
p('The source tokens attach GMK_AHAT everywhere, use variants that contradict the raga, and omit all 111 rest positions. Reusing those targets would train the model on avoidable errors. Rebuilding from notation fixes the representation but does not prove that the notation itself is authentic.')
h('Known exceptions worth remembering')
p('<b>Hindolam:</b> a source fragment contains R even though its supplied scale has no rishabha. It is flagged; the demo excludes windows containing a foreign-note marker.<br/><b>Bhairavi:</b> the declared mela resolves D1, while the documented ascending D2 cannot be recovered from ambiguous source notation.<br/><b>Provenance:</b> uniform tonic and gamaka metadata are reasons to investigate, not proof of fabrication.')
p('Parquet is a typed columnar storage format useful for tabular data. JSONL stores one JSON record per line and is convenient for inspecting splits. A quality log makes transformations and unresolved issues auditable.', 'small')

page('Representations and vocabulary', 'Three different vocabularies appear in this project. Do not mix them up.')
table(['Representation','Example / purpose'],[
('Flat swara sequence',"S, R2, G3, [REST], P, D2, S' - notes and octave marks for window construction."),
('Structured token sequence','[BOS], [TALA:Adi], [SECTION:Pallavi], [BAR], S, ... [EOS] - retains structure; observed vocabulary size is 41.'),
('Scale-degree sequence','0, 1, 2, -1000, 3, 4, 5 in Mohanam - pooled relative-note modelling.'),
('Dense model indices','Contiguous nonnegative IDs for embedding lookup. Default neural vocabulary size is 32.'),
],[.31,.69])
h('Worked example: Mohanam')
code("scale = [S, R2, G3, P, D2]   # n = 5\nS -> 0     R2 -> 1     G3 -> 2     P -> 3     D2 -> 4\nS' -> 5    R2' -> 6    D2. -> -1\nbase note = scale[degree % n]\noctave = degree // n")
p('A degree is the note\'s index in its own raga scale, not a semitone count. A one-degree step can have different acoustic sizes in different ragas. Pooling makes contour patterns transferable, but discards some raga-specific pitch and ornamentation information.')
h('PAD, REST and FOREIGN are different')
p('<b>Degree-space markers:</b> REST_DEGREE=-1000 and FOREIGN_DEGREE=-1001. A negative ordinary degree is a valid lower-register note, so -1 cannot safely mean rest.')
p('<b>Dense indices:</b> PAD=0, REST=1, FOREIGN=2, then degrees -7 through 21 occupy indices 3 through 31. Thus degree 0 maps to ID 10. The 29 ordinary degrees plus two markers plus padding give 32 classes.')
p('PAD fills a tensor rectangle and is ignored as a target. REST is a musical event and can be learned. FOREIGN marks invalid or unrepresentable input; it is not a legitimate generated pitch. The decoder candidate set excludes FOREIGN. The inverse conversion displays special non-note values as rests, so upstream error detection remains essential.')
callout('<b>Unknown condition is another concept:</b> raga/tala/composer vocabularies reserve ID 0 for unseen categories. Unlike PAD, this is a conditioning lookup. If no unknowns occur during training, that embedding may remain untrained; it is not automatically a learned universal-raga embedding.')

page('Splits, windows and leakage', 'The independent unit is the composition, not each overlapping crop.')
table(['Rung','Context -> target','Saved full-corpus count'],[
('T1','12 -> 4 positions','718 windows'),
('T2','16 -> 8 positions','558 windows'),
('T3','4 -> 2 avartanas','59 windows, from 6 compositions'),
],[.12,.43,.45])
h('How a window is made')
p('For sequence length L, context k, horizon h and stride s, the count is max(0, floor((L-k-h)/s)+1). Windows never cross composition boundaries. With L=50, k=16, h=8 and s=1, there are 27 windows. Adjacent windows share 23 of their 24 positions.')
code('piece:   a b c d e f g h i ...\nwindow1: [context........][target....]\nwindow2:   [context........][target....]')
p('The composition IDs determine train, validation and test ownership; all windows from one composition inherit its split. Randomly splitting windows would put almost identical fragments on both sides and inflate evaluation scores.')
h('What the three splits are for')
p('<b>Training:</b> fit count tables or neural parameters.<br/><b>Validation:</b> select hyperparameters, monitor overfitting and choose the best epoch.<br/><b>Test:</b> evaluate the selected approach; do not repeatedly tune against it.')
p('The split targets 80/10/10 overall and distributes holdout slots across composer groups. At n=20, validation and test have only two compositions each, so every subgroup cannot be represented. Unknown / Unclassified is train-only in the current allocation.')
h('An especially important consequence')
p('Every raga occurs in one composition. A composition-held-out raga is therefore also absent from the training condition vocabulary. Its learned condition lookup uses UNKNOWN, while its externally supplied grammar still defines the scale. Results cannot establish learned, within-raga generalization.')
callout('<b>Keep counts labelled:</b> the legacy T2 study has 466 training windows before the demo\'s validity filter; the submission notes report 449 valid demo training windows from 15 contributing compositions. Neither is 449 or 466 independent performances.')
p('T3 has 59 stride-one-position windows; the PRD also mentions about 14 with an avartana stride. Different strides explain the counts. Unmetered material has no avartana-based T3 window.', 'small')

page('The four baseline approaches', 'A baseline tells you whether extra model complexity earns its place.')
table(['Model','How it works','What it tests'],[
('B0: random walk','Provides simple candidate preferences without fitting a corpus.','Can rules alone produce valid output?'),
('B0.5: direction heuristic','Uses recent movement to favor plausible local motion.','Does learned structure beat a musical heuristic?'),
('B1: variable-order Markov','Counts next degrees under different context lengths; combines shorter contexts.','How much can local repetition explain?'),
('B2: retrieval + adaptation','Matches trailing interval contours and uses neighbors\' next-step suggestions.','Can similar training phrases guide continuation?'),
],[.25,.46,.29])
h('B1: counts, context and backoff')
p('A Markov approximation predicts the next event from a limited recent history. For context c, a count estimate is count(c,x)/sum_y count(c,y). Long contexts are specific but sparse; short contexts have more support but less musical detail.')
p('In this implementation max_order=4 means up to <b>four preceding degrees</b> predicting the next one, i.e. an event can involve five positions. The code sums supported context-length distributions, reducing the weight by alpha=0.4 per shorter order. It is weighted multi-order scoring, not simply stopping at the first seen context.')
code('score(x) = sum_over_orders weight(order) * P_count(x | suffix)\nP(x | context) = score(x) / sum_all_x score(x)')
p('The model counts the full context+target sequence for each training window. Overlap therefore repeats many observations and gives interior passages more weight. Counts are not independent evidence. It has no backpropagation, embeddings or learned neural weights.')
h('B2: what is actually retrieved?')
p('The symbolic retrieval baseline uses the last six real context notes to form intervals, ranks similarity, takes up to five neighbors, and relocates the first target step relative to the query\'s last degree. The shared decoder asks again at each generated step. It does not simply paste an entire retrieved continuation.')
callout('<b>Two retrieval systems:</b> B2 adapts symbolic degrees. The local vocal demo retrieves an already recorded response under compatibility filters; it does not pitch-shift the recording into an arbitrary new melody.')

page('Grammar and constrained decoding', 'Separate model preference from the rules that restrict its choices.')
h('One generation step')
p('1. Read the context and find its last real movement to infer direction.<br/>2. Obtain permissible next swaras from the grammar and map them into the allowed register.<br/>3. Limit large jumps; optionally allow a rest with a consecutive-rest cap.<br/>4. Ask the model for next-degree scores and remove illegal or nonpositive candidates.<br/>5. Sample or choose the highest-scoring candidate; append it and repeat until the horizon is filled.')
code('model scores:   S=.2  R2=.1  G3=.5  D2=.2\nallowed now:    S, R2, G3\nrenormalized:   S=.25 R2=.125 G3=.625')
h('Temperature and greedy selection')
p('For positive scores s, the sampler uses weights s^(1/T). Lower positive temperature sharpens preferences; higher temperature flattens them. For probability-derived scores this corresponds to softmax(logits/T). Greedy selects the maximum; the code also treats T&lt;=0 as greedy and breaks ties deterministically.')
h('Fallback behavior matters')
p('If the model gives no positive legal score, the decoder uses uniform legal scores and increments fell_back. If the legal-motion calculation itself finds no candidates, legal_degrees can broaden to the register candidate set. Therefore avoid an unconditional claim that every possible fallback preserves every directional rule.')
p('The default register is from one octave below up to, but excluding, two octaves above the base scale. The consecutive generated-rest cap is three. The supplied TalaTemplate supports position calculations, but this decoder does not fully model note durations, gamakas or expressive tala timing.')
h('Three different mechanisms')
table(['Property','Where it comes from'],[
('Note membership','Ordinary degrees map through the selected raga scale; out-of-scale pitched output is structurally excluded.'),
('Motion restrictions','Direction-aware grammar mask, register and local-jump rules, with the fallback caveat above.'),
('Output position count','A generation loop with exactly horizon steps.'),
('Musical plausibility','Model quality, representation, repertoire and human judgment; not guaranteed by the other rows.'),
],[.28,.72])

page('GRU: recurrence with memory', 'The project\'s smaller conditional neural language model.')
p('A recurrent network updates a hidden state as each token arrives. A vanilla RNN repeatedly transforms the previous state and current input; gradients can shrink or grow across many steps. A GRU uses gates to regulate memory and improve optimization, although it does not eliminate every long-range learning problem.')
h('Gate intuition and equations')
code('r_t = sigmoid(W_ir x_t + b_ir + W_hr h_prev + b_hr)\nz_t = sigmoid(W_iz x_t + b_iz + W_hz h_prev + b_hz)\nn_t = tanh(W_in x_t + b_in + r_t * (W_hn h_prev + b_hn))\nh_t = (1 - z_t) * n_t + z_t * h_prev')
p('The reset gate r controls old information used in the candidate state. The update gate z balances old and new state. In PyTorch\'s convention above, z near 1 retains the old state. Multiplication here is elementwise. A GRU has a hidden state; an LSTM additionally maintains a separate cell state.')
h('Actual Swaraga dimensions')
table(['Stage','Shape with batch B and steps T'],[
('Input IDs','[B,T], dtype long'),
('Degree embedding','[B,T,64]'),
('Raga and tala embeddings, expanded over time','[B,T,16] and [B,T,8]'),
('Concatenate features','[B,T,88] without composer; 96 with composer'),
('One GRU layer, hidden size 128','output [B,T,128]; h_n [1,B,128]'),
('Dropout 0.3, Linear(128,32)','Logits [B,T,32]'),
],[.59,.41])
p('batch_first=True makes the input/output batch dimension first; h_n still starts with layers x directions. The GRU\'s built-in dropout applies between recurrent layers and is set to zero here for one layer. The separate output Dropout still runs during training.')
p('The default model without composer conditioning has approximately 90k parameters; the saved report lists 90,208. Exact totals depend on condition vocabulary sizes. For one GRU layer of input width I and hidden size H, parameters are 3HI + 3H^2 + 6H with both bias vectors.')
p('Source: models/neural.py. Gate convention and API shape semantics checked against the official PyTorch GRU reference [P3, page 30].', 'small')

page('Transformer: causal attention', 'Attention gives each position access to relevant earlier positions.')
code('Attention(Q,K,V) = softmax(Q K^T / sqrt(d_k) + mask) V')
p('Queries ask what information a position needs; keys describe what other positions offer; values carry the information to combine. Scaling by sqrt(d_k) controls score magnitude. Four heads learn different comparisons, and their outputs are combined.')
h('The actual architecture')
p('Degree, learned position, raga and tala embeddings all have width 128 and are <b>added</b>. Composer embeddings are optional. Two TransformerEncoderLayer blocks use four heads, feed-forward width 256, dropout 0.3 and norm_first=True. A final LayerNorm and Linear(128,32) produce logits. The learned position table has 256 entries.')
code('IDs [B,T]\n   -> degree + position + raga + tala embeddings [B,T,128]\n   -> 2 causal self-attention/FFN blocks [B,T,128]\n   -> LayerNorm -> Linear -> logits [B,T,32]')
h('Why the causal mask is essential')
p('At position t the model must predict the next event using only positions up to t. The mask blocks attention to future positions with negative infinity before attention softmax. Without it, teacher-forced input contains future answers and evaluation would be misleading.')
p('The implementation uses TransformerEncoder as a stack of self-attention blocks with a causal mask. Its <b>behavior is autoregressive</b> even though the PyTorch container is named Encoder. There is no separate source encoder and cross-attention decoder here.')
h('Position, residuals and normalization')
p('Attention alone does not encode sequence order, so learned position vectors distinguish first, second and later positions. Residual connections preserve a direct information/gradient path. LayerNorm stabilizes feature statistics; the feed-forward sublayer transforms features at each position. These are not substitutes for a causal mask.')
table(['GRU','Transformer'],[
('Sequential state update','Parallel token processing during teacher-forced training'),
('Strong recurrence bias; smaller here','Flexible context interactions; more parameters here'),
('History compressed into hidden state','Self-attention has quadratic pairwise cost in sequence length'),
('Both generate one new token at a time','Both can overfit this tiny corpus'),
],[.5,.5])
p('The saved default parameter count is 309,152, not a universal architecture constant. This code reprocesses history during next-token calls; it does not implement an attention key/value cache.', 'small')

page('Training: what the code learns', 'Teacher forcing, continuation-only loss and validation-based stopping.')
h('The shifted next-token objective')
code('context = [a,b,c]       target = [d,e]\nfull    = [a,b,c,d,e]\ninput   = [a,b,c,d]\nlabels  = [PAD,PAD,d,e]\n# Position 2 predicts d after seeing a,b,c.\n# Position 3 predicts e after seeing a,b,c,d.')
p('Teacher forcing supplies the true preceding token during training. Only target-region predictions contribute to the loss: the first k-1 labels are PAD. For T2, input and label width is 16+8-1=23, with 15 ignored context labels and 8 scored continuation labels.')
h('Cross-entropy and gradients')
p('For valid labels, loss is the mean of -log P(correct token | history). A high probability for the correct token lowers the loss. The network emits raw logits; CrossEntropyLoss performs the needed log-softmax calculation. Feeding softmax probabilities to it is incorrect for this standard setup.')
p('logits [B,T,V] are reshaped to [B*T,V], and targets [B,T] to [B*T]. ignore_index=0 removes padding/context labels from the objective. It does not remove the PAD class from the output softmax, and it does not create an attention mask.')
h('Actual training configuration')
table(['Setting','Default / purpose'],[
('Optimizer','Adam; learning rate 0.001; weight_decay 0.0001'),
('Training budget','Up to 200 epochs; batch size 32'),
('Stability','Clip total gradient norm to 1.0 before optimizer.step()'),
('Early stopping','Patience 10 epochs; improvement threshold 0.00001'),
('Final model','Restore a cloned copy of the best validation state'),
('Randomness','Python and Torch seeds; deterministic algorithms requested with warn_only=True'),
],[.31,.69])
p('An epoch is one pass over training windows; a batch is one group used for a gradient update. Adam maintains running first and second gradient moments. Dropout and weight decay regularize the model; clipping limits large updates; early stopping selects when to stop. They solve different problems.')
callout('<b>Training/inference mismatch:</b> generation feeds back its own predicted notes. Errors can compound over longer horizons; this is exposure bias. Teacher-forced perplexity and sampled continuation quality therefore measure different behaviors.')

page('Metrics and how to defend them', 'No single number establishes that a continuation sounds like the raga.')
table(['Metric','Definition and interpretation'],[
('Exact match','Fraction of target positions whose degree matches the reference. It is token accuracy, not the fraction of completely correct phrases.'),
('Contour distance','Band-limited DTW of consecutive-note degree intervals, divided by the longer interval count. Lower is better; rests are removed.'),
('Nyasa','Whether the final pitched event is in the grammar\'s resting-note set; averaged over windows. A narrow endpoint check.'),
('Novelty','Fraction of generated 4-gram occurrences absent from the training 4-gram set. Compare with the corpus reference, not an ideal of 1.'),
('Perplexity','exp(-mean log probability of true continuation events). Lower means stronger reference-token prediction, not guaranteed musical quality.'),
('Raga conformance','Pitch-set membership after degree-to-swara mapping. Structurally near/trivially 1 for ordinary generated degrees.'),
('Length exact','Whether the generated position count equals the target count. It says little about performed timing.'),
('Transition legality','Legacy implementation includes context transitions and uses a more permissive direction check. Do not quote it as validated output quality.'),
],[.25,.75])
h('DTW in plain words')
p('Dynamic time warping aligns two sequences while allowing limited stretching. This code uses absolute interval differences and a Sakoe-Chiba band of one, widened when needed for unequal lengths. The band prevents excessive alignment freedom from making very different short contours appear identical.')
h('Two metric traps')
p('<b>Novelty:</b> random notes can be highly novel and musically poor. The saved T2 corpus reference is 0.13 and B1 is 0.16. Because source authenticity is unverified, call it the corpus reference rather than independently verified human ground truth.')
p('<b>Perplexity:</b> evaluation follows true target history and floors probabilities at 1e-6. Neural inference masks PAD before softmax; training loss retains PAD in its normalization. Thus exp(reported training loss) need not exactly equal the separately computed evaluation perplexity.')
p('An all-rest output can receive vacuous conformance because there are no pitched notes to violate the scale. Pair structural checks with rest rates, continuity and listening tests. The current metric suite is an engineering proxy, not a full musical judge.', 'small')

page('Saved results: a careful reading', 'Historical seed-42 experiments; no models were retrained for this guide.')
h('T2: 16-position context, 8-position continuation')
table(['Model','Contour ↓','Token match ↑','Nyasa','Novelty','PPL ↓'],[
('Corpus GT','0.00','1.00','0.50','0.13','-'),
('B0','3.21','0.09','0.42','1.00','-'),
('B0.5','1.45','0.15','0.36','0.87','-'),
('B1','1.11','0.32','0.56','0.16','2.3'),
('B2','1.52','0.22','0.38','0.76','-'),
('M1 GRU','1.39','0.26','0.50','0.38','2.4'),
('M1 Transformer','1.40','0.25','0.58','0.48','4.8'),
],[.24,.15,.19,.13,.14,.15])
p('The table covers 50 overlapping test windows from the small held-out composition split. B1 has better T2 contour distance, token match and perplexity than these neural runs. The Transformer has a higher nyasa value than B1, so saying B1 wins every column is inaccurate.')
h('T1 shows a different tradeoff')
p('At the four-position horizon, B1 has contour distance 0.90, token match 0.46 and perplexity 2.2. The GRU has 1.12, 0.53 and 2.1 respectively: better token match/perplexity but worse contour distance. The Transformer has 1.14, 0.50 and 3.1. The shorter-horizon finding is mixed, not a universal neural victory.')
h('Scaling study: what it can suggest')
p('The saved study trains on 2, 4, 8 and 16 compositions and averages neural results over five seeds. Its GRU validation-minus-training loss gap falls from about 1.04 to 0.04; the Transformer gap falls from about 1.06 to 0.37. This is compatible with less overfitting as training coverage grows, but the tiny fixed test set limits conclusions.')
callout('<b>Do not present:</b> the superseded constraint-ablation table or legacy transition-legality values. The submission notes explicitly withdraw those claims. A credible replacement needs a generated-transition-only, direction-consistent metric and a rerun of both ablation arms.')
p('Useful conclusion: simple local statistics are competitive at this data scale. More model capacity is not automatically useful when examples overlap heavily and raga identity has only one composition of evidence. These results do not establish that n-grams generally outperform neural music models.')
p('Sources: reports/baseline_results.md, reports/scaling_study.md and docs/SUBMISSION_NOTES.md; the newer submission cautions take precedence over stale claims in older prose.', 'small')

page('Audio and the local demo', 'Know exactly what is generated and what is recorded.')
h('Generated swaras')
p('The current demo fits the B1 n-gram on valid training windows, takes one of three hand-written Mohanam seeds, and produces eight positions after a sixteen-position context. Fixed random seeds 42/43/44 make the examples repeatable. These are demonstration prompts, not held-out test cases. The demo does not import or train a neural model.')
p('Reference playback uses a 24,000 Hz sample rate and uniform 0.32-second positions. For a note s semitones above Sa, f=tonic_hz * 2^(s/12). It combines a sine wave with a smaller second harmonic and an attack/release envelope. A [REST] becomes zeros. These are equal-tempered reference tones, not realistic vocal singing or learned gamakas.')
h('Recorded vocal response')
p('<b>Prepared mode:</b> play an approved seed/response pair.<br/><b>Retrieval mode:</b> select a compatible existing response from another source group/take using manually supplied annotations. It does not synthesize the n-gram\'s output in the singer\'s voice.')
table(['Filter / ranking rule','Current implementation'],[
('Identity and split','Exact raga/tala and meter; reject same group or source take; keep bank/evaluation sources separate.'),
('Tuning and timing','Tonic difference at most 25 cents; query/candidate tempo ratio within 3%; join phase within 0.15 beats.'),
('Ranking','Mean absolute difference between 32-sample normalized-time annotated contours, plus absolute log seed-duration ratio.'),
('Preparation','Trim copies with provenance, preserve originals, and use a common gain for both halves of a pair.'),
],[.28,.72])
p('At this snapshot, annotations.json is empty and the submission checkpoint reports no approved recorded pairs. The app can demonstrate the empty-bank state; do not claim completed vocal evaluation. Manual note/timing annotation is not automatic pitch extraction or transcription.')
h('DSP basics the professor might ask')
p('Sample rate is samples per second; frequency is oscillations per second. The Nyquist limit is half the sample rate. Amplitude controls signal level; clipping occurs when representable range is exceeded. An envelope smooths note boundaries and reduces clicks. None of these operations by itself supplies expressive Carnatic ornamentation.')

page('PyTorch basics: tensors', 'A tensor is a multidimensional array with a dtype and a device.')
code('''import torch
from torch import nn

torch.manual_seed(42)
scalar = torch.tensor(3.0)                 # shape []
vector = torch.tensor([1, 2, 3])           # shape [3]
matrix = torch.zeros(2, 3)                # shape [2,3]
noise = torch.randn(2, 3)                 # normal samples
ones = torch.ones(2, 3)
ids = torch.tensor([[10, 11, 12]], dtype=torch.long)
print(ids.shape, ids.dtype, ids.device)
print(ids.ndim, ids.numel())              # 2, 3
floats = ids.float()                      # float32
ids_again = floats.long()                 # int64''')
h('Dtype and device rules')
p('Use torch.long for discrete embedding IDs and class-index labels. Floating-point tensors store activations, weights and differentiable values. The data and model must be on compatible devices. Calling .to(device) on a tensor returns the converted tensor, so assign the result.')
code('''device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
x = torch.randn(4, 8).to(device)
layer = nn.Linear(8, 3).to(device)
logits = layer(x)                         # [4,3]
values = logits.detach().cpu().numpy()     # for NumPy use
one_value = logits[0, 0].item()           # Python scalar''')
h('Basic indexing and arithmetic')
code('''a = torch.arange(6).reshape(2, 3)
print(a)                                 # [[0,1,2],[3,4,5]]
print(a[0], a[:, -1])                     # [0,1,2], [2,5]
print(a[:, :2])                           # first two columns
print(a + 1)                             # elementwise add
print(a * a)                             # elementwise multiply
print(a @ a.T)                           # matrix multiplication
print(a.float().mean(dim=1))              # [1.,4.]
print(a.sum().item())                     # 15''')
p('<b>Watch:</b> a Python list is not a model-ready batch by itself. torch.tensor creates a tensor; shape describes axes, dtype describes values, and device describes where computation happens. torch.randn samples a normal distribution; torch.rand samples uniformly on [0,1).', 'small')

page('Shapes: the viva favorite', 'Always write the input shape, operation and output shape.')
code('''x = torch.randn(2, 3, 4)             # B=2, T=3, features=4
print(x.size(1))                     # 3
print(x.reshape(6, 4).shape)          # [6,4]
print(x.reshape(-1, 4).shape)         # [6,4], infer one size
print(x.transpose(1, 2).shape)        # [2,4,3]
print(x.permute(2, 0, 1).shape)       # [4,2,3]
print(x[:, -1, :].shape)             # [2,4]
print(x[0, -1].shape)                # [4]
print(x.argmax(dim=-1).shape)        # [2,3]''')
h('Unsqueeze, expand and conditioning')
code('''raga_vec = torch.randn(2, 16)         # [B,16]
raga_vec = raga_vec.unsqueeze(1)      # [B,1,16]
raga_time = raga_vec.expand(-1, 3, -1) # [B,T,16]
degree_vec = torch.randn(2, 3, 64)
joined = torch.cat([degree_vec, raga_time], dim=-1)
print(joined.shape)                   # [2,3,80]''')
p('unsqueeze inserts a size-one dimension. expand broadcasts an existing singleton dimension without copying its values; -1 keeps a dimension unchanged. repeat physically repeats values. Do not modify an expanded view in place when multiple entries share storage.')
h('Cat versus stack; reshape versus transpose')
code('''a, b = torch.ones(2, 3), torch.zeros(2, 3)
torch.cat([a, b], dim=0).shape        # [4,3]: existing axis
torch.cat([a, b], dim=1).shape        # [2,6]
torch.stack([a, b], dim=0).shape      # [2,2,3]: new axis
torch.ones(2, 1, 3).squeeze(1).shape  # [2,3]''')
p('reshape changes how the same element sequence is grouped; transpose/permute reorder axes. view requires compatible strides; reshape can copy when needed. A transposed tensor is often non-contiguous, so blindly calling view on it can fail. Calling squeeze() without a dimension may accidentally remove a size-one batch axis.')
h('Broadcasting and softmax')
p('Dimensions compare from the right: sizes must match or one must be 1. Thus [B,T,128] + [B,1,128] works. softmax(logits, dim=-1) normalizes over the vocabulary, not over time or batch. For [B,T,V], argmax(dim=-1) returns token IDs [B,T].')
p('In loss code, reshape(-1,V) merges batch and time but preserves the class axis. It does not mix the ordering of labels when targets are flattened in the same order.', 'small')

page('Autograd and gradient descent', 'Know what backward() does, and what it does not do.')
code('''x = torch.tensor([2.0, 3.0], requires_grad=True)
loss = (x ** 2).sum()                 # 13
loss.backward()
print(x.grad)                        # tensor([4., 6.])

# New forward graph; gradients still accumulate by default.
(x ** 2).sum().backward()
print(x.grad)                        # tensor([8., 12.])
x.grad = None                        # clear accumulated gradient''')
p('Autograd records differentiable tensor operations and applies the chain rule backward from a loss. For a scalar loss it starts with derivative 1. A non-scalar output generally needs a supplied upstream gradient, or a reduction such as sum/mean first.')
h('The optimizer sequence')
code('''optimizer.zero_grad()                # clear previous gradients
predictions = model(inputs)          # forward pass
loss = loss_fn(predictions, labels)   # scalar objective
loss.backward()                      # populate parameter .grad
torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
optimizer.step()                     # update parameter values''')
p('This generic skeleton assumes model, inputs, labels and loss_fn are defined. backward computes gradients; step changes weights. zero_grad must happen before the backward pass whose gradients you want to keep. In the repo it occurs after forward/loss but before backward, which is valid.')
h('Three switches that are often confused')
table(['Operation','Effect'],[
('model.eval()','Changes mode-sensitive layers, such as Dropout. It does not disable gradient recording.'),
('with torch.no_grad():','Disables gradient recording in the block. It does not switch Dropout to evaluation behavior.'),
('tensor.detach()','Returns a tensor disconnected from its history; storage is shared. detach().clone() also copies values.'),
('parameter.requires_grad_(False)','Prevents gradients being accumulated for that parameter; useful when freezing weights.'),
],[.39,.61])
p('The graph is normally released after backward. Do a new forward pass for the next update; retain_graph=True is not a routine training fix. Avoid using .item() or constructing a new tensor from a loss inside the differentiable path, because that can break the connection to parameters.')
callout('<b>One-line answer:</b> forward calculates predictions; loss measures error; backward calculates derivatives; the optimizer uses those derivatives to update weights.')

page('Modules, layers and data loaders', 'Minimal class syntax plus the components behind the project.')
code('''class TinyClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(4, 8), nn.ReLU(), nn.Linear(8, 3)
        )

    def forward(self, x):
        return self.layers(x)

net = TinyClassifier()
out = net(torch.randn(5, 4))          # [5,3]
count = sum(p.numel() for p in net.parameters())
print(count)                         # (4*8+8) + (8*3+3) = 67''')
p('nn.Module registers child layers and parameters. super().__init__() initializes that machinery. __init__ builds layers once; forward defines the computation used repeatedly. Prefer net(x) to calling net.forward(x) directly so Module hooks work. A method\'s self refers to that instance.')
h('Layer meanings')
p('<b>Linear(in,out):</b> applies a learned affine map to the last dimension. A bias-enabled layer has in*out + out parameters.<br/><b>Embedding(V,E):</b> looks up one learned E-dimensional row per integer ID; [B,T] becomes [B,T,E]. It is not one-hot encoding.<br/><b>ReLU:</b> max(0,x), a nonlinearity. <b>Dropout:</b> randomly suppresses activations during training. <b>LayerNorm:</b> normalizes specified feature dimensions.')
h('Dataset and DataLoader basics')
code('''from torch.utils.data import TensorDataset, DataLoader

features = torch.randn(40, 4)
labels = torch.randint(0, 3, (40,), dtype=torch.long)
dataset = TensorDataset(features, labels)
loader = DataLoader(dataset, batch_size=8, shuffle=True)
xb, yb = next(iter(loader))           # [8,4], [8]''')
p('A custom Dataset typically implements __len__ and __getitem__. DataLoader handles batching, optional shuffling and collation. Training usually shuffles examples; validation usually does not. Variable-length examples need a collate function that pads them and supplies suitable masks/lengths.')
p('Swaraga uses its own _batches generator and encode_batch function rather than DataLoader. The concepts are the same: choose examples, map values to IDs, pad a batch and emit tensors. Teaching DataLoader syntax does not mean the repository uses it.', 'small')

page('A complete tiny training example', 'Runnable CPU example: continuation-only training, with the same key shapes as T2.')
code('''import torch
from torch import nn

torch.manual_seed(42)
B, K, H, V = 4, 16, 8, 32

class TinyLM(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(V, 16, padding_idx=0)
        self.gru = nn.GRU(16, 32, batch_first=True)
        self.head = nn.Linear(32, V)

    def forward(self, ids):
        hidden, _ = self.gru(self.embed(ids))
        return self.head(hidden)

model = TinyLM()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss(ignore_index=0)

# Synthetic IDs only: this illustrates mechanics, not musical data.
full = torch.randint(1, V, (B, K + H))
inputs = full[:, :-1]                 # [4,23]
targets = full[:, 1:].clone()         # [4,23]
targets[:, :K - 1] = 0                # ignore 15 context labels

for step in range(3):
    model.train()
    optimizer.zero_grad()
    logits = model(inputs)           # [4,23,32]
    loss = criterion(logits.reshape(-1, V), targets.reshape(-1))
    loss.backward()
    nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    print(step, round(loss.item(), 4))

model.eval()
with torch.no_grad():
    check = model(inputs)
    score = criterion(check.reshape(-1, V), targets.reshape(-1))
print("same-batch check loss:", score.item())''')
p('<b>Explain these details:</b> clone() prevents masking targets from also changing the shared full tensor; long IDs select embedding rows; logits remain unnormalized for cross-entropy; 4*8=32 target positions contribute to the loss.')
p('This example omits raga/tala conditioning for readability and checks the same synthetic batch. It is not a validation experiment or a trained Carnatic generator. The repository adds condition embeddings, real windows, batching and best-validation-checkpoint selection.', 'small')

page('Inference, sampling and saving', 'Run after page 18 so TinyLM, model and full already exist.')
code('''model.eval()
history = full[:1, :K].clone()         # one context, [1,16]
with torch.no_grad():
    for _ in range(H):
        next_logits = model(history)[:, -1, :]  # [1,V]
        next_logits[:, 0] = float("-inf")       # no PAD output
        probabilities = torch.softmax(next_logits / 0.8, dim=-1)
        next_id = torch.multinomial(probabilities, 1)  # [1,1]
        history = torch.cat([history, next_id], dim=1)
generated = history[:, K:]            # [1,8]

# Greedy alternative for one step:
greedy_id = next_logits.argmax(dim=-1, keepdim=True)''')
p('This is unconstrained toy sampling except for PAD suppression. A project generation call also excludes foreign-note markers and applies its legal-degree set. If every logit is -inf, softmax is invalid; handle an empty legal set before sampling. The production decoder has an explicit fallback path.')
h('Weights and reproducible interpretation')
code('''torch.save(model.state_dict(), "tiny_weights.pt")
restored = TinyLM()                    # same architecture
weights = torch.load("tiny_weights.pt", map_location="cpu",
                     weights_only=True)
restored.load_state_dict(weights)
restored.eval()

with torch.no_grad():
    prediction = restored(inputs)
print(prediction.shape)                # [4,23,32]''')
p('state_dict contains named parameter and persistent-buffer tensors, not the constructor code. Rebuild the matching architecture before loading. Save vocabulary mappings and configuration with the trained artifact: otherwise token ID 10 could silently mean the wrong event.')
p('To resume training faithfully, also save optimizer state, epoch, random-generator state and scheduler state when applicable. A weights-only file is sufficient for many inference cases but not an exact continuation of the optimization process.')
h('Evaluation loop essentials')
p('Use model.eval() together with no_grad() or inference_mode(). Compute loss/metrics without optimizer updates. For token accuracy, count matches only where targets != PAD. Aggregate by valid-token counts if batches have unequal lengths; averaging batch means equally can weight small batches too heavily.')
p('Official PyTorch saving/loading guidance is listed as [P8] on page 30. The actual project wrapper exposes state_dict/load_state_dict; this example demonstrates how to persist the network weights to disk.', 'small')

page('Read the project code aloud', 'These lines connect basic syntax to the real implementation.')
h('GRU conditioning path')
code('''steps = degrees.size(1)
parts = [self.degree(degrees),
         self.raga(raga).unsqueeze(1).expand(-1, steps, -1),
         self.tala(tala).unsqueeze(1).expand(-1, steps, -1)]
hidden_states, _ = self.gru(torch.cat(parts, dim=-1))
return self.out(self.drop(hidden_states))''')
p('degrees is [B,T]. Its embedding is [B,T,64]. raga is [B], becoming [B,16], then [B,1,16], then [B,T,16]. Tala follows the same pattern with width 8. Concatenation gives 88 features per time step. The underscore discards the returned final hidden state; hidden_states contains every time step.')
h('Training loss path')
code('''logits = net(sequences, ragas, talas, composers)
loss = loss_fn(logits.reshape(-1, logits.size(-1)),
               targets.reshape(-1))''')
p('For a full T2 batch of 32 windows: sequences [32,23]; logits [32,23,32]; flattened logits [736,32]; flattened targets [736]. With all windows complete, only 32*8=256 labels are scored. Batch size and vocabulary size both happen to be 32 here, but they mean different things.')
h('One next-token probability vector')
code('''logits = self.net(degrees, raga, tala, composer)[0, -1]
logits[PAD_INDEX] = float("-inf")
return torch.softmax(logits, dim=-1)''')
p('The network output is [1,T,V]. [0,-1] selects the first batch example and last sequence position, leaving [V]. PAD is suppressed before normalization. The wrapper maps dense IDs back to degree-space values; the shared decoder then applies musical restrictions.')
h('Best-epoch snapshot')
code('''best_state = {k: v.clone() for k, v in net.state_dict().items()}
# ... later, after training ...
net.load_state_dict(best_state)''')
p('clone() captures tensor values so later training updates do not mutate the saved best snapshot. Assigning best_state = net.state_dict() alone would retain references to the live tensors.')
callout('<b>Code-reading habit:</b> say what each variable means, its dtype and its shape, then explain the operation. This is more convincing than memorizing an API name without understanding the data flow.')

