"""Measured SVG/PNG diagrams from stored study009 integer forwards."""
import argparse,html,json
from pathlib import Path
from fractions import Fraction
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from research678_run import put
ROOT=Path(__file__).resolve().parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'


def case_records(out):
    out=Path(out);base=np.load(out/'baseline009.npz');selection=json.loads((out/'selection009.json').read_text())
    scope_order=['query','value','router','readout']
    def first(category):
        rr=[r for r in selection if r['category']==category and r['canonical_id'] is not None]
        return min(rr,key=lambda r:(scope_order.index(r['scope'].split('.')[0]),r['canonical_id']))
    specs=[('positive-failure',first('chosen-move-failure')),('robust-negative',first('robust-changed-stage')),('restoration-introduced-damage',first('route-restoration-introduced-damage'))]
    # All per-scope first set-change categories were frozen before the run.
    extra=[r for r in selection if r['scope']=='router.weight' and r['category']=='set-change-optimal-move' and r['canonical_id'] is not None]
    if extra:specs.append(('raw-tie-counterexample',min(extra,key=lambda r:r['canonical_id'])))
    cases=[]
    for label,spec in specs:
        scope=spec['scope'].split('.')[0];i=spec['canonical_id'];board=base['boards'][i];meta=json.loads((out/f'{scope}-materialized009.json').read_text())
        arrays={'baseline':base}
        for v in ('plain','restore-baseline-router-scores','restore-baseline-merged','self-router-scores-control','self-merged-control','clean-code-restoration'):
            arrays[v]=np.load(out/f'{scope}-{v}009.npz')
        stage={'query':'board_query','value':'board_value','router':'router_scores','readout':'readout_pre'}[scope]
        delta=arrays['plain'][stage][i]-base[stage][i];coord=np.unravel_index(int(np.abs(delta).argmax()),delta.shape);row=int(coord[-1])
        xx={'query':base['board_normalized'][i], 'value':base['board_normalized'][i], 'router':base['norm2_output'][i], 'readout':base['attention_residual'][i].reshape(-1)}[scope]
        x=xx[int(coord[0])] if xx.ndim==2 else xx
        old=np.array(meta['old_codes'][row]);new=np.array(meta['codes'][row]);k=meta['shifts'][row]
        product_error=(new*(1<<k)-old)*x;col=int(np.abs(product_error).argmax());e=meta['old_exponents'][row];ee=meta['exponents'][row]
        code=dict(coordinate=[row,col],row=row,input_lane=col,old_code=int(old[col]),old_exponent=e,new_code=int(new[col]),new_exponent=ee,shift=k,old_effective=str(Fraction(int(old[col]))*Fraction(2)**e),new_effective=str(Fraction(int(new[col]))*Fraction(2)**ee),input_value=int(x[col]),original_lattice_product_error=int(product_error[col]),old_row=old.tolist(),new_row=new.tolist(),old_row_dot=int(old@x),new_row_dot=int(new@x),stage_coordinate=[int(v) for v in coord],stage=stage,stage_before=int(base[stage][i][coord]),stage_after=int(arrays['plain'][stage][i][coord]),selection='Within this fixed selected case: largest absolute stage-output delta then largest absolute exact row product error; illustrative coordinate, not isolated causal attribution.')
        variants={}
        for name,a in arrays.items():
            logits=a['logits'][i];members=np.flatnonzero((logits>=0)&(board==0));move=next((s for s in (4,1,3,5,7,2,6,8,0) if s in members),-1)
            variants[name]=dict(logits=logits.tolist(),members=members.tolist(),move=move,empty=len(members)==0,correct=bool(move>=0 and base['optimal'][i,move]),routes=a['routes'][i].tolist(),gates=a['gates'][i].tolist(),router_scores=a['router_scores'][i].tolist(),readout=a['readout_gelu'][i].tolist(),norm2=a['norm2_output'][i].tolist(),merged=a['merged'][i].tolist())
        stagechanges=[]
        for st in ('board_query','board_value','attention_probs','attended','projected','attention_residual','readout_pre','readout_gelu','norm2_output','router_scores','gates','merged','logits'):
            d=arrays['plain'][st][i]-base[st][i];ix=np.unravel_index(int(np.abs(d).argmax()),d.shape)
            stagechanges.append(dict(stage=st,changed_scalars=int((d!=0).sum()),max_abs_delta=int(np.abs(d).max()),coordinate=[int(v) for v in ix],before=int(base[st][i][ix]),after=int(arrays['plain'][st][i][ix])))
        flips=np.flatnonzero(((base['logits'][i]>=0)!=(arrays['plain']['logits'][i]>=0))&(board==0))
        rawids=np.flatnonzero(base['raw_to_canonical_id']==i)
        rawbad=[int(j) for j in rawids if not arrays['plain']['raw_correct'][j]]
        j=rawbad[0] if rawbad else int(rawids[0]);t=base['raw_to_canonical_transform'][j]
        rawrec=dict(raw_id=j,board=base['raw_boards'][j].tolist(),raw_to_canonical=t.tolist(),baseline_members=np.flatnonzero(base['raw_optimal'][j]).tolist(),plain_members=np.flatnonzero(arrays['plain']['raw_members'][j]).tolist(),baseline_move=next(s for s in (4,1,3,5,7,2,6,8,0) if base['raw_optimal'][j,s]),plain_move=int(arrays['plain']['raw_moves'][j]),plain_correct=bool(arrays['plain']['raw_correct'][j]),raw_orbit_boards=len(rawids),raw_orbit_errors=len(rawbad))
        cases.append(dict(label=label,scope=scope,canonical_id=i,fold=int(base['fold'][i]),board=board.tolist(),code=code,legal_sign_crossings=flips.tolist(),stage_changes=stagechanges,variants=variants,raw_alignment=rawrec))
    return cases


class Canvas:
    def __init__(self,w,h):
        self.w=w;self.h=h;self.image=Image.new('RGB',(w,h),'#f5f7fb');self.d=ImageDraw.Draw(self.image);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#f5f7fb"/>'];self.texts=[]
    def rect(self,x,y,w,h,fill='#ffffff',stroke='#c8d1df'):
        self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke,width=2);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    def text(self,x,y,text,size=21,color='#17283f',mono=False):
        text=str(text);font=ImageFont.truetype(MONO if mono else FONT,size);box=self.d.textbbox((x,y),text,font=font)
        assert box[2]<=self.w-12 and box[3]<=self.h-8,(text,box)
        self.d.text((x,y),text,font=font,fill=color)
        self.svg.append(f'<text x="{x}" y="{y+size}" font-family="{"DejaVu Sans Mono" if mono else "DejaVu Sans"}" font-size="{size}" fill="{color}">{html.escape(text)}</text>');self.texts.append(dict(text=text,bounds=box))
    def arrow(self,x1,y1,x2,y2):
        self.d.line((x1,y1,x2,y2),fill='#567998',width=3);self.d.polygon([(x2,y2),(x2-10,y2-5),(x2-10,y2+5)],fill='#567998');self.svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#567998" stroke-width="3"/><path d="M{x2},{y2} l-10,-5 l0,10 Z" fill="#567998"/>')
    def board(self,x,y,board,members=(),move=-1):
        cell=63
        for s,v in enumerate(board):
            xx=x+s%3*cell;yy=y+s//3*cell
            self.rect(xx,yy,cell,cell,'#d6f0df' if s in members else '#ffffff','#467965' if s==move else '#bcc9d8')
            self.text(xx+8,yy+5,s,13,color='#66778a');self.text(xx+23,yy+20,'.XO'[v],27)
    def save(self,out,name):
        self.image.save(out/(name+'.png'));(out/(name+'.svg')).write_text('\n'.join(self.svg)+"\n</svg>\n")
        return dict(name=name,width=self.w,height=self.h,text_boxes=self.texts)


def case_figure(out,c,name):
    ca=Canvas(1560,1110);v=c['variants'];code=c['code'];base=v['baseline'];p=v['plain'];r=v['restore-baseline-router-scores'];m=v['restore-baseline-merged']
    ca.text(28,17,f"{c['label']} | {c['scope']}.weight | canonical #{c['canonical_id']} | fold {c['fold']}",29)
    ca.text(28,62,'A  Canonical board: green = legal nonnegative set; outline = fixed-priority move',21)
    for x,key,title in [(30,'baseline','Baseline W16'),(280,'plain','Coarse signed8'),(530,'restore-baseline-router-scores','Restore router'),(780,'restore-baseline-merged','Restore merged')]:
        ca.text(x,102,title,20);ca.board(x,137,c['board'],v[key]['members'],v[key]['move'])
        ca.text(x,336,f"move={v[key]['move']}  {'empty' if v[key]['empty'] else 'optimal' if v[key]['correct'] else 'nonoptimal'}",18)
    ca.rect(1030,102,497,266,fill='#edf2f8')
    ca.text(1048,119,'Static decoded parameter example',21)
    ca.text(1048,158,f"[{code['row']},{code['input_lane']}]  shift k={code['shift']}",20,mono=True)
    ca.text(1048,194,f"W16 {code['old_code']} x 2^{code['old_exponent']}",20,mono=True)
    ca.text(1048,230,f"W8  {code['new_code']} x 2^{code['new_exponent']}",20,mono=True)
    ca.text(1048,266,f"input scalar: {code['input_value']}",20,mono=True)
    ca.text(1048,306,'Whole component changes; not one-cell attribution.',16)
    ca.rect(28,389,1500,169)
    ca.text(45,400,f"B  Actual integer stage {code['stage']} at {code['stage_coordinate']}",22)
    ca.text(45,437,f"rounded output {code['stage_before']} -> {code['stage_after']}; row dots {code['old_row_dot']} -> {code['new_row_dot']}",20,mono=True)
    ca.text(45,474,f"baseline routes {base['routes']}, gates {base['gates']}  ->  coarse routes {p['routes']}, gates {p['gates']}",20,mono=True)
    ca.text(45,511,'Routes are ordered expert IDs; gates Q15 sum to 32768. Unselected expert outputs are unobserved.',20)
    ca.rect(28,580,1500,185)
    ca.text(45,592,'C  Dynamic activations and signed legal membership (not categorical preference)',22)
    ca.text(45,633,f"merged W16: {base['merged']}",19,mono=True)
    ca.text(45,670,f"merged W8 : {p['merged']}",19,mono=True)
    ca.text(45,710,f"legal sign crossings: {c['legal_sign_crossings']}  |  occupied crossings do not enter the legal set",19)
    ca.rect(28,786,1500,185)
    ca.text(45,798,'D  Nine actual final scores: square indices 0..8, accepted iff empty and score >= 0',22)
    for yy,key,title in [(838,'baseline','W16'),(875,'plain','W8 '),(912,'restore-baseline-router-scores','Rtr')]:
        ca.text(45,yy,f"{title}: {v[key]['logits']}",19,mono=True)
    ca.text(30,991,'Self-cutpoint controls reproduce every coarse stage; clean code restoration reproduces every baseline stage.',20)
    ca.text(30,1026,'Restoring merged is a downstream sufficiency check with unchanged head, not proof of a unique circuit.',20)
    ca.text(30,1061,'Packet-derived host diagnostic only. Stored weights are static; activations/routes depend on the board.',20)
    return ca.save(out,name)


def render(out):
    out=Path(out);cases=case_records(out);put(out/'cases009.json',cases);rows=json.loads((out/'results009.json').read_text());layouts=[]
    ca=Canvas(1560,980);ca.text(30,20,'Study009: componentwise coarser precision is not isolated one-code noise',29)
    ca.text(30,70,'Frozen deployed packet -> row-scaled signed8 approximation -> unchanged integer neural forward',22)
    ca.text(30,110,'Four single-component scopes, six variants each: 24 fixed specifications. No escalation, training or deployment.',21)
    ca.rect(28,165,1502,307);ca.text(45,182,'A  Full legal-set changes and actual raw-wrapper outcomes',24)
    ca.text(45,230,'Scope       set /627   bad move /627   raw set /4520   raw bad /4520   raw empty / nonoptimal',20,mono=True)
    for j,short in enumerate(('query','value','router','readout')):
        r=next(v for v in rows if v['scope']==short+'.weight' and v['variant']=='plain');a=r['canonical'];b=r['raw']
        ca.text(45,279+j*42,f"{short:8}   {a['set_changes']:5}       {a['move_errors']:5}         {b['set_changes']:5}          {b['move_errors']:5}            {b['empty']:3} / {b['nonoptimal_nonempty']:3}",20,mono=True)
    ca.rect(28,492,730,248);ca.text(45,507,'B  Whole-row representation change',23)
    ca.text(45,552,'Codes -127..127; -128 unused. Round half away.',20)
    ca.text(45,589,'Smallest k fits row; exponent becomes e+k.',20)
    ca.text(45,626,'All biases unchanged. Clipping = 0 in every scope.',20)
    ca.text(45,663,'64 / 64 / 31 / 575 effective scalars changed.',20)
    ca.text(45,700,'Prior008: 76 isolated +/-1 probes; 0 legal-set changes.',19)
    ca.rect(782,492,748,248);ca.text(800,507,'C  Restore baseline routes AND gates',23)
    ca.text(800,552,'Readout: 12 -> 8 canonical move failures.',21)
    ca.text(800,589,'5 rescued, 1 newly damaged; not a universal rescue.',20)
    ca.text(800,626,'Raw: 91 -> 65 failures; canonical counts are not x8.',20)
    ca.text(800,663,'Merged restoration: all final vectors exact.',20)
    ca.text(800,700,'Matched self controls: all-stage identity, 8/8.',20)
    ca.text(30,777,'Static parameter conversion and dynamic integer responses are different evidence surfaces.',23)
    ca.text(30,819,'>=0 is membership, not confidence; wrong full sets can hide behind correct canonical chosen moves.',21)
    ca.text(30,859,'Host-only replay of original-target fixtures. All boards previously trained/audited; folds are probe confirmation.',20)
    ca.text(30,899,'NOT a verified reproduction of historical float-master INT8 exports. No C64 timing or deployment claim.',21)
    layouts.append(ca.save(out,'overview009'))
    for c,name in zip(cases[:3],('mechanism009','robust009','restoration-damage009')):layouts.append(case_figure(out,c,name))
    c=cases[3];v=c['variants'];raw=c['raw_alignment'];ca=Canvas(1560,1030)
    ca.text(30,20,'Raw-coordinate tie counterexample: a correct canonical move is not a correct full set',28)
    ca.text(30,68,f"router.weight approximation | canonical #{c['canonical_id']} | raw #{raw['raw_id']} | fold {c['fold']}",22)
    ca.text(30,113,'A  Canonical W16',22);ca.board(30,158,c['board'],v['baseline']['members'],v['baseline']['move'])
    ca.text(315,113,'B  Canonical W8',22);ca.board(315,158,c['board'],v['plain']['members'],v['plain']['move'])
    ca.text(655,113,'C  Raw W16',22);ca.board(655,158,raw['board'],raw['baseline_members'],raw['baseline_move'])
    ca.text(950,113,'D  Raw W8',22);ca.board(950,158,raw['board'],raw['plain_members'],raw['plain_move'])
    ca.arrow(240,249,300,249);ca.arrow(860,249,930,249)
    ca.text(30,370,f"Canonical chosen move {v['baseline']['move']} -> {v['plain']['move']} stays optimal; set {v['baseline']['members']} -> {v['plain']['members']}",21)
    ca.text(30,413,f"Raw chosen move {raw['baseline_move']} -> {raw['plain_move']}; coarse raw move is {'optimal' if raw['plain_correct'] else 'NONOPTIMAL'}",22)
    ca.rect(28,467,1500,246)
    ca.text(45,484,'E  Exact alignment and wrapper, not a learned strategy layer',23)
    ca.text(45,530,f"raw -> canonical square mapping: {raw['raw_to_canonical']}",22,mono=True)
    ca.text(45,574,'Raw priority: [4,1,3,5,7,2,6,8,0]. Inverse-transform the COMPLETE set, then apply priority.',21)
    ca.text(45,618,f"Raw orbit: {raw['raw_orbit_errors']} wrong moves / {raw['raw_orbit_boards']} boards; do not multiply canonical errors by eight.",22)
    ca.text(45,662,f"routes {v['baseline']['routes']} -> {v['plain']['routes']}; gates {v['baseline']['gates']} -> {v['plain']['gates']}",21,mono=True)
    ca.rect(28,736,1500,166)
    ca.text(45,750,'F  Actual output scores in canonical square order 0..8',23)
    ca.text(45,794,f"W16: {v['baseline']['logits']}",19,mono=True)
    ca.text(45,834,f"W8 : {v['plain']['logits']}",19,mono=True)
    ca.text(45,872,f"Legal sign crossings: {c['legal_sign_crossings']} (green denotes set membership, not a preference ranking).",19)
    ca.text(30,935,'Actual public predict_history wrapper executed on all 4520 raw boards with test-only canonical logits.',20)
    ca.text(30,971,'627 canonical neural forwards per variant were recomputed in full. This is a composed host proof, not target speed.',20)
    layouts.append(ca.save(out,'raw-alignment009'));put(out/'figure-layout009.json',layouts)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();render(a.out)
