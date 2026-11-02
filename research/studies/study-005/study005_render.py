"""005 evidence-only renderer using installed Pillow, no installs/matplotlib."""
from pathlib import Path
import json,hashlib
import numpy as np
from scripts.render_strategy_maps import Canvas,INK,MUTED,DYNAMIC,GREEN,RED,EDGE,BG,color

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def board(c,x,y,b,s):
    for col in range(3):c.text(x+col*42+12,y-20,'ABC'[col],13,MUTED)
    for row in range(3):c.text(x-15,y+row*42+12,str(row+1),13,MUTED)
    for k,v in enumerate(b):
        xx=x+(k%3)*42;yy=y+(k//3)*42;c.rect(xx,yy,42,42,BG,GREEN if k==s else EDGE,3 if k==s else 1);c.text(xx+13,yy+7,'.XO'[v],23,INK)

def heat(c,x,y,p,size=27):
    for k in range(9):c.text(x+k*size+7,y-19,str(k),11,MUTED)
    for q in range(9):
        c.text(x-18,y+q*size+7,str(q),11,MUTED)
        for k in range(9):c.rect(x+k*size,y+q*size,size,size,color(p[q][k],32768),EDGE,1)

def render(out):
    out=Path(out);read=lambda n:json.loads((out/n).read_text());d=read('descriptive005.json');rs=read('interventions005.json');ex=read('examples005.json');base=read('baseline-vectors005.json');figs=[]
    c=Canvas(1720,1080)
    c.text(28,20,'Study005 / input-sensitive attention, not an established strategy detector',26)
    c.text(28,61,'Measured actual model on627 canonical boards; perturbations are isolated upstream OOD overrides, never deployed behavior.',16,MUTED)
    c.rect(24,102,760,430);c.text(42,120,'A / actual attention distribution',22,DYNAMIC)
    c.text(42,162,f"Row entropy mean {d['row_entropy_bits']['mean']:.4f} / {d['row_entropy_bits']['uniform_max']:.4f} bits",19)
    c.text(42,194,f"Range {d['row_entropy_bits']['min']:.4f} to {d['row_entropy_bits']['max']:.4f}; effective keys mean {d['effective_keys_mean']:.3f}",18)
    c.text(42,225,f"Zero edges {100*d['zero_fraction']:.2f}%; mean row maximum P {d['row_max_probability']['mean']:.4f}",18)
    p=np.array(base['stages']['attention_probs'],dtype=float)/32768;h=-(np.where(p>0,p*np.log2(np.maximum(p,1e-300)),0)).sum(-1);counts,edges=np.histogram(h,bins=np.linspace(0,np.log2(9),9));maxn=int(counts.max())
    for j,n in enumerate(counts):
        xx=52+j*84;hh=int(n/maxn*135);c.rect(xx,438-hh,60,hh,DYNAMIC,EDGE);c.text(xx,448,f'{edges[j]:.1f}',12,MUTED);c.text(xx,438-hh-21,str(n),12)
    c.text(42,485,'Actual row entropy (bits); counts across5643 query rows',16,MUTED)
    c.rect(24,550,760,475);c.text(42,568,'B / position and occupancy controls',22,DYNAMIC)
    c.paragraph(42,612,'Local Q/K/V are exactly determined by square, local occupancy and side: within-ply/square/own-opponent occupancy MSE =0. This is architectural locality, NOT a whole-board tactical detector.',704,19)
    c.paragraph(42,731,f"Actual P still varies across boards in fixed ply/query/key/own-opponent occupancy strata: within-MSE {d['edge_variation_controlled_ply_q_k_own_opponent']['within_mse']:,.1f} (Q15 squared). Normalization depends on all keys; actual P times V and projection also depend on input.",704,19)
    c.paragraph(42,881,'All query rows feed a flattened global readout plus residual. Query q is NOT output square q. Legal occupied masking and final full-set inverse/tie rules are external and not learned.',704,19)
    c.rect(808,102,888,923);c.text(829,120,'C / all19 fixed interventions, including unfavorable controls',21,DYNAMIC)
    c.text(829,158,'Bars: canonical wrong/empty move /627. Blue dots: changed route order.',15,MUTED)
    x0=1190;scale=460/627
    for j,r in enumerate(rs):
        yy=202+j*35;c.text(828,yy,r['id'],13)
        err=r['canonical']['move_errors'];rc=r['route_order_changes'];c.rect(x0,yy,err*scale,18,RED,RED);c.text(x0+err*scale+5,yy,str(err),12)
        xx=x0+rc*scale;c.rect(xx-2,yy+23,5,5,'#68b8ec','#68b8ec')
    c.paragraph(829,898,'Identity/no-op has exact all-stage parity. Group controls move equal per-row mass over equally many disjoint edges, but may affect other lines. Substantial control damage prevents a dedicated line-circuit conclusion.',837,17)
    c.text(28,1043,'Selection folds372/121/134 are NOT model-heldout. Full-set logits are candidate membership scores, not probabilities.',17,MUTED)
    figs.append(c.save(out,'attention-overview005'))
    c=Canvas(1720,1190);c.text(28,20,'Study005 / actual board contrasts and their explicit coordinate alignment',25)
    c.text(28,61,'Each legal single-mark relocation preserves ply and own/opponent corner-edge-center counts. No activation transplantation.',16,MUTED)
    for row,item in enumerate(ex['examples'][:2]):
        r=item['match'];yy=106+row*438;c.rect(24,yy,1672,416);s=r['candidate'];ss=r['donor_candidate'];i=r['receiver'];j=r['donor'];t=r['donor_raw_to_canonical']
        display='matched test threat' if row==0 else 'PV/P ratio counterexample (P is NOT small)'
        c.text(42,yy+15,f"{chr(65+row)} / {display} / {r['task']} / fold{r['fold']} / canonical IDs {i} vs {j}",20,DYNAMIC)
        c.text(56,yy+54,'Receiver raw',16);c.text(231,yy+54,'Donor raw',16)
        board(c,64,yy+99,r['receiver_raw'],s);board(c,242,yy+99,r['donor_raw'],s)
        c.text(42,yy+246,f"Raw candidate {s} = {'ABC'[s%3]}{s//3+1}; canonical {s} -> {ss}",14,GREEN)
        c.text(42,yy+275,f"Move mark {r['mark']}: raw {r['from_square']} -> {r['to_square']}",14)
        c.paragraph(42,yy+307,f"Receiver raw→canonical identity; donor raw→canonical {t}. Actual receiver/donor logits {item['receiver_logit']} / {item['donor_logit']}.",380,14)
        c.text(456,yy+55,'Actual receiver P[q,k]',16);heat(c,464,yy+99,item['receiver_actual_p'],25)
        c.text(464,yy+340,'q query (down); k key (right)',13,MUTED)
        c.text(752,yy+55,'Actual donor P aligned to raw',16);heat(c,760,yy+99,item['donor_actual_p_aligned'],25)
        c.text(760,yy+340,'Both axes indexed by donor transform',13,MUTED)
        c.text(1044,yy+55,'Measured differences / not attention pictures alone',16,DYNAMIC)
        for k,text in enumerate([f"Aligned P L1: {r['aligned_attention_l1']}/32768",f"Aligned actual V L1: {r['aligned_value_l1']:,}",f"Actual P*V numerator L1: {r['actual_weighted_pv_numerator_l1']:,}",f"Aligned projection L1: {r['aligned_projection_l1']:,}",f"Natural route changed: {r['route_changed']}; gate L∞ {r['gate_linf']}",f"Training-line target lesion set: {item['target_lesion_set']}",f"Equal-mass control lesion set: {item['control_lesion_set']}"]):c.text(1044,yy+94+k*35,text,15)
        c.text(1044,yy+353,'Lesion sets are counterfactual, NOT actual attention.',14,RED)
    c.rect(24,1000,1672,149);counter=ex['unfavorable_control'];c.text(42,1018,'C / retained unfavorable control counterexample',20,DYNAMIC)
    c.paragraph(42,1057,f"{counter}. Empty perturbed set is failure, not selective tactical evidence. All array coordinates0..8 row-major; A-C columns/1-3 rows; green outlines denote the candidate, not preference.",1620,16)
    c.text(28,1162,'P colors share absolute0..1 scale: dark0, orange1. Actual Q/K/V and projected vectors remain in baseline-vectors005.json.',15,MUTED)
    figs.append(c.save(out,'attention-contrasts005'))
    meta=dict(figures=figs,input_sha256={n:sha(out/n) for n in ['examples005.json','baseline-vectors005.json','descriptive005.json','interventions005.json']},renderer_sha256=sha(__file__),canvas_sha256=sha(Path(__file__).parent/'scripts/render_strategy_maps.py'),coordinates='Zero-based row-major raw/canonical. Donor both P axes transformed to receiver raw; receiver identity. A-C columns1-3 rows. Actual unmodified P only; common absolute0..1 scale.',callouts={str(i):item['match'] for i,item in enumerate(ex['examples'])},scope='Host evidence figures; no game screenshot or removed-edge-as-actual map')
    (out/'figure-metadata005.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')

def corrected_report(out,original):
    original(out);p=Path(out)/'REPORT005.md';text=p.read_text()
    text=text.replace('Actual attention is broad:','Actual attention is heterogeneous and often concentrated:').replace('probabilities are broad;','probabilities vary in concentration;')
    text=text.replace('`python study005_run.py run --output <fresh005-directory>`','`python study005_execute.py --output <fresh005-directory>`')
    text=text.replace('Small probability changes can coexist with substantial value/projection differences.','Probability and value/projection changes must be compared separately; the largest PV/P-ratio example does NOT have small absolute P change. There is no uniformly weak-variation finding.')
    read=lambda n:json.loads((Path(out)/n).read_text())
    selected=read('training-selection005.json')['selected'];records=read('candidate-probes005.json')['records'];interventions={r['id']:r for r in read('interventions005.json')}
    auc=lambda task,feature:next(r['auc'] for r in records if r['task']==task and r['fold']==2 and r['feature']==feature)
    details='; '.join(f"{task} {auc(task,'controls'):.5f} -> {auc(task,'controls_plus_attention_rowcol'):.5f}" for task in ('win','threat','fork'))
    text+=f"\n## Measured positive and negative interpretation\nTraining-only selected line {selected['line']} had positive-minus-negative line mass contrast {selected['mean_candidate_line_mass_contrast']:.6f}; a negative contrast is not a bright-line support detector. Test candidate AUC controls -> controls+attention: {details}; unfavorable controls retained. Position-mean attention causes{interventions['position-mean']['canonical']['move_errors']}/627 canonical selected-move failures ({interventions['position-mean']['route_order_changes']} route-order changes). Selected-line full-dose lesion: {interventions['training-line-target-2of2']['canonical']['move_errors']} failures vs equal-size/equal-mass control {interventions['training-line-control-2of2']['canonical']['move_errors']}; not selective strategic-circuit evidence.\n"
    text+='\n## Execution repairs (no design change)\nThe first attempt stopped before interventions on NumPy JSON scalar serialization. A wrapper converts only NumPy scalars/arrays to JSON. All19 interventions then executed; the environment lacked matplotlib. No packages were installed: a Pillow/Canvas evidence-only renderer replaces the unavailable renderer. Frozen experiment source and manifest remain byte-identical; amendment-study005.json binds the execution/renderer repair. Original partial attempts retained separately. Concentration wording is generated to match actual entropy, not the unused generic broad-attention hypothesis.\n'
    p.write_text(text)
