"""Evidence-only008 visual correction: zero failures must not be called fragile."""
import json,hashlib
from pathlib import Path
import numpy as np
from scripts.render_strategy_maps import Canvas,MUTED,DYNAMIC,GREEN,RED,EDGE,BG
from research678_render import board,lines
from research678_run import put,sha,ROOT

def render(out):
    out=Path(out);read=lambda n:json.loads((out/n).read_text());b=read('baseline.json');s=read('summary.json');census=read('margin-census.json');specs={r['id']:r for r in read('interventions.json')};vectors=read('vectors.json');base=np.array(b['logits']);legal=np.array(b['boards'])==0
    assert s['boards_any_set_change']==0 and s['boards_any_move_failure']==0,'zero-effect-specific display contract'
    figs=[];c=Canvas(1580,900);c.text(28,22,'Study008 / a bounded negative finding: no legal decision fragility observed',26)
    c.text(28,64,'76 one-code changes across38 coordinates; exact integer host recomputation, not a precision conversion or target benchmark.',17,MUTED)
    c.rect(25,110,1530,218);c.text(45,129,'A / all declared perturbations preserve legal complete sets',23,DYNAMIC)
    lines(c,45,174,[f"0/627 boards changed legal full sets;0/627 changed chosen moves; all627 robust to this finite76-intervention panel.",f"{s['legal_score_count']} legal scores;0 exact zeros. Negative->nonnegative legal flips0; nonnegative->negative legal flips0.",f"Occupied sign flips{s['occupied_sign_flips']} board-square-intervention observations: ignored by the fixed legal mask, not hidden decision failures.",f"All76 original-code restorations recover627 baseline boards and every saved stage; frozen5195-byte packet never rewritten."],1460,19)
    c.rect(25,352,1530,290);c.text(45,371,'B / exact legal membership-boundary distance census',23,DYNAMIC)
    dist=np.array(census['minimum_integer_score_change_to_membership_flip']);edges=np.array([1,100,1000,10000,100000,1000000,10000000]);counts,_=np.histogram(dist,edges)
    for j,n in enumerate(counts):
        x=70+j*235;h=140*n/max(1,int(counts.max()));c.rect(x,570-h,125,h,GREEN,GREEN);c.text(x,578,f'{edges[j]:,}..{edges[j+1]-1:,}',14);c.text(x,546-h,str(n),17)
    c.text(45,613,'Distance: y+1 if y>=0; -y if y<0. Board minimum over legal squares. Not a ranking margin.',17,MUTED)
    c.rect(25,668,1530,175);c.text(45,686,'C / limits and controls',22,DYNAMIC)
    lines(c,45,729,['Actual descriptor width8: all9 output biases,4 router biases,8 norm2 weights,8 norm2 biases,9 output weights chosen from TRAIN activation only.38 coordinates x2 doses; no code boundary rejects.','Closest legal score is+54 (distance55); this is not a parameter-space robustness certificate. No failure-prone coordinate ranking or human strategy established.'],1460,18)
    figs.append(c.save(out,'overview008'))
    # Display rules are descriptive postprocessing of saved vectors only, not intervention selection.
    nearest=int(np.argmin(dist));robust=int(max(range(627),key=lambda i:(dist[i],-i)));occupied=None
    for v in vectors:
        yy=np.array(v['logits']);flips=np.argwhere(((base>=0)!=(yy>=0))&~legal)
        if len(flips):occupied=(int(flips[0,0]),int(flips[0,1]),v);break
    assert occupied is not None
    cases=[('nearest legal boundary / no failure',nearest,vectors[0],None),('occupied sign flip / legally masked',occupied[0],occupied[2],occupied[1]),('robust counterexample / finite panel only',robust,vectors[0],None)]
    c=Canvas(1580,1100);c.text(28,22,'Study008 / actual nearest-boundary, masked-flip and robust examples',26)
    c.text(28,65,'No fragile legal case exists in this panel. A-C are descriptive saved-evidence callouts, not new or tuned experiments.',17,MUTED)
    evidence=[]
    for j,(label,i,v,occupied_square) in enumerate(cases):
        y=110+j*305;actual=[k for k in range(9) if legal[i,k] and base[i,k]>=0];spec=specs[v['id']];c.rect(25,y,1530,282);c.text(45,y+13,chr(65+j)+' / '+label,22,DYNAMIC);board(c,48,y+64,b['boards'][i],actual)
        ss=[f"Canonical ID{i}; fold{b['fold'][i]}; actual pair{b['routes'][i]}; Q15 gates{b['gates'][i]}",f"Legal full set{actual}; minimum legal integer flip distance{int(dist[i])}; zero failures across all76 codes.",f"Stored {spec['tensor']}{spec['coordinate']}: {spec['old_code']} ->{spec['new_code']}; code bits{spec['bits']}, packet byte offset{spec['byte_offset']}",f"Baseline logits {b['logits'][i]}",f"Perturbed logits {v['logits'][i]}"]
        if occupied_square is not None:ss.append(f"Occupied square{occupied_square}, mark{b['boards'][i][occupied_square]}: score{b['logits'][i][occupied_square]} ->{v['logits'][i][occupied_square]}; excluded before inverse/tie.")
        else:ss.append('Robust here means only this finite panel. Selected code is a display control, not the closest parameter boundary.')
        lines(c,240,y+63,ss,1260,16)
        evidence.append(dict(callout=chr(65+j),rule=label,id=i,board=b['boards'][i],fold=b['fold'][i],route=b['routes'][i],gates=b['gates'][i],baseline_logits=b['logits'][i],perturbed_logits=v['logits'][i],legal_set=actual,perturbation=spec,occupied_square=occupied_square,minimum_integer_distance=int(dist[i])))
    c.text(28,1058,'Green outline: actual baseline optimal legal set. Coordinates0..8 row-major. Final logits are >=0 set membership, never probabilities.',16,MUTED)
    figs.append(c.save(out,'cases008'))
    put(out/'figure-metadata.json',dict(figures=figs,callouts=evidence,renderer_sha256=sha(__file__),display_selection='Post hoc descriptive examples only, no added interventions: smallest legal distance; first occupied flip; largest legal distance.',reason='Original generic renderer used fragile/failure-prone labels despite zero failures. Corrected truthfully; original numeric experiment/source unchanged.'))
    put(out/'visual-amendment.json',dict(study='008',type='evidence-only caption/display correction after zero-effect result',no_new_interventions=True,renderer_sha256=sha(__file__),numeric_summary_sha256=sha(out/'summary.json'),original_renderer_sha256=sha(ROOT/'research678_render.py'),original_examples_sha256=sha(out/'examples.json'),preconfirmation_descriptor_amendment_sha256=sha(ROOT/'amendment-study008-descriptors.json')))
    p=out/'REPORT008.md';text=p.read_text();heading='\n## Zero-effect visual correction\n'
    if heading not in text:text+=heading+'All76 perturbations produced zero legal set or chosen-move failures. Generic original labels "fragile" and "failure-prone" were misleading and have been removed from the actual PNG/SVG figures. The original `examples.json` is retained as raw generated evidence; its legacy "fragile" label is NOT a finding. Revised figure metadata selects the actually nearest legal boundary, a real occupied-square sign flip removed by legal masking, and a robust counterexample, solely from already saved vectors. No new intervention or post-hoc panel expansion. `visual-amendment.json` binds this evidence-only correction.\n'
    p.write_text(text)
