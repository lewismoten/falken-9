#!/usr/bin/env python3
"""Measured host-side PNG/SVG maps. No game HUD edits or weight semantics guessed."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from falken9.flexible_integer_export import load
from falken9.symmetry import TRANSFORMS, transform_board
from scripts.build_runtime import FOUR_MODEL

BG='#101720';PANEL='#182330';INK='#edf2f6';MUTED='#aab9c6';STATIC='#b8a0eb';DYNAMIC='#eda85f';GREEN='#82d5a1';RED='#ee8e90';EDGE='#405368'


def read(path):return json.loads(Path(path).read_text())

def color(value,maximum):
    intensity=min(1,abs(float(value))/max(1,float(maximum)))
    target=(240,163,75) if value>=0 else (87,171,235)
    base=(28,40,54)
    return '#'+''.join(f'{round(a+(b-a)*intensity):02x}' for a,b in zip(base,target))


class Canvas:
    def __init__(self,width,height):
        self.size=(width,height);self.image=Image.new('RGB',self.size,BG);self.draw=ImageDraw.Draw(self.image)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',f'<rect width="100%" height="100%" fill="{BG}"/>']
        self.bounds=[]

    def rect(self,x,y,w,h,fill=PANEL,stroke=EDGE,width=1):
        self.draw.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke,width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def text(self,x,y,text,size=16,fill=INK):
        font=ImageFont.truetype('DejaVuSans.ttf',size)
        box=self.draw.textbbox((x,y),str(text),font=font,anchor='lt');self.bounds.append(list(box))
        self.draw.text((x,y),str(text),font=font,fill=fill,anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" dominant-baseline="hanging" font-family="DejaVu Sans,sans-serif" font-size="{size}" fill="{fill}">{html.escape(str(text))}</text>')

    def paragraph(self,x,y,text,width,size=15,fill=MUTED):
        font=ImageFont.truetype('DejaVuSans.ttf',size);line=''
        for word in text.split():
            if line and font.getlength(line+' '+word)>width:
                self.text(x,y,line,size,fill);y+=size+6;line=word
            else:line=(line+' '+word).strip()
        if line:self.text(x,y,line,size,fill);y+=size+6
        return y

    def line(self,x1,y1,x2,y2,fill=EDGE,width=2,arrow=False):
        self.draw.line((x1,y1,x2,y2),fill=fill,width=width)
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{fill}" stroke-width="{width}"/>')
        if arrow:
            angle=math.atan2(y2-y1,x2-x1)
            for offset in [-.5,.5]:self.line(x2,y2,x2-10*math.cos(angle+offset),y2-10*math.sin(angle+offset),fill,width)

    def tag(self,x,y,text,fill=STATIC):
        font=ImageFont.truetype('DejaVuSans.ttf',14);w=math.ceil(font.getlength(text))+14
        self.rect(x,y,w,26,BG,fill,2);self.text(x+7,y+5,text,14,fill)

    def save(self,out,name):
        for box in self.bounds:assert 0<=box[0]<=box[2]<=self.size[0] and 0<=box[1]<=box[3]<=self.size[1],(name,box,self.size)
        self.image.save(out/(name+'.png'))
        (out/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n')
        return dict(name=name,size=list(self.size),text_bounds=self.bounds,sha256={ext:hashlib.sha256((out/(name+'.'+ext)).read_bytes()).hexdigest() for ext in ('png','svg')})


def board(c,x,y,values,cell=42,move=None,after=None):
    for i,value in enumerate(values):
        row,col=divmod(i,3);px=x+col*cell;py=y+row*cell
        stroke=GREEN if i==move else EDGE
        if after is not None and after!=move and i==after:stroke=RED
        c.rect(px,py,cell,cell,BG,stroke,3 if i in (move,after) else 1)
        c.text(px+cell*.31,py+cell*.2,'.XO'[value],int(cell*.5),RED if value==1 else '#88baff' if value==2 else MUTED)
        if not value:c.text(px+3,py+3,str(i+1),10,MUTED)


def heatmap(c,x,y,values,cell,row_prefix='',col_prefix='',highlights=(),maximum=None,numbers=False):
    maximum=max(abs(float(v)) for row in values for v in row) if maximum is None else maximum
    for col in range(len(values[0])):c.text(x+col*cell+cell*.2,y-19,col_prefix+str(col),11,MUTED)
    for row,line in enumerate(values):
        c.text(x-30,y+row*cell+cell*.3,row_prefix+str(row),11,MUTED)
        for col,value in enumerate(line):
            c.rect(x+col*cell,y+row*cell,cell,cell,color(value,maximum),STATIC if (row,col) in highlights else EDGE,3 if (row,col) in highlights else 1)
            if numbers:c.text(x+col*cell+3,y+row*cell+cell*.35,str(value),10,INK)


def heading(c,title,subtitle):
    c.text(28,22,title,27)
    c.text(28,63,subtitle,16,MUTED)


def render(study,output):
    study=Path(study);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    choices=read(study/'callouts.json');cases=read(study/'cases.json');summary=read(study/'summary.json');spatial=read(study/'spatial.json');symmetry=read(study/'symmetry.json')
    effects={row['id']:row for row in read(study/'interventions.json')}
    model=load(FOUR_MODEL);arrays=np.load(study/'baseline-stages.npz');t=model['tensors']
    assert hashlib.sha256(FOUR_MODEL.read_bytes()).hexdigest()==summary['model_sha256']
    measured_terms=[]
    for case in cases:
        choice=next(v for v in choices if v['callout']==case['callout']);parameter=choice['parameter']
        e,k,u=parameter['coordinates'];exponent=t['expert_w1']['exponents'][e*4+u]
        numerator=case['norm2_output'][k]*parameter['stored_value']
        measured_terms.append(dict(callout=case['callout'],kind=case['kind'],canonical_index=case['canonical_index'],expert=e,hidden_unit=u,input_lane=k,input_value=case['norm2_output'][k],static_code=parameter['stored_value'],exponent=exponent,exact_pre_round_term_numerator=numerator,exact_pre_round_term_denominator=1<<(-exponent),hidden_preactivation=int(arrays['expert_hidden_pre'][case['canonical_index'],e,u]),hidden_activation=case['unit_value'],zero_unit_selected_logit_effect=case['selected_logit_delta']))
    figures=[]
    c=Canvas(1480,1110)
    heading(c,'FALCON-9: measured strategy callout map','Frozen Q11 / W16 / A32 model. STATIC scalar weights | DYNAMIC activations and gates | tested interventions.')
    boxes=[(28,110,310,'Fixed geometry','8 literal permutations'),(385,110,330,'Integer neural model','Attention + routed experts'),(760,110,300,'Predicted complete set','Legal logits >= 0'),(1105,110,345,'Fixed inverse + tie','Original-coordinate choice')]
    for x,y,w,title,detail in boxes:c.rect(x,y,w,62);c.text(x+12,y+10,title,17);c.text(x+12,y+37,detail,14,MUTED)
    for i in range(3):c.line(boxes[i][0]+boxes[i][2]+4,141,boxes[i+1][0]-5,141,INK,2,True)
    c.rect(28,195,710,480,stroke=STATIC)
    c.text(46,211,'STATIC stored parameter maps',20,STATIC)
    for e,x in [(0,85),(1,415)]:
        c.text(x,252,f'Expert {e}: expert_w1[{e}, input, hidden]',15)
        codes=t['expert_w1']['codes'][e].numpy();exponents=np.array(t['expert_w1']['exponents'][e*4:(e+1)*4]);values=(codes*(2.0**exponents)).tolist()
        coord=(1,2) if e==0 else (7,0)
        heatmap(c,x,298,values,35,'i','h',highlights=[coord])
        c.tag(x+152,320 if e==0 else 538,'A1 / B1' if e==0 else 'C1')
        c.line(x+150,333 if e==0 else 551,x+coord[1]*35+18,298+coord[0]*35+18,STATIC,2,True)
    c.paragraph(46,605,'One tile = one static effective scalar (stored code times column scale). Signed colors are normalized separately per tensor. A1 and B1 are the SAME weight, not separate winning/blocking weights.',665,14)
    positive=next(v for v in cases if v['callout']=='C' and v['kind']=='tactical')
    c.rect(760,195,690,480,stroke=DYNAMIC)
    c.text(778,211,f"DYNAMIC fork example: canonical board{positive['canonical_index']}",20,DYNAMIC)
    c.text(810,257,'Computed hidden activations',15)
    hidden=positive['expert_hidden'];scale=max(abs(v) for row in hidden for v in row)
    heatmap(c,820,301,hidden,46,'E','h',maximum=scale)
    for e in range(4):
        if e not in positive['routes']:
            for u in range(4):c.rect(820+u*46,301+e*46,46,46,BG,EDGE);c.text(835+u*46,316+e*46,'-',15,MUTED)
    c.tag(778,351,'C',DYNAMIC);c.line(807,363,837,370,DYNAMIC,2,True)
    board(c,1170,295,positive['board'],cell=61,move=positive['move'],after=positive['after_zero_move'])
    c.text(1146,500,f"Base: square{positive['move']+1} (fork)",16,GREEN)
    c.text(1146,526,f"Zero C: square{positive['after_zero_move']+1} (nonoptimal)",16,RED)
    selected=choices[2]['coordinates'];slot=positive['routes'].index(selected[0])
    c.text(790,513,f"E{selected[0]}.h{selected[1]} = {positive['unit_value']}; gate = {positive['gates_q15'][slot]}/32768",16,DYNAMIC)
    c.text(790,541,f"Zero C changes selected logit by {positive['selected_logit_delta']:+d}",15)
    c.paragraph(790,580,'Dash means NOT ROUTED, not a measured zero. Bright activation is input-dependent; stored weights do not light up or change. Green/red board boxes are recommendations, not played marks.',620,14)
    # Stable callouts, directly bound to exact tensor coordinates and payload offsets.
    for j,choice in enumerate(choices):
        x=28+j*480;y=700;c.rect(x,y,455,295)
        c.tag(x+14,y+14,choice['callout'],DYNAMIC);coord=choice['coordinates'];p=choice['parameter'];r=choice['training_association']
        c.text(x+60,y+20,f'E{coord[0]}.h{coord[1]} / '+{'A':'win availability','B':'must-block','C':'fork opportunity'}[choice['callout']],18)
        c.paragraph(x+16,y+59,f"Exploratory training partial r={r['residual_ply_correlation']:+.3f} after ply centering. Held-out AUC with controls {choice['heldout_unit_probe']['auc']:.3f}; route/control-only {choice['heldout_route_control_probe']['auc']:.3f}.",421,14)
        c.paragraph(x+16,y+137,f"{p['callout']}: {p['tensor']}[{','.join(map(str,p['coordinates']))}], code {p['stored_value']}; tensor scalar {p['flat_index']}, global scalar {p['global_parameter_index']}, byte {p['packet_byte_offset']} (zero-based).",421,14,STATIC)
        e=effects[choice['zero_intervention']]['effects'][choice['task']]
        c.paragraph(x+16,y+215,f"Zero unit: {e['nonoptimal_or_empty']}/{e['n']} target boards become nonoptimal/empty. This is NOT a unique strategy detector; see matched controls and counterexamples.",421,14)
    c.paragraph(30,1024,'A and B select one shared unit. C is behaviorally relevant on a fork board, but its probe does not beat controls and other weights also cause fork errors. Callouts identify measured coordinates, not proven symbolic meanings. Full denominators and matched-control strata are in MODEL_INTERPRETABILITY.md.',1410,15)
    c.text(30,1081,'Signed-value colors: blue negative / dark zero / orange positive. Purple outline: static parameter reference.',12,MUTED)
    figures.append(c.save(out,'strategy-circuit-map'))
    c=Canvas(1480,1130)
    heading(c,'Tactical boards versus matched non-target boards','Same weights; actual production recommendations. Nearest same-ply controls: occupancy-count distance is disclosed.')
    for row,choice in enumerate(choices):
        y=105+row*340;positive=next(v for v in cases if v['callout']==choice['callout'] and v['kind']=='tactical');negative=next(v for v in cases if v['callout']==choice['callout'] and v['kind']=='matched-nontarget')
        c.rect(28,y,1422,318);c.tag(44,y+14,choice['callout'],DYNAMIC)
        c.text(95,y+18,{'A':'Immediate winning move','B':'Blocking an immediate threat','C':'Creating a double threat / fork'}[choice['callout']],21)
        for n,case in enumerate([positive,negative]):
            x=50+n*685;c.text(x,y+58,f"{'TACTICAL' if n==0 else 'NON-TARGET'} / board{case['canonical_index']} / {case['probe_split']}"+(f" / count-distance {case['occupancy_control_L1_distance']:g}" if n else ''),14,MUTED)
            board(c,x,y+90,case['board'],cell=43,move=case['move'],after=case['after_zero_move'])
            sx=x+153;c.text(sx,y+91,f"Base square{case['move']+1}; zero unit -> "+(str(case['after_zero_move']+1) if case['after_zero_move']>=0 else 'NO RESULT'),17,GREEN if case['after_zero_optimal'] else RED)
            c.text(sx,y+121,f"E{choice['coordinates'][0]}.h{choice['coordinates'][1]} activation = {case['unit_value']}",17,DYNAMIC)
            gates=', '.join(f'E{e}:{g}/32768' for e,g in zip(case['routes'],case['gates_q15']))
            c.text(sx,y+151,'Gates '+gates,14,MUTED)
            c.text(sx,y+179,f"Zero-unit effect on selected logit: {case['selected_logit_delta']:+d}",15)
            term=next(v for v in measured_terms if v['callout']==choice['callout'] and v['kind']==case['kind'])
            c.paragraph(sx,y+211,f"{choice['parameter']['callout']} input lane{term['input_lane']}={term['input_value']}; static code {term['static_code']}. Exact incoming term before whole-dot rounding: {term['exact_pre_round_term_numerator']}/{term['exact_pre_round_term_denominator']}.",490,13,STATIC)
        note='Higher activation on the non-winning control; tiny E0 gate limits the effect. Not a winning-neuron detector.' if row==0 else 'The same E0.h2 unit is also ranked for winning availability: shared, weakly associated behavior, not a dedicated blocker.' if row==1 else 'A real decision flip: removing C loses this fork choice. Non-fork effects and comparable control-weight damage prevent a unique fork-detector claim.'
        c.paragraph(48,y+277,note,1380,14)
    figures.append(c.save(out,'strategy-board-comparisons'))
    c=Canvas(1480,1150)
    heading(c,'Fixed symmetry wrapper versus learned positional structure','Geometry is literal code/data, not learned layers. Position and attention measurements are separate, input-dependent evidence.')
    c.text(30,108,'Eight FIXED geometry permutations (G0..G7)',20)
    source=next(v for v in cases if v['callout']=='C' and v['kind']=='tactical')['board']
    for i,tform in enumerate(TRANSFORMS):
        x=35+(i%4)*188;y=155+(i//4)*190;c.text(x,y-24,f'G{i}',15,INK)
        board(c,x,y,transform_board(source,tform),cell=41)
        c.text(x,y+132,','.join(str(k+1) for k in tform[:5])+'...',10,MUTED)
    c.paragraph(32,555,f"{symmetry['board_transform_set_roundtrips']} board/set roundtrips passed across4520 boards. Complete move sets are equivariant. Fixed original-coordinate tie order is not: {symmetry['tie_choice_nonequivariant_examples']} transform/board pairs choose a different tied representative.",728,16)
    c.rect(800,105,650,510,stroke=STATIC);c.text(820,122,'STATIC position[9,8] / Q11 offsets',20,STATIC)
    pc=spatial['coordinates'];heatmap(c,854,180,spatial['position_values'],36,'s','c',highlights=[tuple(pc)],numbers=True)
    c.tag(1190,325,'P1')  # Exact row/column highlight; do not cross printed values.
    c.paragraph(820,526,f"P1 = position[{pc[0]},{pc[1]}], code {spatial['stored_value']}, scalar{spatial['flat_index']}, byte{spatial['packet_byte_offset']}. Constant offset, NOT a rotate/reflect parameter. Embedding/center association r={spatial['training_association']['residual_ply_correlation']:+.3f} includes occupancy and side sums.",603,14)
    c.rect(28,675,715,410,stroke=DYNAMIC);c.text(48,693,'DYNAMIC attention probabilities / winning board595',20,DYNAMIC)
    attention=next(v for v in cases if v['callout']=='A' and v['kind']=='tactical')['attention_probs_q15'];edge=tuple(map(int,spatial['attention_association']['coordinates'].split(',')))
    heatmap(c,87,750,attention,29,'q','k',highlights=[edge],maximum=32768)
    c.tag(382,934,'T1',DYNAMIC);c.line(381,947,87+edge[1]*29+14,750+edge[0]*29+14,DYNAMIC,2,True)
    c.paragraph(390,753,f"T1 = attention_probs[{edge[0]},{edge[1]}]. Q15, row sums32768. Actual value here: {attention[edge[0]][edge[1]]}/32768. Training win-availability association r={spatial['attention_association']['residual_ply_correlation']:+.3f}: weak and exploratory, not a learned geometry operation.",323,15)
    c.rect(800,675,650,410);c.text(820,693,'Position intervention is broad, not a transform circuit',19)
    py=737
    for name in ['P1-half','P1-zero','P1-control-zero']:
        effect=effects[name]['effects']['all'];c.text(820,py,name,16,STATIC)
        c.text(820,py+27,f"Nonoptimal/empty {effect['nonoptimal_or_empty']}/4520; routes changed {effect['route_changes']}/4520",15)
        py+=79
    c.paragraph(820,991,'Rerouting confounds a downstream-only interpretation. Zeroing P1 changes model behavior but does not change any wrapper permutation. No raw noncanonical model experiment is claimed.',598,15)
    figures.append(c.save(out,'symmetry-position-map'))
    metadata=dict(schema='measured-strategy-maps-v1',weights_are_static=True,activations_and_gates_are_input_dependent=True,model_sha256=summary['model_sha256'],renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),study_summary_sha256=hashlib.sha256((study/'summary.json').read_bytes()).hexdigest(),callout_ids=['A','B','C','A1','B1','C1','P1','T1'],callouts=choices,spatial=spatial,measured_incoming_terms=measured_terms,figures=figures,normalization='Static tensors separately normalized by max effective scalar; dynamic pair comparisons use actual raw integer values. Attention uses fixed Q15 0..32768. Colors are not strategy labels.',semantic_limit='Exploratory associations and tested intervention effects, not unique detector/circuit identification; no game HUD or release modification.')
    (out/'maps.json').write_text(json.dumps(metadata,separators=(',',':'))+'\n')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();metadata=render(args.study,args.output);print('rendered',len(metadata['figures']),'PNG/SVG pairs')
