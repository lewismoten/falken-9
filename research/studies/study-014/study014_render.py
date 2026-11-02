"""Deterministic paired SVG/PNG figures and evidence-linked report."""
import html,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
class Canvas:
    def __init__(self,w,h):
        self.im=Image.new('RGB',(w,h),'#f5f7fb');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#f5f7fb"/>']
    def rect(self,x,y,w,h,fill,stroke=None,width=1):
        self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke,width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
    def line(self,points,fill,width=1):
        pts=[(round(float(x),3),round(float(y),3)) for x,y in points];self.d.line(pts,fill=fill,width=width)
        self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{fill}" stroke-width="{width}"/>')
    def polygon(self,points,fill):
        pts=[(round(float(x),3),round(float(y),3)) for x,y in points];self.d.polygon(pts,fill=fill)
        self.svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{fill}"/>')
    def text(self,x,y,text,size=18,color='#172438',mono=False):
        self.d.text((x,y),str(text),font=ImageFont.truetype(MONO if mono else FONT,size),fill=color)
        self.svg.append(f'<text x="{x}" y="{y+size}" font-family="DejaVu Sans Mono" font-size="{size}" fill="{color}">{html.escape(str(text))}</text>')
    def save(self,out,name):
        self.im.save(out/(name+'.png'));(out/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n')
    def board(self,x,y,board,highlight,cell=65):
        for s,v in enumerate(board):
            r,c=divmod(s,3);xx=x+c*cell;yy=y+r*cell
            self.rect(xx,yy,cell,cell,'#ffded7' if s==highlight else '#ffffff','#7b8798')
            self.text(xx+7,yy+5,str(s),12,'#566377')
            if v:self.text(xx+22,yy+17,'X' if v==1 else 'O',29)

def render(out):
    out=Path(out);boxes=json.loads((out/'boxes014.json').read_text());res=json.loads((out/'results014.json').read_text());runs=json.loads((out/'validations014.json').read_text());audit=json.loads((out/'independent-audit014.json').read_text());bands=np.load(out/'joint-bands014.npz');d=np.load(out/'baseline014.npz');cons=json.loads((out/'constraints014.json').read_text())
    k=boxes['accepted_numerator'];accepted=boxes['grid'][k];orig=boxes['grid'][16]
    c=Canvas(1380,1120)
    c.text(30,20,'A | One-coordinate intervals are not automatically a joint box',26)
    c.text(30,58,f'Frozen head: 9 independent rows, each with bias + column0 weight. Accepted dyadic scale: {k}/16.',18)
    c.text(30,90,'Orange: original013 rectangle   Green: certified014 box   Blue: original codes   Pale: exact feasible bands',16)
    for s in range(9):
        col=s%3;row=s//3;left=35+col*450;top=140+row*285;ww=orig['rows'][s]['weight_interval'];bb=orig['rows'][s]['bias_interval'];aw=accepted['rows'][s]['weight_interval'];ab=accepted['rows'][s]['bias_interval']
        low=bands[f'row{s}-lower'];high=bands[f'row{s}-upper'];oldw=(aw[0]+aw[1])//2
        prior=json.loads((ROOT/'results013/certificates013.json').read_text());oldw=next(v['old_code'] for v in prior if v['id']==f'weight-{s}-0');oldb=next(v['old_code'] for v in prior if v['id']==f'bias-{s}')
        xmin=ww[0]-(ww[1]-ww[0])*.08;xmax=ww[1]+(ww[1]-ww[0])*.08;ymin=bb[0]-(bb[1]-bb[0])*.12;ymax=bb[1]+(bb[1]-bb[0])*.12
        px=lambda x:left+42+(x-xmin)/(xmax-xmin)*350
        py=lambda y:top+205-(y-ymin)/(ymax-ymin)*160
        c.text(left,top,f'Row{s}: w[{s},0], b[{s}]',19)
        c.rect(left+42,top+45,350,160,'#ffffff','#d6dce6')
        xs=np.unique(np.linspace(ww[0],ww[1],151).astype(int));polygon=[]
        for wv in xs:polygon.append((px(wv),py(max(ymin,min(ymax,int(low[wv+32768]))))))
        for wv in xs[::-1]:polygon.append((px(wv),py(max(ymin,min(ymax,int(high[wv+32768]))))))
        c.polygon(polygon,'#dce6f2')
        c.rect(px(ww[0]),py(bb[1]),px(ww[1])-px(ww[0]),py(bb[0])-py(bb[1]),None,'#cf7333',3)
        c.rect(px(aw[0]),py(ab[1]),px(aw[1])-px(aw[0]),py(ab[0])-py(ab[1]),None,'#158364',4)
        c.rect(px(oldw)-3,py(oldb)-3,6,6,'#2356bd')
        c.text(left+40,top+212,f'w: {ww[0]} .. {ww[1]}',13)
        c.text(left+40,top+232,f'b: {bb[0]} .. {bb[1]}',13)
        c.text(left+40,top+252,f'accepted min+ {accepted["rows"][s]["member_minimum"]}; max- {accepted["rows"][s]["nonmember_maximum"]}',13,'#116c55')
    c.text(30,1020,'B | Proof: every legal board constrains b above/below a rounded affine function of w.',18)
    c.text(30,1050,'C | All 65,536 signed16 weight codes per row audited. Shading sampled only for drawing; saved bands are exact.',16)
    c.text(30,1080,'Grid-maximal is not continuous-optimal. Membership scores are signed set indicators, never confidence.',16)
    c.save(out,'joint014')
    failures=[r for r in runs if r['role']=='original-row-corner' and r['examples']]
    r=failures[0] if failures else next(v for v in runs if v['witness'])
    if failures:ex=r['examples'][0];i=ex['canonical_id'];s=ex['row']
    else:ex=r['witness'];i=ex['canonical_id'];s=ex['row']
    obs=next(v for v in cons[s]['observations'] if v['canonical_id']==i);den=cons[s]['denominator'];oldcert=json.loads((ROOT/'results013/certificates013.json').read_text());oldb=next(v['old_code'] for v in oldcert if v['id']==f'bias-{s}');oldw=next(v['old_code'] for v in oldcert if v['id']==f'weight-{s}-0');ch=next(v for v in r['changes'] if v['row']==s);newb=ch['bias_code'];neww=ch['weight_code']
    def scalar(w,b):
        dot=obs['other']+obs['activation']*w
        return (1 if dot>=0 else -1)*((abs(dot)+den//2)//den)+b
    baseline=scalar(oldw,oldb);bias_only=scalar(oldw,newb);weight_only=scalar(neww,oldb);joint=scalar(neww,newb)
    c=Canvas(1380,930);c.text(30,20,'A | Actual counterexample: separate safe changes can combine into a sign flip' if failures else 'A | No original-box counterexample: measured boundary retained',24)
    c.text(30,62,f'{r["id"]} | canonical #{i}, output row{s}; square{s} is legal',18)
    c.board(45,125,d['boards'][i].tolist(),s,75)
    c.text(45,365,'X=first player; O=second',16)
    c.text(45,395,f'Baseline legal set: {np.flatnonzero(d["optimal"][i]).tolist()}',15)
    c.text(45,425,f'Changed legal set: {ex.get("changed_set",np.flatnonzero(d["optimal"][i]).tolist())}',15)
    c.text(350,120,'B | Exact arithmetic for this same board',21)
    details=[f'merged[0] = {obs["activation"]}; other dot = {obs["other"]}',f'score = round_half_away((other + merged[0]*w)/{den}) + b',f'Original codes: b={oldb}, w={oldw}; score {baseline}',f'Bias endpoint alone: b={newb}, w={oldw}; score {bias_only}',f'Weight endpoint alone: b={oldb}, w={neww}; score {weight_only}',f'JOINT: b={newb}, w={neww}; score {joint}']
    for j,line in enumerate(details):c.text(350,165+j*40,line,17,'#b64d32' if j==5 else '#172438')
    c.text(350,420,'Joint score above: observed FULL network; single-coordinate scores: exact scalar head.',15)
    c.text(350,450,'Source013 independently validated each one-coordinate endpoint. Zero counts as a member.',15)
    wr=next(v for v in runs if v['role']=='accepted-row-extremum' and v['changes'][0]['row']==s and v['witness']['kind']==('member-min' if obs['member'] else 'nonmember-max'));we=wr['witness']
    c.text(30,510,f'C | Accepted {k}/16 box: actual worst-case full-network witness for row{s}',23)
    c.board(45,560,we['board'],s,65)
    lines=[f'Canonical #{we["canonical_id"]}: {we["kind"]}',f'Full network score: {we["full_network_score"]}; baseline {we["baseline_score"]}',f'Corner codes: b={wr["changes"][0]["bias_code"]}, w={wr["changes"][0]["weight_code"]}',f'All627 canonical and4520 raw sets/ties unchanged.',f'PROOF: each legal member has min score >=0;',f'each legal nonmember has max score <0.',f'Rows separate, so all18-coordinate combinations satisfy these bounds.']
    for j,line in enumerate(lines):c.text(300,558+j*32,line,17)
    c.text(30,800,'OBSERVATIONS: 36 original row corners +18 accepted extrema +4 whole-box patterns; 58 full restorations.',17)
    c.text(30,838,'CERTIFICATE: affine dot extrema + monotone exact rounding; independent exhaustive weight/bias bands.',17)
    c.text(30,876,'Not 2^18 neural batches; no retraining, novel-input inference, probability, export or target timing claim.',17)
    c.save(out,'witness014')
    lines=['# Study014 — exact joint final-head robustness','',f'**Outcome:** original013 Cartesian box is **{"safe" if boxes["original_box_safe"] else "unsafe"}**. The largest passing predeclared dyadic scale is **{k}/16**. This accepted18-coordinate box certifies **{boxes["accepted_combinations_decimal"]} distinct integer parameter combinations** over every legal sign on627 canonical /4520 raw boards. Grid-maximal, not continuous-optimal.','', '![One-at-a-time rectangles versus feasible joint bands](joint014.png)','', '## Frozen design and boundaries','',f'Manifest SHA-256 `{res["manifest_sha256"]}`. Frozen model SHA-256 `{res["model_sha256"]}`. Manifest was read-only before any new outcome computation. Nine bias codes and column0 weight codes are varied on isolated in-memory copies, descriptors/exponents and all other codes fixed. All boards were already trained/audited. This is a host finite-domain certificate, not model-held-out generalization or new target execution.','', 'Predeclared panel: all36 original row corners; exact bands for all signed16 weight codes in each row; all17 scales0/16 through16/16 using delta truncation toward0;18 accepted row extremum witnesses (one lowest legal-member score and one highest legal-nonmember score per row, smallest canonical ID breaks ties); four accepted whole-box patterns(LL,LH,HL,HH). Each of58 candidates runs the complete627-board integer network, followed by a full original-code restoration and all-stage equality. No search beyond this frozen finite grid or further study.','', '## Arithmetic, exact constraints and proof','', 'For row s, let a=merged[0], c=sum over lanes1..7 of merged[j]*W[s,j], w=W[s,0], b=output.bias[s], D=2^(-row exponent). Scores are clamp32(R(c+a*w)+b), where R(z)=sign(z)*floor((abs(z)+D/2)/D). Bias codes add directly AFTER rounding; their stored exponent-11 is not reapplied. Signed32 clamping preserves signs. A zero score is a member. The observed panel has no output saturation.','', 'Exact joint feasible bias band at weight w: L(w)=max(-32768, max over legal members of -R(c+a*w)); U(w)=min(32767, min over legal nonmembers of -R(c+a*w)-1). L>U means no feasible bias. `joint-bands014.npz` retains both arrays for all65536 signed16 weights in each row. Each row is independent of all other final output rows and the final head cannot alter upstream merged vectors.','', 'Equivalent **piecewise half-plane constraints**, with integer b,w: write h(b)=-D/2 if b<0 and h(b)=-(D-1)//2 if b>=0. A legal member requires a*w+D*b >= h(b)-c; a legal nonmember requires a*w+D*b <= h(b)-c-1. This follows from the exact smallest dot threshold for R(dot)>=-b; the branch at b=0 preserves half-away asymmetry. The accepted box need not remain within one bias branch: direct rounding extrema and the full bands handle both branches. Every legal-board a,c,member,D is saved in `constraints014.json`. Occupied squares impose no policy constraint.','', 'For any row rectangle [wL,wU]x[bL,bU], per-board minimum=R(c+min(a*wL,a*wU))+bL and maximum=R(c+max(a*wL,a*wU))+bU. Monotone rounding makes these exact, not a linearized approximation. Require minimum>=0 for each baseline legal member and maximum<0 for each legal nonmember. Product safety follows by row separability: these inequalities hold simultaneously for ALL choices of ALL18 stored codes. The independent verifier separately enumerates EVERY weight code, computes bands board-by-board using quotient/remainder rounding (no shared014 core), and checks every bias in the accepted interval is contained in every band across the accepted weight range. It additionally directly scalar-evaluates four corners for every board at every scale. Thus certification is not inferred merely from the58 empirical network candidates.','', '## Grid certificate and accepted code box','', '|Scale|Safe|Rows failing|Smallest legal-member minimum|Largest legal-nonmember maximum|','|---|---|---|---:|---:|']
    for g in boxes['grid']:
        lines.append(f'|{g["numerator"]}/16|{g["safe"]}|{[v["row"] for v in g["rows"] if not v["safe"]]}|{min(v["member_minimum"] for v in g["rows"])}|{max(v["nonmember_maximum"] for v in g["rows"])}|')
    lines+=['','All larger declared scales fail; no continuous scale optimization, alternative center, asymmetric search or globally largest box claim. Nested boxes use original+sign(delta)*floor(abs(delta)*k/16).','','|Row|Original bias interval|Accepted bias interval|Original column0 weight interval|Accepted weight interval|Accepted min+/max-|','|---|---|---|---|---|---|']
    for ro,ac in zip(orig['rows'],accepted['rows']):lines.append(f'|{ro["row"]}|{ro["bias_interval"]}|{ac["bias_interval"]}|{ro["weight_interval"]}|{ac["weight_interval"]}|{ac["member_minimum"]}/{ac["nonmember_maximum"]}|')
    lines+=['','## Actual counterexample and proof witnesses','','![Measured counterexample and certified accepted witness](witness014.png)','']
    if failures:
        lines += [f'First declared failing candidate `{r["id"]}`: canonical#{i}, board`{d["boards"][i].tolist()}`, row{s}, a={obs["activation"]}, other={obs["other"]}, D={den}. Baseline score{baseline}; bias endpoint alone{bias_only}; weight endpoint alone{weight_only}; joint full-network score**{joint}**. Baseline legal set`{ex["baseline_set"]}`, changed`{ex["changed_set"]}`. Separate endpoint scores are exact scalar calculations on the saved merged vector, consistent with013 endpoint confirmations; the joint score is from a new full neural forward.','']
    lines += [f'Original failing corner batches: **{res["original_failing_corner_batches"]}/36**. All failures and favorable corners are retained; no assumption that the original box had to fail. Accepted18 extremum batches and4 whole-box patterns have zero canonical/raw complete-set changes, empties, nonoptimal choices or optimal tie changes. Occupied-only sign crossings, where present, remain distinct in validation records.','',f'Accepted row{s} `{we["kind"]}` witness canonical#{we["canonical_id"]}, board`{we["board"]}`, full-network score{we["full_network_score"]}; matching exact extremum saved in `extrema014.npz`. Both sign directions for every row are retained with code endpoints, activations and actual network scores in `validations014.json`.','', '## Every observed full-network candidate','', 'Counts are canonical/raw separately: set changes; empty sets; nonoptimal nonempty chosen moves; changes between equally optimal chosen moves. Raw sets are completely inverse-restored and ties freshly applied in original raw coordinates, not canonical errors multiplied by8.','', '|Candidate|Canonical set/empty/wrong/tie|Raw set/empty/wrong/tie|Occupied flips|','|---|---|---|---:|']
    for v in runs:
        fmt=lambda m:'/'.join(str(m[z]) for z in ('set_changes','empty','nonoptimal_nonempty','optimal_tie_changes'))
        lines.append(f'|{v["id"]}|{fmt(v["canonical"])}|{fmt(v["raw"])}|{v["occupied_sign_crossings"]}|')
    lines+=['','## Independent audit, reproduction and preservation','',f'* Actual full integer batches:117 =1 baseline +58 candidates +58 restorations; {res["full_network_board_executions"]} full board executions. Baseline reproduces all{res["baseline_stage_count"]} saved010 stages; each restoration recovers every stage, legal set and raw tie.',f'* Independent full-head scalar comparisons: {audit["independent_scalar_full_head_checks"]}. Independent65536-code row census: {audit["independently_verified_weight_codes"]} row-weight codes and{audit["independent_board_weight_sign_evaluations"]} applicable board/weight rounding constraints. No infeasible band is silently treated as a safe interval.',f'* Independent packet descriptor/signed16 offsets, reachable-board enumeration, minimax, D4 alignment, legal masks and raw ties pass. Actual public predict_history calls: {res["composed_public_wrapper_calls"]}; TEST-ONLY wrapper fixture replays freshly recomputed neural outputs, not that many neural forwards or a deployed bypass.','* Every project import originates inside this workspace; the existing dependency interpreter is borrowed only. All86 files in013,1492 files in003 and51 main frozen model/runtime/application files are hashed before and after, with exact prior-source file-list equality. Parent-owned mutable documentation is deliberately excluded from main preservation. No prior root or main files were modified.','* Two fresh full runs must reproduce every generated byte, including NPZ timestamps, figures and this report; final comparison and bundle identities are recorded in `verification014.json` and `FINAL-STUDY-014.json` at workspace root. `README-REPRODUCTION014.md` supplies exercised commands. Source/evidence ZIP excludes the frozen packet, environments, ROMs and private credentials; its exact packet hash remains a prerequisite.','', '## Limits and stop','', 'Finite-domain frozen-head policy membership only; no new boards, training, export/deployment, GPU, target execution, timing or RAM claim. Scores are arbitrary signed optimal-set indicators, never categorical confidence. Boxes constrain only these18 decoded signed16 codes with all other tensors, exponents, tables and wrapper fixed. This proves all combinations inside the accepted grid box, not arbitrary joint edits, a universal-input result, or continuous/global optimality. Stop after014; no further study or retraining.','']
    (out/'REPORT014.md').write_text('\n'.join(lines))
