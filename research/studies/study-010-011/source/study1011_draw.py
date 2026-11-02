"""PNG+native selectable-text SVG using existing Pillow; no install."""
import json,textwrap
from pathlib import Path
import numpy as np
from study009_render import Canvas
from study1011_run import put
BLUE='#2061a6';GREEN='#248553';RED='#bc432f'
def load(p):return json.loads(Path(p).read_text())
def letters(ss):return ''.join(chr(97+int(s)) for s in ss) or 'EMPTY'
def text(c,x,y,lines,size=22,gap=31,mono=False,color='#17283f'):
    if isinstance(lines,str):lines=lines.split('\n')
    for j,line in enumerate(lines):c.text(x,y+j*gap,line,size,color,mono)
    return y+len(lines)*gap
def board(c,x,y,b,members=(),expected=None,cell=64):
    members=set(members);expected=set(expected) if expected is not None else members
    for s,v in enumerate(b):
        xx=x+s%3*cell;yy=y+s//3*cell
        fill='#d9ebfb' if s in members else '#ffffff'
        if s in members and s not in expected:fill='#f6d3cc'
        c.rect(xx,yy,cell,cell,fill,GREEN if s in expected else '#bbc8d4')
        c.text(xx+5,yy+3,chr(97+s),14,color='#687785');c.text(xx+cell*.38,yy+cell*.3,'.XO'[v],int(cell*.4))
def save(c,d,name):return c.save(Path(d),name)
def render010(d):
    d=Path(d);r=load(d/'results010.json');ex=load(d/'examples010.json');c=Canvas(1400,920)
    text(c,32,20,['Research010 | Learned network versus fixed wrapper'],32)
    text(c,32,77,['Same frozen integer model; only the orientation path changes.'],24)
    c.rect(28,130,650,485);c.rect(700,130,670,485)
    text(c,48,146,['A  Complete legal sets, not just one move'],25)
    for y,n,label,col in [(240,1514,'Direct network, off-contract orientations',BLUE),(410,4520,'Unchanged canonicalizing wrapper',GREEN)]:
        text(c,48,y-44,[label],22);c.rect(48,y,575*n/4520,49,col,col);text(c,48,y+65,[f'{n:,} / 4,520 unique raw boards'],25,color=col)
    text(c,720,146,['B  All eight transformations'],25)
    text(c,720,196,['      full set    chosen optimal    exact logits'],19,mono=True)
    for j,z in enumerate(r['per_transform']):
        text(c,720,241+j*40,[f"T{j}     {z['full_set_correct']:3}/627        {z['chosen_optimal']:3}/627          {z['exact_aligned_logit_boards']:3}/627"],19,mono=True)
    text(c,32,655,['C  The direct path has 485 empty sets + 1,151 nonoptimal nonempty choices.',
        '345 different but optimal tie choices are not errors. Full-set changes: 3,006 / 4,520.',
        'Only 14 / 627 canonical boards keep the exact set under every direct D4 orientation.',
        '5,016 orbit observations reuse 4,520 inputs; stabilizers are not independent evidence.'],23,gap=42)
    text(c,32,838,['Off-contract diagnostic, not a shipping-game failure; no learned hidden-invariance or new target-speed claim.'],20)
    m1=save(c,d,'overview010')
    c=Canvas(1400,1140);text(c,30,18,['One real board | Eight transforms | Canonical ID1'],31)
    text(c,30,67,['Blue fill = NN member; red fill = false member; green border = wrapper optimal member.'],21)
    for k,e in enumerate(ex):
        col=k%4;row=k//4;x=25+col*346;y=120+row*450
        c.rect(x,y,330,420);text(c,x+12,y+12,[f"{e['callout']}  T{k}   raw {e['raw_id']}"],23)
        board(c,x+65,y+58,e['board'],e['direct_legal_set'],e['wrapper_legal_set'],cell=65)
        text(c,x+12,y+270,[f"NN set {{{letters(e['direct_legal_set'])}}}",f"wrapper {{{letters(e['wrapper_legal_set'])}}}",f"experts {e['routes']}",f"Q15 gates {e['gates']}"],19,gap=32)
    text(c,30,1043,['Repeated raw IDs are identical inputs. A zero gate is executed, not inactive.',
        'T1/T4: NN chooses i with X on g; fixed wrapper chooses e. Full vectors: examples010.json.'],21,gap=33)
    m2=save(c,d,'orbits010')
    put(d/'figure-metadata010.json',dict(figures=[m1,m2],canonical_id=1,callouts={e['callout']:dict(transform=e['transform_id'],raw_id=e['raw_id']) for e in ex},spatial_axes='Both query/key axes; square feature rows; NO latent-unit permutation',render='Pillow DejaVu TrueType + native SVG selectable text'))

def render011(d):
    d=Path(d);rows=load(d/'results011.json');ex=load(d/'examples011.json');c=Canvas(1400,1370)
    text(c,30,20,['Research011 | Exact classes are not strategic meaning'],31)
    text(c,30,78,['A  Distinct full integer vectors / 627 canonical boards. No projection or trained decoder.'],22)
    x=570;scale=700/627
    for j,r in enumerate(rows):
        y=132+j*40;name=r['stage'].replace('board_','').replace('executed_expert_','executed experts: ')
        text(c,30,y,[name],22);n=r['distinct_classes'];col=GREEN if n==627 else BLUE
        c.rect(x,y+1,max(4,n*scale),27,col,col);text(c,x+n*scale+12,y-2,[str(n)],21,color=col)
    text(c,30,1160,['B  Routes: 12 ordered classes (6 unordered). Routes + exact Q15 gates: 480.',
        'C  Full merged vectors and integer logits: 627 distinct, despite coarse routing metadata.',
        'D  Legal sign sets: 118. Different boards can legitimately need identical optimal moves.',
        'Green = injective only on this finite census; NOT semantic decoding or causal strategy use.'],22,gap=40)
    m1=save(c,d,'cardinality011')
    pair=next(e for e in ex if e['stage']=='pair_and_gates' and e['reason']=='controlled-different-tactic')
    mask=next(e for e in ex if e['stage']=='unmasked_signs' and e['reason']=='controlled-different-optimal-set')
    c=Canvas(1400,1090);text(c,30,20,['Exact collisions | What routing and signs do not tell you'],30)
    text(c,30,76,['Actual boards; blue fill and green borders = complete optimal legal sets, not a preference.'],21)
    for row,e in enumerate((pair,mask)):
        y=132+row*410
        for col,i in enumerate(e['canonical_ids']):
            x=30+col*315;text(c,x,y,[f"{'ABCD'[row*2+col]}  Canonical {i}"],24)
            board(c,x,y+49,e['boards'][col],e['optimal_sets'][col],cell=75)
            text(c,x,y+295,[f"set {{{letters(e['optimal_sets'][col])}}}",f"route {e['routes'][col]}",f"gates {e['gates'][col]}"],19,gap=30)
        if row==0:
            lines=['Same exact routing metadata:', '[3, 0, 32768, 0]', '', 'Same ply / side / geometry and legal mask.',
                   '452: opponent fork + prevention', '413: one immediate opponent threat', '',
                   'Distinct expert activity, merged values and logits.', 'Expert0 executes at zero gate; inactive is null.',
                   'No tactical-detector name follows from this.']
        else:
            lines=['Same unmasked sign vector:', '[+, +, +, +, +, +, +, +, +]', '', 'Same ply / side / geometry counts.',
                   'Occupied squares differ; external masks differ.', '299 legal set {abcdeh}; 524 {abefgh}.', '',
                   'The full integer logits are NOT identical.', 'No full-logit collision on all 627 boards.', 'Sign equality is weaker than logit equality.']
        text(c,675,y+8,lines,22,gap=33)
    text(c,30,1000,['Geometry controls: own/opponent corner, edge, center counts. Tactical labels describe geometry;',
        'an immediate threat need not have one uniquely saving block on an already lost board. Exact data: examples011.json.'],20,gap=32)
    m2=save(c,d,'collisions011')
    put(d/'figure-metadata011.json',dict(figures=[m1,m2],callouts={'A':452,'B':413,'C':299,'D':524},no_projection_proof=True))

def draw_walkthrough(out,a,t):
    out=Path(out);i=t['canonical_id'];p=t['static_parameter_snippets'];c=Canvas(1400,1110)
    text(c,30,18,['One actual frozen forward | 1 / 2 | Input → attention → readout'],31)
    text(c,30,77,['Stored parameter codes are STATIC. All measured activations on this board are DYNAMIC.'],22)
    text(c,30,133,[f'A  Canonical board {i}'],24);board(c,30,181,t['board'],t['legal_set'],cell=75)
    text(c,30,425,[f"side index {t['side_embedding_index']}",f"complete set {{{letters(t['legal_set'])}}}"],22)
    text(c,370,133,['B  One exact embedding sum, query square e'],25)
    lines=[f"occupancy code: {p['occupancy_code']}",f"position code:  {p['position_code']}",f"side code:      {p['side_code']}",'',f"dynamic sum:   {t['embedding']}",'',
           'Integer norm1 → learned Q / K / V on all nine tokens.', 'Eight lanes are latent dimensions, not eight other squares.']
    text(c,370,188,lines,19,gap=35,mono=True)
    text(c,30,544,['C  Q15 attention (query rows / key cols)'],22)
    probs=a['attention_probs'][i];cell=39;x0=70;y0=608
    for k in range(9):text(c,x0+k*cell+12,y0-30,[chr(97+k)],18)
    for q in range(9):
        text(c,32,y0+q*cell+8,[chr(97+q)],18)
        for k in range(9):
            v=float(probs[q,k]/32768);rgb=tuple(int(244-v*(244-c0)) for c0 in (32,97,166));col='#%02x%02x%02x'%rgb
            c.rect(x0+k*cell,y0+q*cell,cell,cell,col,'#b8c6d4')
    text(c,30,993,['White 0 → dark blue 1; every row sums to 32768.'],19)
    text(c,530,544,['D  Exact query e audit and global readout'],25)
    lines=[f"Q[e] · K[a] = {t['query_key0_dot']}",f"Q15 row sum = {sum(t['attention_q15'])}",f"P[e] × V numerator, lane0 = {t['weighted_value_numerator'][0]}",f"round(numerator / 32768) = {t['attended'][0]}",'',
        'Then learned projection + residual → global 72→8 readout.', 'Query e is NOT the output square e.', 'Attention mass is NOT move confidence.', '',
        'All 21 stages retained in baseline011.npz.', 'Exact sample vectors/parameter snippets: walkthrough1011.json.']
    text(c,530,600,lines,22,gap=36)
    text(c,30,1055,['A→B→C→D labels follow actual computation. No tactic label or minimax output enters inference.'],21)
    m1=save(c,out,'forward-attention1011')
    c=Canvas(1400,1190);text(c,30,18,['One actual frozen forward | 2 / 2 | Routed experts → head → wrapper'],29)
    text(c,30,76,['E/F/G: learned integer computation. H: fixed masking, inverse coordinates and raw-board tie priority.'],21)
    for x,y in ((25,127),(710,127),(25,620),(710,620)):c.rect(x,y,660,467)
    text(c,42,144,['E  Actual dynamic routing and execution'],25)
    lines=[f"scores {t['router_scores']}",f"ordered expert IDs {t['routes']}",f"matching Q15 gates {t['gates']}",'',
           f"E{t['routes'][0]} hidden {t['expert_hidden'][0]}",f"E{t['routes'][1]} hidden {t['expert_hidden'][1]}",'',
           'Other expert activations: null / unobserved.', 'A selected zero-gate expert still executes.', 'These expert IDs do not uniquely name a tactic.']
    text(c,42,195,lines,20,gap=35)
    text(c,727,144,['F  Exact merge, lane0 (all lanes retained)'],25)
    u=t['expert_outputs'];g=t['gates'];n=t['weighted_expert_numerator'][0]
    lines=[f"E{t['routes'][0]} {u[0][0]} × gate {g[0]}",f"+ E{t['routes'][1]} {u[1][0]} × gate {g[1]}",f"= weighted numerator {n}",'',
        f"readout lane0 {t['readout_gelu'][0]}",f"+ round({n} / 32768)",f"= merged lane0 {t['merged'][0]}",'', 'Both expert outputs feed the merge, then the head.', 'Exact rounding/clamps belong to the contract.']
    text(c,727,195,lines,21,gap=35)
    text(c,42,637,[f"G  Output row {chr(97+t['head_square'])}: static × dynamic"],25)
    row=str(p['output_row']);parts=textwrap.wrap('stored row codes '+row,51)
    lines=parts+[f"row exponent {p['output_exponent']}; native bias {p['output_bias']}",'',
        f"Σ stored code × merged = {t['head_dot']}",f"scaled/rounded dot = {t['head_scaled']}",f"+ bias = logit {t['logits'][t['head_square']]}",'',
        'One signed membership score, NOT probability.', 'All eight lanes contribute; all nine rows checked.']
    text(c,42,689,lines,20,gap=34)
    text(c,727,637,['H  Integer logits → legal set → fixed tie'],25)
    text(c,727,684,['sq    score       empty?   member'],19,mono=True)
    for s,y in enumerate(t['logits']):
        legal=t['legal_mask'][s];text(c,727,719+s*27,[f"{chr(97+s)} {y:>10}      {'yes' if legal else 'no ':3}      {'IN' if legal and y>=0 else 'out'}"],19,mono=True)
    text(c,727,983,[f"Set {{{letters(t['legal_set'])}}}; ebdfhcgia → {chr(97+t['chosen'])}",'Inverse-map WHOLE set before raw ties,', 'never rotate one already chosen move.'],20,gap=28)
    text(c,30,1120,['Numerical execution is not semantic attribution. No “block/fork expert” claim without selective evidence.'],21)
    m2=save(c,out,'forward-experts1011')
    put(out/'figure-metadata-walkthrough1011.json',dict(figures=[m1,m2],canonical_id=i,callouts=list('ABCDEFGH'),fixed_vs_learned=True,static_vs_dynamic=True,attention_query_is_not_output_square=True,exact_head_scalar_checks=9,embedding_scalar_checks=8,weighted_value_scalar_checks=8,merged_scalar_checks=8))
