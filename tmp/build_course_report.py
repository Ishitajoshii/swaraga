from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('D:/ishi/swaraga')
OUT = ROOT / 'output/docx'
TMP = ROOT / 'tmp/course_report'
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

# A diagram drawn directly from build_gru in src/swaraga/models/neural.py.
im = Image.new('RGB', (1560, 640), 'white')
d = ImageDraw.Draw(im)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 29)
bold = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
def box(x1,y1,x2,y2,lines):
    d.rectangle((x1,y1,x2,y2), fill='#F5F5F5', outline='#555555', width=2)
    for i, line in enumerate(lines):
        d.text(((x1+x2)/2, y1+20+i*37),line,font=bold if i==0 else font,anchor='mt',fill='black')
def arrow(x1,y1,x2,y2):
    d.line((x1,y1,x2,y2), fill='black',width=3)
    if y2>y1: d.polygon([(x2,y2),(x2-8,y2-13),(x2+8,y2-13)], fill='black')
    else: d.polygon([(x2,y2),(x2-13,y2-8),(x2-13,y2+8)],fill='black')
box(20,10,510,150,['Degree IDs  (B, L)','Embedding 32 x 64','Output (B, L, 64)'])
box(535,10,1025,150,['Raga ID  (B,)','Embedding 17 x 16','Repeat over L: (B, L, 16)'])
box(1050,10,1540,150,['Tala ID  (B,)','Embedding 6 x 8','Repeat over L: (B, L, 8)'])
for x in [265,780,1295]: arrow(x,150,x,185)
d.line((265,185,1295,185),fill='black',width=3)
arrow(780,185,780,210)
box(300,210,1260,300,['Concatenate 64 + 16 + 8 = 88','GRU input (B, L, 88)'])
d.line((780,300,780,315),fill='black',width=3)
box(160,330,730,435,['One GRU layer  hidden size 128','Hidden states (B, L, 128)'])
d.line((780,315,445,315),fill='black',width=3)
arrow(445,315,445,330)
box(835,330,1405,435,['Dropout 0.3 then Linear 128 to 32','Logits (B, L, 32)'])
arrow(730,383,835,383)
arrow(1120,435,1120,480)
box(160,480,1405,615,['Inference: last-step logits to softmax to constrained sampling','Append one degree and repeat until 8 positions are generated','Map scale degrees back to swaras in the selected raga'])
im.save(TMP/'gru_architecture.png')

doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.27); sec.page_height=Inches(11.69)
sec.top_margin=sec.bottom_margin=Inches(.65)
sec.left_margin=sec.right_margin=Inches(.7)
normal=doc.styles['Normal']; normal.font.name='Arial'; normal.font.size=Pt(10.5)
normal.paragraph_format.space_after=Pt(6)
normal.paragraph_format.line_spacing=1.06
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
for name,size in [('Title',21),('Heading 1',13),('Heading 2',11)]:
    s=doc.styles[name]; s.font.name='Arial'; s.font.size=Pt(size); s.font.color.rgb=RGBColor(0,0,0)
    s.paragraph_format.space_before=Pt(10); s.paragraph_format.space_after=Pt(5)
doc.styles['Title'].paragraph_format.space_before=Pt(0)
def p(t): return doc.add_paragraph(t)
def h(t): doc.add_heading(t,level=1)
def table(headers, rows, widths):
    t=doc.add_table(rows=1, cols=len(headers)); t.autofit=False
    for c,w in zip(t.columns,widths): c.width=Inches(w)
    for c,txt in zip(t.rows[0].cells,headers): c.text=txt
    for row in rows:
        for c,txt in zip(t.add_row().cells,row): c.text=str(txt)
    for i,row in enumerate(t.rows):
        for j,c in enumerate(row.cells):
            c.width=Inches(widths[j]); pr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
            pr.append(borders)
            margins=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side); e.set(qn('w:w'),'75'); e.set(qn('w:type'),'dxa'); margins.append(e)
            pr.append(margins)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(0)
                for r in para.runs: r.font.size=Pt(9.5); r.bold=(i==0)
            if i==0:
                shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'EEEEEE'); pr.append(shade)
        trPr=row._tr.get_or_add_trPr(); trPr.append(OxmlElement('w:cantSplit'))
    return t

doc.add_heading('Swaraga Final Course Project Report',0)
p('Carnatic melody continuation')
p('Name: [Add names and registration numbers]    Course: [Add course name]')
h('1 Project goal')
p('Swaraga predicts a short Carnatic melody continuation from a given swara sequence. In the main T2 task, it takes 16 musical positions and generates the next 8 positions, using raga and tala information. A position can be a note or a rest.')
p('The project compares an n-gram baseline with GRU and Transformer neural models. The current Mohanam localhost demo uses the n-gram model and plays synthesized notes or retrieves existing vocal responses. The neural model described below is the experimental GRU.')
h('2 Dataset description')
p('The symbolic dataset contains 20 composition fragments, 20 ragas, 8 composers and 6 talas. It contains 1,018 swara/rest positions: 907 notes and 111 rests. Sequences range from 32 to 84 positions, with an average of 50.9. Each record includes composition ID, composer, raga, tala and notation.')
p('Preprocessing standardizes names, checks duplicates and notation errors, and rebuilds swara sequences from the source notation. Notes are converted to relative scale degrees so that patterns can be shared across ragas. The original corpus source has not been independently verified.')
p('[Add the original dataset source URL and verify its provenance. If you collected the dataset yourself, upload the permitted dataset to Kaggle and paste its Kaggle link here.]')
p('Separate demo material includes 63 Mohanam notation passages from two compositions and 4 self-recorded vocal takes, prepared as 6 seed-response pairs. These additions are not part of the historical neural test results reported below.')
p('[If the self-collected recordings are submitted as a dataset, add their Kaggle link here.]')
h('3 Training validation and test split')
table(['Split','Compositions','Percentage','T2 windows'],[
('Training',16,'80%',466),('Validation',2,'10%',42),('Test',2,'10%',50),('Total',20,'100%',558)], [1.7,1.7,1.5,1.9])
p('Seed: 42. Splitting is done by whole composition, with composer-group stratification, before making overlapping windows. A composition cannot appear in more than one split. Windows use a stride of 1, so they are not independent recordings.')
p('These counts describe the saved neural experiments. The current demo excludes windows containing foreign-note errors and uses 449 corpus training windows, plus the separate Mohanam notation supplement.')

doc.add_page_break()
h('4 Input and output tensor sizes')
p('For T2, batch size B = 32. Shifting the 16-position context plus 8-position target by one gives training length L = 23. The vocabulary has 32 entries, including padding, rest and foreign-note markers.')
table(['Tensor','Shape'],[
('Training input IDs and target labels','(B, 23), normally (32, 23)'),
('Raga IDs and tala IDs','(B,) each'),
('GRU output logits','(B, 23, 32)'),
('Single test seed and generated continuation','Input (1, 16); final output (1, 8)')],[4.0,2.8])
h('5 Loss function')
p('Cross-entropy loss: L = -mean(log P(correct next token)). Padding and the first 15 context-only labels are ignored using ignore_index = 0; only the 8 continuation positions contribute. Training uses Adam, learning rate 0.001, weight decay 0.0001, up to 200 epochs and early stopping after 10 epochs without validation-loss improvement.')
h('6 Model architecture')
doc.add_picture(str(TMP/'gru_architecture.png'),width=Inches(6.2))
p('Figure 1. Conditional GRU. B is batch size; L is sequence length. Composer conditioning is disabled. The input grows after each prediction.')
h('7 Calculation of trainable parameters')
table(['Component','Calculation','Parameters'],[
('Degree embedding','32 x 64','2,048'),
('Raga embedding','17 x 16','272'),
('Tala embedding','6 x 8','48'),
('GRU input weights','3 x 128 x 88','33,792'),
('GRU recurrent weights','3 x 128 x 128','49,152'),
('GRU biases','2 x 3 x 128','768'),
('Output layer','128 x 32 + 32','4,128'),
('Total','2,048 + 272 + 48 + 33,792 + 49,152 + 768 + 4,128','90,208')],[2.0,3.85,.95])
p('Condition vocabularies: 16 ragas + unknown; 5 talas + unknown. All embedding rows are counted. Dropout and concatenation add no parameters.')

doc.add_page_break()
h('8 Training loss and accuracy versus epochs')
p('[Insert a graph of GRU training loss and validation loss versus epochs. Rerun training and save the epoch history: the current experiment script does not save it to disk. Label both axes and both curves.]')
p('[Insert a graph of GRU training accuracy and validation accuracy versus epochs. Add accuracy logging to the training loop first: calculate the percentage of correct next-token predictions over the 8 unmasked target positions. Accuracy is not currently logged.]')
p('The model with the lowest validation loss is used for final evaluation. The n-gram baseline fits counts rather than training over epochs, so the required epoch plots should come from the neural experiment.')
h('9 Sample test prediction and final test accuracy')
p('Held-out example: kalyani_varnam_ata_001, Kalyani raga, Khanda Ata tala. The B1 n-gram prediction below was reproduced using the historical experiment setup, fitted only on the training split, with decoding seed 420000 for the first test window.')
for label,notes in [
('Input of 16 positions',"S R2 G3 M2 P D2 N3 S' R2' S' N3 D2 P M2 G3 R2"),
('Expected next 8 positions',"S REST REST REST S' N3 D2 P"),
('B1 predicted next 8 positions',"S REST D2 N3 S' N3 D2 P")]:
    para=p(''); para.add_run(label+': ').bold=True; para.add_run(notes)
p('This sample matches 6 of 8 target positions, giving 75% positional accuracy for this example only. REST means a rest, and an apostrophe marks the upper octave.')
p('[Add the GRU prediction for the same held-out input, with a terminal screenshot showing input, expected output and predicted output. The historical GRU checkpoint and individual predictions were not saved.]')
p('Final saved test results for T2, experiment seed 42:')
table(['Model','Test positional accuracy','Test perplexity'],[
('B1 n-gram','32.25% (129 / 400)','2.25'),
('M1 GRU','25.75% (103 / 400)','2.44'),
('M1 Transformer','25.25% (101 / 400)','4.80')],[2.0,2.9,1.9])
p('Accuracy is the percentage of generated positions matching the reference: correct positions / total target positions x 100. The test set has 50 windows x 8 positions = 400 positions from 2 compositions. This is positional accuracy, not the percentage of completely correct phrases.')
p('For this saved T2 experiment, B1 has the highest positional accuracy. Results are preliminary because the corpus is small, windows overlap and the original notation provenance is unverified. Raga pitch membership is enforced by the representation and must not be reported as 100% prediction accuracy.')
p('[Optional demo screenshot: open http://127.0.0.1:8765 and capture a seed with its generated continuation. Label it as an n-gram demo example; the hand-written demo seeds are not held-out test examples.]')
p('Project evidence: reports/dataset_statistics.json; reports/baseline_results.json; data/splits; src/swaraga/models/neural.py; src/swaraga/train.py; docs/SUBMISSION_NOTES.md.')
doc.core_properties.title='Swaraga Final Course Project Report'
doc.core_properties.subject='Carnatic melody continuation course project'
doc.save(OUT/'Swaraga_Final_Course_Project_Report.docx')
print(OUT/'Swaraga_Final_Course_Project_Report.docx')
