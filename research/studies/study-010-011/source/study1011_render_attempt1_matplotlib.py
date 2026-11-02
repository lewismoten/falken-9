"""Measured, deterministic SVG/PNG illustrations and portable research reports."""
import argparse,json,hashlib,copy,textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from study1011_run import put,PRIORITY,TACTICS
ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'study1011','axes.spines.top':False,'axes.spines.right':False})
BLUE='#2061a6';GREEN='#248553';RED='#bc432f';INK='#182b3e'
def load(p):return json.loads(Path(p).read_text())
def save(fig,d,name):
    fig.savefig(Path(d)/(name+'.png'),dpi=140,facecolor='white')
    fig.savefig(Path(d)/(name+'.svg'),metadata={'Date':None},facecolor='white');plt.close(fig)
def board(ax,b,members=(),expected=None,title='',footer=''):
    b=list(b);members=set(members);expected=set(expected) if expected is not None else members
    ax.set_xlim(-.05,3.05);ax.set_ylim(3.08,-.1);ax.set_aspect('equal');ax.axis('off');ax.set_title(title,fontsize=12,fontweight='bold',loc='left',pad=10)
    for s,x in enumerate(b):
        y,z=divmod(s,3);face='#d9ebfb' if s in members else '#f2f4f6';edge=GREEN if s in expected else '#9da8b2'
        if s in members and s not in expected:face='#f6d3cc'
        ax.add_patch(Rectangle((z,y),1,1,facecolor=face,edgecolor=edge,linewidth=3 if s in expected else 1))
        ax.text(z+.5,y+.51,('.','X','O')[x],ha='center',va='center',fontsize=23,color=INK,fontweight='bold')
        ax.text(z+.09,y+.2,chr(97+s),fontsize=9,color='#596777')
    if footer:ax.text(0,-.09,footer,transform=ax.transAxes,va='top',fontsize=9.5,linespacing=1.45)
def letters(ss):return ''.join(chr(97+int(s)) for s in ss) or 'EMPTY'
def render010(d):
    d=Path(d);r=load(d/'results010.json');ex=load(d/'examples010.json');rows=r['per_transform']
    fig,axs=plt.subplots(1,2,figsize=(12,5.8));fig.subplots_adjust(left=.09,right=.97,top=.8,bottom=.22,wspace=.32)
    ax=axs[0];counts=[r['unique_direct']['full_set_correct'],r['wrapper']['full_sets_correct']]
    ax.bar(['Direct network\nOFF-CONTRACT orientations','Fixed canonicalizing\nwrapper'],counts,color=[BLUE,GREEN],width=.58);ax.set_ylim(0,5050);ax.set_ylabel('Exact complete legal sets / 4,520 unique raw boards')
    for i,n in enumerate(counts):ax.text(i,n+100,str(n),ha='center',fontweight='bold')
    ax.set_title('A  Correct set membership',loc='left',fontweight='bold')
    ax=axs[1];x=np.arange(8);ax.bar(x-.18,[z['full_set_correct'] for z in rows],width=.36,label='Complete set correct',color=BLUE);ax.bar(x+.18,[z['chosen_optimal'] for z in rows],width=.36,label='Chosen move optimal',color='#8dadd0');ax.set_xticks(x,[f'T{i}' for i in x]);ax.set_ylim(0,680);ax.set_ylabel('Boards / 627 canonical-board orbits');ax.legend(loc='upper right',fontsize=9);ax.set_title('B  Set accuracy is stricter than one move',loc='left',fontweight='bold')
    fig.suptitle('Research010 — symmetry comes from the whole system',fontsize=18,fontweight='bold',y=.97)
    fig.text(.06,.87,'Frozen network + exact integer arithmetic; only the input orientation path changes.',fontsize=12)
    fig.text(.06,.1,f"C  Direct path: {r['unique_direct']['empty_sets']} empty sets; {r['unique_direct']['nonoptimal_nonempty']} nonoptimal nonempty choices; " + f"{r['unique_direct']['optimal_tie_changes']} different but optimal tie choices.\n5,016 orbit observations reuse 4,520 inputs (stabilizers). These are NOT 5,016 independent boards.\nWrapper is a composed proof using saved target-verified logits; no new target-speed or OOD-performance claim.",fontsize=10.5,linespacing=1.5)
    save(fig,d,'overview010')
    fig,axs=plt.subplots(2,4,figsize=(12,9));fig.subplots_adjust(left=.04,right=.98,top=.86,bottom=.2,wspace=.27,hspace=.75)
    for ax,e in zip(axs.ravel(),ex):
        footer=f"raw {e['raw_id']} · NN {{{letters(e['direct_legal_set'])}}}\nwrapper {{{letters(e['wrapper_legal_set'])}}} · NN move {letters([e['direct_chosen']]) if e['direct_chosen']>=0 else 'EMPTY'}\nexperts {e['routes']} · gates {e['gates']}"
        board(ax,e['board'],e['direct_legal_set'],e['wrapper_legal_set'],f"{e['callout']}  T{e['transform_id']}",footer)
    fig.suptitle(f"One real board, eight coordinate transforms (canonical ID {ex[0]['canonical_id']})",fontsize=17,fontweight='bold',y=.97)
    fig.text(.04,.9,'Blue fill = NN member; red fill = false member; green border = wrapper optimal member. Letters are raw squares.',fontsize=10.5)
    fig.text(.04,.075,'The repeated raw IDs are identical network inputs, not extra evidence. T0 is canonical.\nT1 and T4 put X on g: direct NN selects i, while the unchanged wrapper selects e.\nT0 executes expert0 even though its gate is exactly zero. Inactive experts are null, not measured zero.\nAll logits, legal masks, permutations, gates and expert vectors: examples010.json / measurements010.npz.',fontsize=10.5,linespacing=1.5)
    save(fig,d,'orbits010')
    put(d/'figure-metadata010.json',dict(figures=['overview010','orbits010'],canonical_id=ex[0]['canonical_id'],callouts={e['callout']:dict(transform=e['transform_id'],raw_id=e['raw_id']) for e in ex},spatial_axes='query/key both axes; square feature rows only; no latent/expert-unit permutation',render='TrueType DejaVu Sans; SVG selectable text; PNG140dpi'))

def render011(d):
    d=Path(d);rows=load(d/'results011.json');ex=load(d/'examples011.json')
    fig,ax=plt.subplots(figsize=(12,10));fig.subplots_adjust(left=.3,right=.94,top=.88,bottom=.16)
    ys=np.arange(len(rows));colors=[GREEN if r['distinct_classes']==627 else BLUE for r in rows]
    ax.barh(ys,[r['distinct_classes'] for r in rows],color=colors);ax.set_yticks(ys,[r['stage'].replace('board_','').replace('executed_expert_','executed experts: ') for r in rows],fontsize=10);ax.invert_yaxis();ax.set_xlim(0,700);ax.set_xlabel('Distinct exact full-vector classes / 627 canonical boards')
    for y,r in zip(ys,rows):ax.text(r['distinct_classes']+5,y,str(r['distinct_classes']),va='center',fontsize=9)
    ax.axvline(627,color='#8a98a5',ls=':',lw=1)
    fig.suptitle('Research011 — exact information retention is not strategic meaning',fontsize=17,fontweight='bold',y=.97)
    fig.text(.05,.91,'A  Green = injective on this finite board census. Blue = at least two boards share an exact representation.',fontsize=11)
    fig.text(.05,.07,'B  Routes compress to 12 ordered classes (6 unordered); adding exact gates gives 480.\nC  The full merged vector and integer logits remain distinct on all 627 boards.\nD  Legal sign sets have 118 classes: several positions can share the same optimal moves.\nThis is equality counting, not a learned decoder, causal circuit, or held-out-domain performance test.',fontsize=11,linespacing=1.5)
    save(fig,d,'cardinality011')
    pair=next(e for e in ex if e['stage']=='pair_and_gates' and e['reason']=='controlled-different-tactic')
    mask=next(e for e in ex if e['stage']=='unmasked_signs' and e['reason']=='controlled-different-optimal-set')
    fig=plt.figure(figsize=(12,9));gs=fig.add_gridspec(2,3,width_ratios=[1,1,1.55]);fig.subplots_adjust(left=.045,right=.98,top=.86,bottom=.12,hspace=.5,wspace=.35)
    for row,e in enumerate((pair,mask)):
        for col,i in enumerate(e['canonical_ids']):
            footer=f"optimal {{{letters(e['optimal_sets'][col])}}}\nroute {e['routes'][col]} · Q15 {e['gates'][col]}"
            board(fig.add_subplot(gs[row,col]),e['boards'][col],e['optimal_sets'][col],e['optimal_sets'][col],f"{'ABCD'[row*2+col]}  Canonical {i}",footer)
        ax=fig.add_subplot(gs[row,2]);ax.axis('off')
        if row==0:
            txt="Same exact router metadata\n[3, 0, 32768, 0]\n\nSame ply / side / geometry counts.\n452: opponent fork + prevention\n413: one immediate opponent threat\n\nDifferent expert activations, merged\nvectors, logits and complete sets.\nExpert0 executes at gate zero.\nThis does NOT identify expert3\nas a tactical detector."
        else:
            txt="Same unmasked signs\n[+, +, +, +, +, +, +, +, +]\n\nSame ply / side / geometry counts.\nDifferent occupied squares remove\ndifferent members externally.\n\n299 legal set: {abcdeh}\n524 legal set: {abefgh}\n\nNo identical-logit collision exists\non this 627-board domain."
        ax.text(0,1,txt,va='top',fontsize=11.5,linespacing=1.5,color=INK)
    fig.suptitle('Exact collisions: what routing and signs do not tell you',fontsize=17,fontweight='bold',y=.97)
    fig.text(.045,.9,'All boards are real. Green borders and blue fills show the complete optimal legal set, not one preferred square.',fontsize=10.5)
    fig.text(.045,.035,'Geometry control: own/opponent corner, edge and center counts. Tactical labels are independent geometry,\nnot claims that blocking a threat can save an already lost position. Full data: examples011.json.',fontsize=11,linespacing=1.5)
    save(fig,d,'collisions011')
    put(d/'figure-metadata011.json',dict(figures=['cardinality011','collisions011'],callouts={'A':452,'B':413,'C':299,'D':524},pair_stage=pair['stage'],mask_stage=mask['stage'],no_projection_proof=True))

def walkthrough(out):
    """One exact canonical forward; parameter snippets are static, traces dynamic."""
    import torch
    from falken9.flexible_integer_export import load as packetload
    from scripts.build_runtime import FOUR_MODEL
    from study009_run import linear_scalar,round_scalar
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    a=np.load(ROOT/'artifacts/interpretability/study-011-final/baseline011.npz');c=packetload(FOUR_MODEL);i=341;b=a['boards'][i];side=int((b!=0).sum()%2);s=next(s for s in PRIORITY if a['optimal'][i,s]);query=4
    tables={n:c['tensors'][n]['codes'].tolist() for n in ('occupancy.weight','position','side.weight')}
    embedding=(np.array(tables['occupancy.weight'])[b[query]]+np.array(tables['position'])[query]+np.array(tables['side.weight'])[side]);assert np.array_equal(embedding,a['board_embedding'][i,query])
    dot=int(a['board_query'][i,query]@a['board_key'][i,0]);weighted=(a['attention_probs'][i,query,:,None]*a['board_value'][i]).sum(0)
    assert np.array_equal(np.array([round_scalar(int(x),32768) for x in weighted]),a['attended'][i,query])
    routes=a['routes'][i];gates=a['gates'][i];outputs=a['expert_outputs'][i,routes];mix=(outputs*gates[:,None]).sum(0)
    merged=a['readout_gelu'][i]+np.array([round_scalar(int(x),32768) for x in mix]);assert np.array_equal(merged,a['merged'][i])
    head=c['tensors']['output.weight'];bias=c['tensors']['output.bias']['codes'].tolist();yy=linear_scalar(merged.tolist(),head,bias,c['output_bits']);assert yy==a['logits'][i].tolist()
    hrow=head['codes'][s].tolist();products=(merged*np.array(hrow)).tolist();head_dot=sum(products);e=int(head['exponents'][s]);scaled=head_dot*(1<<e) if e>=0 else round_scalar(head_dot,1<<-e);assert scaled+bias[s]==yy[s]
    learned=dict(occupancy_code=tables['occupancy.weight'][b[query]],position_code=tables['position'][query],side_code=tables['side.weight'][side],output_row=hrow,output_exponent=e,output_bias=bias[s])
    trace=dict(canonical_id=i,board=b.tolist(),query_square=query,head_square=s,side_embedding_index=side,static_parameter_snippets=learned,embedding=embedding.tolist(),query_vector=a['board_query'][i,query].tolist(),key0_vector=a['board_key'][i,0].tolist(),query_key0_dot=dot,attention_scores=a['attention_scores'][i,query].tolist(),attention_q15=a['attention_probs'][i,query].tolist(),weighted_value_numerator=weighted.tolist(),attended=a['attended'][i,query].tolist(),readout_pre=a['readout_pre'][i].tolist(),readout_gelu=a['readout_gelu'][i].tolist(),norm2=a['norm2_output'][i].tolist(),router_scores=a['router_scores'][i].tolist(),routes=routes.tolist(),gates=gates.tolist(),expert_hidden_pre=[a['expert_hidden_pre'][i,e].tolist() for e in routes],expert_hidden=[a['expert_hidden'][i,e].tolist() for e in routes],expert_outputs=outputs.tolist(),weighted_expert_numerator=mix.tolist(),merged=merged.tolist(),head_products=products,head_dot=head_dot,head_scaled=scaled,logits=yy,legal_mask=(b==0).tolist(),legal_set=np.flatnonzero(a['optimal'][i]).tolist(),chosen=s,scope='One observed canonical forward, not semantic attribution. Attention query e is not output e; global flattened readout consumes all9x8 positions. Static code values do not light up. Inactive expert data unobserved.')
    put(out/'walkthrough1011.json',trace)
    # First page: board and truthful static-to-dynamic arithmetic in legible panels.
    fig=plt.figure(figsize=(12,9));gs=fig.add_gridspec(2,3);fig.subplots_adjust(left=.055,right=.97,top=.86,bottom=.14,hspace=.45,wspace=.4)
    board(fig.add_subplot(gs[0,0]),b,trace['legal_set'],trace['legal_set'],f'A  Input, canonical ID {i}',f"occupancy 0/1/2 = empty/X/O\nside index {side} · complete set {{{letters(trace['legal_set'])}}}")
    ax=fig.add_subplot(gs[0,1:]);ax.axis('off');txt=f"B  Stored learned codes (STATIC) → one embedding (DYNAMIC)\n\nquery square e, occupancy code: {learned['occupancy_code']}\nposition e code:                 {learned['position_code']}\nside index {side} code:              {learned['side_code']}\n\nExact componentwise sum: {trace['embedding']}\nThen integer norm1 and learned Q/K/V projections, on all nine tokens.\nThe eight coordinates are latent lanes, not the eight other squares."
    ax.text(0,1,txt,va='top',fontsize=10.5,family='DejaVu Sans Mono',linespacing=1.55)
    ax=fig.add_subplot(gs[1,0:2]);im=ax.imshow(a['attention_probs'][i]/32768,vmin=0,vmax=1,cmap='Blues',aspect='auto');ax.set_xticks(range(9),list('abcdefghi'));ax.set_yticks(range(9),list('abcdefghi'));ax.set_xlabel('Key square');ax.set_ylabel('Query square');ax.set_title('C  Actual attention probabilities (Q15 / 32768)',loc='left',fontweight='bold',fontsize=11)
    fig.colorbar(im,ax=ax,fraction=.035,pad=.02)
    ax=fig.add_subplot(gs[1,2]);ax.axis('off');ax.text(0,1,f"D  Row e, integer audit\n\nQ[e] · K[a] = {dot}\n\nRow sum = {sum(trace['attention_q15'])}\nQ15 mass, not move confidence.\n\nP[e] × V numerator lane0\n= {int(weighted[0])}\nround /32768 = {trace['attended'][0]}\n\nAttention is followed by learned\nprojection + residual, then a\nglobal 72→8 readout. Query e\nis NOT the output square e.",va='top',fontsize=11,linespacing=1.5)
    fig.suptitle('Read one real forward pass — 1 / 2',fontsize=19,fontweight='bold',y=.97)
    fig.text(.055,.9,'A→B→C→D is actual computation, not a drawing of what an expert “means”. All numbers use the frozen integer contract.',fontsize=10.5)
    fig.text(.055,.045,'Blue cells encode dynamic probability mass; static parameter snippets are labeled separately.\nFull 21-stage trace is in baseline011.npz; this page samples a query row only for readability.',fontsize=11,linespacing=1.5)
    save(fig,out,'forward-attention1011')
    fig=plt.figure(figsize=(12,9));gs=fig.add_gridspec(2,2);fig.subplots_adjust(left=.055,right=.97,top=.87,bottom=.14,hspace=.42,wspace=.32)
    ax=fig.add_subplot(gs[0,0]);ax.axis('off');ax.text(0,1,f"E  Learned router, dynamic top-2 execution\n\nrouter scores: {trace['router_scores']}\nordered expert IDs: {trace['routes']}\nmatching Q15 gates: {trace['gates']}\n\nSelected expert hidden vectors:\nE{routes[0]}: {trace['expert_hidden'][0]}\nE{routes[1]}: {trace['expert_hidden'][1]}\n\nOther expert activations: unobserved (null).\nA zero gate would NOT mean an expert was skipped.\nBoth selected experts actually execute.",va='top',fontsize=10.8,linespacing=1.5)
    ax=fig.add_subplot(gs[0,1]);ax.axis('off');vec=lambda v:'\n'.join(textwrap.wrap(str(v),60))
    ax.text(0,1,f"F  Merge is arithmetic, not a verbal strategy\n\nexpert weighted numerator, lane0:\n{int(outputs[0,0])} × {int(gates[0])} + {int(outputs[1,0])} × {int(gates[1])}\n= {int(mix[0])}\n\nreadout lane0 {int(a['readout_gelu'][i,0])} + round({int(mix[0])}/32768)\n= merged lane0 {int(merged[0])}\n\nComplete merged vector:\n{vec(trace['merged'])}\n\nThe final head uses all eight merged lanes.",va='top',fontsize=10.8,linespacing=1.5)
    ax=fig.add_subplot(gs[1,0]);ax.axis('off');ax.text(0,1,f"G  Exact output row {chr(97+s)}: static weights × activity\n\nstored row codes: {learned['output_row']}\nexponent {e}; bias {bias[s]} (native output units)\n\nΣ code × merged = {head_dot}\nscaled/rounded dot = {scaled}\n+ bias = {yy[s]}\n\nThis is one exact signed logit, not a probability.\nPositive/zero means membership; negative means out.\nRounding/clamps are part of the integer contract.",va='top',fontsize=10.6,linespacing=1.5)
    ax=fig.add_subplot(gs[1,1]);ax.axis('off');lines=[f"{chr(97+sq)}   {yy[sq]:>9}   {'empty' if not b[sq] else 'occupied':8}   {'IN' if not b[sq] and yy[sq]>=0 else 'out'}" for sq in range(9)]
    ax.text(0,1,"H  Final fixed wrapper\n\nsq    integer logit    legal?     result\n"+'\n'.join(lines)+f"\n\nFull set {{{letters(trace['legal_set'])}}}; priority ebdfhcgia → {chr(97+s)}.\nFor a rotated raw board: inverse-map the WHOLE set,\nthen reapply raw-coordinate priority. Never rotate\na single already chosen move as a shortcut.",va='top',fontsize=10.2,family='DejaVu Sans Mono',linespacing=1.5)
    fig.suptitle('Read one real forward pass — 2 / 2',fontsize=19,fontweight='bold',y=.97)
    fig.text(.055,.91,'E→F→G are learned integer computation; H is fixed masking, inverse coordinates and original-board tie-breaking.',fontsize=10.5)
    fig.text(.055,.045,'No tactic label, minimax result or cached move is consulted by this forward. Numerical execution does not, by itself,\njustify naming a unit “block detector”, “fork expert” or any other strategic component.',fontsize=11,linespacing=1.5)
    save(fig,out,'forward-experts1011')
    put(out/'figure-metadata-walkthrough1011.json',dict(canonical_id=i,callouts=list('ABCDEFGH'),fixed_vs_learned=True,static_vs_dynamic=True,attention_query_is_not_output_square=True,output_head_square=s,exact_head_scalar_checks=9,embedding_scalar_checks=8,weighted_value_scalar_checks=8,merged_scalar_checks=8,arrows='Sequential labels A through H; no invented spatial permutation of latent coordinates'))
    return trace

def make_reports(d10,d11,walk):
    d10=Path(d10);d11=Path(d11);walk=Path(walk);r=load(d10/'results010.json');rs=load(d11/'results011.json');experts=load(d11/'expert-census011.json');w=load(walk/'walkthrough1011.json')
    common="""## Scope and boundaries

The 5,195-byte packet SHA-256 is `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Parameters, tables, scales and integer arithmetic are frozen. These are CPU host studies, not new C64 timing/execution proofs. Baseline first reproduces **627 canonical boards, 13,167 saved actual-target stage vectors, 5,643 logit scalars**, and the composed **4,520 raw-board complete-set/inverse/tie contract**. Public wrapper calls replay those already verified canonical logits as TEST-ONLY fixtures; deployment always runs the neural core.

All boards were already trained/audited. There is no new held-out model-domain claim. Geometric tactical labels and the independent minimax solver are offline analysis only. Nonnegative logits indicate set membership, **not categorical confidence or ranking**. Independent tactical labels describe immediate geometry; on an already lost board an immediate-threat label need not imply one unique optimal blocking move.

No accepted C64 application, main checkout, model, packet, training run or release is changed. Research study010 is unrelated to accepted application010. All 1,258 files present at discovery, including every earlier study009 artifact, are hash-preserved. Tests use no cache writes; project imports are checked to resolve inside this snapshot.

"""
    t=["# Research010 — learned versus wrapper symmetry\n","> **Finding:** bypassing canonicalization leaves only **1,514 / 4,520** unique raw boards with the correct complete legal set; the unchanged canonicalizing wrapper gets **4,520 / 4,520**. This is an off-contract diagnostic of the canonical-trained network, not a shipping-game failure.\n",'[![Measured symmetry comparison](overview010.png)](overview010.svg)\n',common,"## Predeclared finite experiment\n\n`manifest010.json` / root `experiment-study010.json` were frozen before direct-orientation confirmation. All eight D4 transforms are applied to all 627 canonical boards. A transform maps original-square indices to destination indices. Direct inference deliberately skips canonicalization and uses frozen occupancy/absolute-position/side embeddings. We execute **4,520 deduplicated raw inputs**, then expand to **5,016 orbit observations**. Repeated orientations of symmetric boards do not create independent evidence. All 5,016 transform observations are also re-executed in per-transform batches to validate deduplication and all21 stages. A separate production-policy forward validates every direct logit without diagnostic hooks.\n\nFull predicted legal sets are inverse-aligned for the main symmetry comparison. Chosen-move statistics are instead evaluated in each actual transformed/raw coordinate frame using the original fixed priority `ebdfhcgia`. We do **not** transform one canonical chosen move. Readout and expert latent units have no spatial axis. Attention scores/probabilities align both query and key axes; square feature tensors align only the square row.\n",'## Exact unique-input outcomes\n\n|Outcome|Direct network / 4,520|Fixed wrapper / 4,520|\n|---|---:|---:|\n']
    for label,key,wr in [('Complete legal set correct','full_set_correct',4520),('Complete set differs','full_set_changes',0),('Empty learned set','empty_sets',0),('Nonoptimal nonempty choice','nonoptimal_nonempty',0),('Chosen move optimal','chosen_optimal',4520),('Different but optimal tie','optimal_tie_changes',0)]:t.append(f"|{label}|{r['unique_direct'][key]}|{wr}|\n")
    t.append('\nEmpty sets and nonoptimal nonempty choices partition chosen errors: 485 + 1,151 = 1,636. A changed complete set can still yield one correct chosen move. Different optimal ties are not errors.\n\n## All transformations, with repeated orbit observations\n\n|Transform|Exact full sets /627|Chosen optimal /627|Exact aligned logits /627|Identical ordered routes /627|\n|---|---:|---:|---:|---:|\n')
    for z in r['per_transform']:t.append(f"|T{z['transform_id']}|{z['full_set_correct']}|{z['chosen_optimal']}|{z['exact_aligned_logit_boards']}|{z['route_order_equal']}|\n")
    t.append(f"\nAcross the 5,016 observations: **{r['orbit_full_set_correct']}** exact sets and **{r['orbit_full_set_changes']}** different sets. Only **{r['all8_full_set_equivariant_canonical_boards']} /627** boards preserve the complete set under all eight direct orientations. **0/627** preserve all nine aligned integer logits under all eight. This is observed output non-equivariance, not a claim about any particular learned hidden mechanism.\n\nOrbit sizes: "+', '.join(f"{k} unique inputs for {n} canonical boards" for k,n in r['orbit_size_distribution'].items())+'. The size1 boards still have repeated identical inputs; their aligned logits can differ because coordinates are permuted even when the board is unchanged.\n\n## Follow one real board\n\n[![Eight actual orientations](orbits010.png)](orbits010.svg)\n\nCallouts A–H are the predeclared first canonical ID showing a nonidentity full-set disagreement (ID1). The same X-in-a-corner position is passed directly through the network in four unique raw orientations. T1/T4 select i when X is on g; the correct wrapper set is {e}. T2/T5 keep a correct chosen e but include six nonoptimal squares, demonstrating why one selected move hides full-set damage. T0/T7 repeat the canonical occupancy input but do not establish hidden invariance. Full integer scores, expert IDs, gate slots, active/null masks and expert vectors are in `examples010.json` and `measurements010.npz`.\n\n## Stage equality, not invented spatial semantics\n\n|Stage|T0 equal boards|T1|T2|T3|T4|T5|T6|T7|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n')
    for stage in r['stage_alignment'][0]['equal_boards']:t.append('|'+stage+'|'+'|'.join(str(z['equal_boards'][stage]) for z in r['stage_alignment'])+'|\n')
    t.append('\nExpert equality serializes only executed expert IDs, active masks and observed values. A normally unselected expert is null/unobserved, not zero. The observed canonical ID1 executes expert0 with Q15 gate0: execution is not contribution. Routes/gates are compared in their real ordered slots, not spatially permuted.\n\n## Verification, negative findings and interpretation limits\n\n* Identity reproduces all21 baseline stage arrays exactly. Each of the eight permutations and inverses is tested on square rows, both attention axes and output squares; nonspatial vectors remain unpermuted.\n* A production frozen policy independently matches 40,680 direct integer logit scalars. Per-transform reruns match 5,016 deduplicated observations and168 stage-array comparisons.\n* Independent matrix-derived D4 transforms, reachability enumeration, minimax sets, axis-aware equality counts, raw-coordinate set/move metrics and4,520 fixed-wrapper reconstructions pass (`independent-audit010.json`).\n* No hidden unit or expert is established as a symmetry detector. Canonicalized output agreement proves wrapper behavior, not network-learned rotational generalization.\n* Absolute positional embeddings and global flattened readout permit orientation dependence structurally; this study does not causally apportion the measured effect between them.\n* No post-hoc transform expansion, retraining or relaxed matching. The unfavorable direct-orientation results are retained.\n\n## Reproduction and files\n\nSee root `README-REPRODUCTION1011.md`, `FINAL-STUDY-010.json`, `verification-study010.json`. Arrays retain exact integer traces; dense NPZ inactive expert zeros are storage placeholders only, never measured observations. JSON examples use explicit nulls. Figures are measured PNGs with selectable-text SVG counterparts; click any image. The model/ROM binaries and environment are excluded from the source/evidence bundle.\n')
    (d10/'REPORT010.md').write_text(''.join(t))
    t=['# Research011 — exact representation collisions and information retention\n\n',"> **Finding:** full merged vectors and integer logits distinguish all **627** canonical boards; ordered routes distinguish only **12**, and routes plus exact gates distinguish **480**. Coarse routing metadata cannot uniquely identify the independent tactics or complete optimal sets. This does not imply the experts lack information.\n\n",'[![Exact stage cardinality](cardinality011.png)](cardinality011.svg)\n\n',common,'## Predeclared finite census\n\n`manifest011.json` fixes25 stage scopes and exact serialization before confirmation. C-order signed little-endian int64 values include an exact shape prefix. SHA-256 selects candidate buckets; **full byte equality**, never digest equality alone, establishes classes. An independent shape+integer-tuple implementation verifies all partitions and13,100 stage classes. A unit test forces a hash collision to ensure unequal values stay separate.\n\nFull expert observations serialize expert IDs in ascending ID order, execution masks and active values only. Per-expert populations include only boards where that expert actually executes. Route order and matching gate order are retained. Inactive observations are null; selected zero-gate execution remains an observation.\n\nIndependent labels: immediate own win, a single opponent threat when no own win, own fork after priority exclusions, opponent fork and fork prevention. Conditioning uses ply, side, and own/opponent corner/edge/center counts. The complete optimal-square set is independently solved offline. Exact equality can retain the information needed for an arbitrary finite lookup decoder without showing a simple semantic decoder or causal use. Unique embeddings are almost tautological because occupancy and positions are present.\n\n## Full exact counts\n\n`Duplicate boards` means all boards belonging to nonsingleton classes; `redundant boards` in JSON means population minus number of classes. Pair counts are unordered board pairs, not independent observations. A mixed class contains at least two different tactical tuples or complete optimal sets.\n\n|Stage|Classes|Duplicate boards|Collision pairs|Mixed tactics|Mixed optimal sets|Controlled mixed tactics / sets|\n|---|---:|---:|---:|---:|---:|---:|\n']
    for z in rs:t.append(f"|{z['stage']}|{z['distinct_classes']}|{z['duplicate_boards']}|{z['colliding_pairs']}|{z['mixed_tactic_classes']}|{z['mixed_optimal_classes']}|{z['conditioned']['mixed_tactic_classes']} / {z['conditioned']['mixed_optimal_classes']}|\n")
    t.append('\nControlled counts refer to separate `(representation, control-stratum)` classes. One unconditioned class can split into many controlled classes, so controlled mixed-class counts need not be smaller. They are not a numerator over the unconditioned class denominator. Exact control-stratum class/population counts and per-tactic breakdowns are in `results011.json`.\n\n## Actual collision counterexamples\n\n[![Controlled routing and masking collisions](collisions011.png)](collisions011.svg)\n\n* **A/B, canonical452/413:** identical ordered IDs `[3,0]` and exact gates `[32768,0]`, same ply/side/geometry counts, and even the same legal mask. Their independent tactical labels and full optimal sets differ. Distinct observed expert vectors, residuals and merged values carry information not present in router metadata. This is a direct counterexample to identifying a tactic from route+gate alone, not evidence against useful routing.\n* **C/D, canonical299/524:** all nine unmasked logits are positive on both boards, but occupied squares differ. Legal masks create distinct final sets {abcdeh}/{abefgh}. Raw sign equality does not require legally masked outcome equality. Actual integer logits remain different.\n* Exact full-logit collisions with different legal sets: **none on these627 boards**. The general warning about masks is illustrated by sign collisions, not by inventing an absent full-logit example.\n\n## Applicable per-expert census\n\n|Expert|Observed boards|Pre-GELU classes|Post-GELU classes|Output classes|Executed zero-gate boards|\n|---|---:|---:|---:|---:|---:|\n')
    for e in range(4):
        rr=[x for x in experts if x['expert_id']==e];t.append(f"|{e}|{rr[0]['population']}|{rr[0]['distinct_classes']}|{rr[1]['distinct_classes']}|{rr[2]['distinct_classes']}|{rr[0]['executed_zero_gate_boards']}|\n")
    t.append('\nThese populations sum to1,254 actual selected-expert executions, not2,508 observed four-expert activations. Expert0 has301 applicable boards and291 distinct post-GELU/output vectors; expert1 has258 and249. Expert2/3 remain injective within their applicable populations. Thus a full joint executed-expert signature can distinguish every board even when one expert collapses some inputs. No per-expert collapse is hidden by zero-filling inactive experts. Per-expert `first_*_pair` values index the accompanying `canonical_ids` list (local population coordinates), unlike the main stage examples, which use global canonical IDs.\n\n## What the census establishes—and what it does not\n\n1. Ordered route identity alone is necessarily coarse: top2 from4 admits12 orders and6 memberships; all are observed. Small route cardinality is architectural, not proof of strategic ignorance.\n2. Router score vectors remain distinct on all627 boards. Top-k and quantized gates discard distinctions when viewed **alone**; the network still passes richer vectors to experts.\n3. Exact merged/logit uniqueness is finite-domain information retention, not semantic decoding, hidden-unit strategy localization, generalization, or proof that all information is used causally.\n4. Sign/mask conversion is intentionally many-to-one: several boards legitimately require the same full optimal set. A mixed tactical class in the final set is not a policy error.\n5. No aesthetic2D embedding is used as evidence. All claims are exact equality checks on full integer values, with occupancy and applicable expert masks retained.\n6. Reused canonical boards are not independent samples; there are no statistical p-values or held-out accuracy claims. No parameter intervention or deployment modification occurs.\n\n## Controls, failures, reproducibility\n\nThe saved target baseline passes before the census. All25 full-vector partitions, all12 per-expert scopes, independent geometry and minimax labels, conditional counts, null masks,1,254 executions and22 collision examples pass independent checking. Full collision classes/IDs/hashes are retained in `classes011.json`; no post-hoc label or control relaxation occurs.\n\nA first write attempt failed on NumPy integer JSON metadata. Its partial evidence is preserved in `study-011-attempt1-incomplete-json`, with the original execution log. A new regression test first reproduced the serialization error; a scalar-to-native JSON fix passes. The manifest, stage scopes and numerical measurements were not altered; a fresh final run completes.\n\nSee root `README-REPRODUCTION1011.md`, `FINAL-STUDY-011.json`, `verification-study011.json`, and click the figures for native SVG. Binaries/environments/secrets are excluded from bundles.\n')
    (d11/'REPORT011.md').write_text(''.join(t))
    text=f'''# A reader's guide: frozen computation, wrapper symmetry and exact collisions

## Start with the boundary

A board is **not** a direct request to a rotation-invariant neural network. The shipping path validates the history, builds occupancy, picks a fixed canonical orientation, runs the frozen learned integer network, thresholds all nine logits, removes occupied squares, inverse-maps the **whole set**, and applies the original-board priority `ebdfhcgia`. Validation/canonicalization/inverse/mask/tie are fixed code, not learned reasoning. Learned embeddings, attention/readout, router, expert paths and output weights are numerical computation—not a solver fallback.

## 1. One actual forward pass, with labeled evidence

Canonical board **{w['canonical_id']}** is shown below. The first page separates stored parameter codes from input-dependent activity and shows attention's real query/key axes. The second shows actual expert IDs/gates, one exact merge lane, one exact output-row dot product and every final integer score.

[![Actual embeddings and attention](forward-attention1011.png)](forward-attention1011.svg)

**A. Input.** Cells use occupancy0/1/2, not confidence. Lowercase a–i are square identifiers. The example is canonical; a raw rotation would first be mapped to this frame by fixed code.

**B. Static → dynamic.** Occupancy, position and side parameter codes are summed componentwise. A weight is a stored scalar; it does not “light up.” Eight lanes are latent dimensions, not eight board positions. Exact parameter snippets and8 embedding sums are checked in `walkthrough1011.json`.

**C/D. Attention.** Query/key dot products feed the frozen integer scale/LUT softmax. Q15 row mass sums to32768. Value-weighted numerators are rounded, projected and added residually. A query row is not an output-square decision because the subsequent learned readout consumes the global flattened9×8 tensor. The display samples querye; it does not claim e is a strategy detector.

[![Actual routed experts, head and fixed mask](forward-experts1011.png)](forward-experts1011.svg)

**E. Routing.** Actual ordered experts **{w['routes']}** get matching Q15 gates **{w['gates']}**. Only these experts execute. Unselected expert observations are null; a selected expert with gate0 still executes (shown elsewhere in Research010/011). Gate mass is a mixture coefficient, not a tactic label.

**F. Expert paths and merge.** Each selected expert computes its learned hidden projection, integer GELU and output projection. Their weighted output vectors are rounded and added to the readout residual. The numerical diagram shows lane0 exactly, while JSON retains every lane. No scalar gets a strategy name without selective causal evidence.

**G. Output head.** For square **{chr(97+w['head_square'])}**, all8 merged lanes are multiplied by the frozen stored row codes, scaled/rounded using exponent **{w['static_parameter_snippets']['output_exponent']}**, and combined with native-unit bias. The exact dot is **{w['head_dot']}**, producing logit **{w['logits'][w['head_square']]}**. All9 head outputs, not just this row, are independently checked.

**H. Fixed output contract.** Nonnegative logits indicate membership, not probabilities or an ordering. Occupied squares are excluded. Canonical membership is inverse-mapped as a full set before tie-breaking in raw coordinates. The example returns {{{letters(w['legal_set'])}}} and chooses **{chr(97+w['chosen'])}**; another raw orientation can select a different equally optimal member after the same raw priority.

## 2. What changes when canonicalization is bypassed?

[![Symmetry measurement](../study-010-final/overview010.png)](../study-010-final/overview010.svg)

The direct off-contract network preserves the exact full legal set on **1,514/4,520** unique raw boards, versus **4,520/4,520** for the unchanged wrapper. Empty sets485; nonoptimal nonempty choices1,151; different but optimal ties345. The learned network is not, by itself, D4-output-equivariant on this finite audit. Do not describe those deliberate off-contract inputs as a broken game. [Full Research010 report](../study-010-final/REPORT010.md).

## 3. Does a route or a bright activation identify a tactic?

[![Controlled collision counterexamples](../study-011-final/collisions011.png)](../study-011-final/collisions011.svg)

No unique tactic identification follows from route/gate alone. Controlled boards452/413 share `[3,0,32768,0]` but differ in independent geometry labels and full optimal sets. The underlying full vectors remain distinct. All merged/logit vectors distinguish627 canonical boards, while routing has12 ordered classes and route+gate480. Equality census is about retained finite distinctions, not causal strategic meaning. [Full Research011 report](../study-011-final/REPORT011.md).

## Evidence and limits

* All5,195 model bytes remain unchanged (SHA-256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`).
* Baseline627/13,167/5,643 and composed4,520 raw complete-set/inverse/ties exact; no new C64 timing or execution claim.
* All boards previously trained/audited. Independent labels/solver are offline only. No semantic brain-map, invented screenshots or hidden-unit claims.
* Every PNG has a clickable native SVG with selectable labels. `walkthrough1011.json` gives exact coordinates, parameter snippets and arithmetic; stage files retain complete traces.
* See root `README-REPRODUCTION1011.md` for executed reproduction and preservation checks. Parent alone owns main-report integration; accepted game/model are untouched.
'''
    (walk/'ILLUSTRATED-SYNTHESIS1011.md').write_text(text)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--d10',required=True);a.add_argument('--d11',required=True);a.add_argument('--walk',required=True);args=a.parse_args();render010(args.d10);render011(args.d11);walkthrough(args.walk);make_reports(args.d10,args.d11,args.walk)
