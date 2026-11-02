"""Evidence-only board sequences, exact gates, domain coverage, seed orbit."""
import argparse,html,json
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
class Canvas:
 def __init__(self,w,h):
  self.im=Image.new('RGB',(w,h),'#f5f7fb');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#f5f7fb"/>'];self.extents=[]
 def rect(self,x,y,w,h,fill,stroke=None,width=1):
  self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke,width=width);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
 def line(self,pts,fill,width=1):
  self.d.line(pts,fill=fill,width=width);self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{fill}" stroke-width="{width}"/>')
 def text(self,x,y,t,size=18,color='#172438',mono=False):
  t=str(t);font=ImageFont.truetype(MONO if mono else FONT,size);box=self.d.textbbox((x,y),t,font=font);assert box[2]<self.im.width and box[3]<self.im.height,(t,box);self.extents.append(box)
  self.d.text((x,y),t,font=font,fill=color);self.svg.append(f'<text x="{x}" y="{y+size}" font-family="DejaVu Sans{ " Mono" if mono else ""}" font-size="{size}" fill="{color}">{html.escape(t)}</text>')
 def board(self,x,y,b,last,cell=29):
  for s,v in enumerate(b):
   r,c=divmod(s,3);xx=x+c*cell;yy=y+r*cell
   self.rect(xx,yy,cell,cell,'#ffe2bd' if s==last else '#ffffff','#b0bac8')
   if not v:self.text(xx+3,yy+1,s+1,10,'#8b94a1')
   elif v==1:
    self.line([(xx+7,yy+7),(xx+cell-7,yy+cell-7)],'#15618c',3);self.line([(xx+cell-7,yy+7),(xx+7,yy+cell-7)],'#15618c',3)
   else:
    self.d.ellipse((xx+6,yy+6,xx+cell-6,yy+cell-6),outline='#ad4b45',width=3);self.svg.append(f'<circle cx="{xx+cell/2}" cy="{yy+cell/2}" r="{cell/2-6}" fill="none" stroke="#ad4b45" stroke-width="3"/>')
 def save(self,out,n):
  self.im.save(out/(n+'.png'));(out/(n+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n')
def render(out):
 out=Path(out);load=lambda n:json.loads((out/n).read_text());g=load('games015.json');r=load('results015.json');t=load('opening-transitions015.json')['fixed_seed_host_emulation'];ply=load('coverage-by-ply015.json');values=load('value-coverage015.json');opening=load('opening015.json')
 first=next(x for x in g if x['is_first_deterministic']);order=[first]+[x for x in g if x is not first];keys=sorted({tuple(x['d4_key']) for x in g});cl={k:chr(65+i) for i,k in enumerate(keys)}
 c=Canvas(1740,1600);c.text(30,20,'A | Nine approved openings, nine complete real-inference paths',29)
 c.text(30,65,'9 raw move sequences | 7 D4 trajectory classes | all 9 games draw after 9 marks | host policy emulation',21)
 c.text(30,101,'Read left to right. Every board is an actual saved state; amber is the newest mark. Squares use 123 / 456 / 789.',18)
 c.text(30,132,'D4 class = one fixed rotation/reflection applied to the entire time-ordered sequence, not a new transform at each step.',17)
 for col in range(10):c.text(260+col*145,177,'start' if not col else f'mark {col}',17)
 for row,x in enumerate(order):
  yy=220+row*142;c.text(30,yy,f'Opening {x["opening"]+1}',22);c.text(30,yy+34,f'class {cl[tuple(x["d4_key"])]} / draw',17)
  if x['is_first_deterministic']:c.text(30,yy+65,'FIRST GAME',17,'#975519')
  for j,b in enumerate(x['boards']):
   xx=260+j*145;c.board(xx,yy,b,x['sequence'][j-1] if j else -1,29)
   if j:c.text(xx,yy+95,f'{"X" if j%2 else "O"} -> {x["sequence"][j-1]+1}',17)
 c.text(30,1515,'B | Only the opening branches. Every later turn restores the whole approved set and applies raw tie order afresh.',18)
 c.text(30,1547,'No screenshot mockups; these are annotated offline diagrams, not captured C64 output. Full vectors: game-stages015.npz.',17)
 c.save(out,'paths015')
 c=Canvas(1880,1510);c.text(30,20,'C | Variety is not coverage: 37 of 627 canonical decision boards',29)
 c.text(30,66,f'64/4520 raw decision boards ({64/4520:.2%}) | 37/627 canonical ({37/627:.2%}) | 81 model-mark forwards',21)
 c.text(30,108,'D | Each cell: ordered expert IDs, then exact Q15 gates (sum 32768). Columns are the pre-move ply.',18)
 for j in range(9):c.text(195+j*120,149,f'ply {j}',17)
 colors=['#dceaf5','#e4eedc','#f2e8d7','#eadff4']
 for i,x in enumerate(order):
  yy=190+i*74;c.text(30,yy+12,f'open {x["opening"]+1}',19)
  for j,s in enumerate(x['steps']):
   xx=180+j*120;c.rect(xx,yy,112,66,colors[s['routes'][0]])
   c.text(xx+7,yy+6,f'{s["routes"][0]} > {s["routes"][1]}',19,mono=True)
   c.text(xx+5,yy+39,f'{s["gates"][0]}/{s["gates"][1]}',12,mono=True)
 c.text(1320,115,'E | Ordered route coverage',22)
 c.text(1320,154,'route   full627  unique37  visits81',16,mono=True)
 for i,rr in enumerate(r['route_coverage']):
  yy=195+i*48;a,b=rr['route'];c.text(1320,yy,f'{a}>{b}     {rr["domain_boards"]:3d}      {rr["unique_path_canonical_boards"]:2d}       {rr["game_step_visits"]:2d}',17,mono=True)
 c.text(30,893,'F | Where paths miss the domain (terminal boards excluded from both denominators)',22)
 c.text(30,937,'ply      0     1     2     3     4     5     6     7     8',20,mono=True)
 for idx,(label,key) in enumerate([('domain','domain_canonical'),('path D4','path_unique_canonical'),('path raw','path_unique_raw')]):
  c.text(30,976+idx*34,f'{label:8}'+''.join(f'{p[key]:6}' for p in ply),20,mono=True)
 c.text(30,1110,'Coverage bars: one canonical decision board per unit; green = visited; grey = unvisited.',18)
 c.rect(30,1152,1254,25,'#d5dce5');c.rect(30,1152,74,25,'#218772');c.text(30,1190,'37 visited / 590 unvisited. Playing these games forever cannot expand this fixed branch union.',19)
 covered=sum(rr['unique_path_canonical_boards']>0 for rr in r['route_coverage']);c.text(1320,850,f'{covered}/12 ordered routes visited',22);c.text(1320,889,'Route IDs are not strategies.',17)
 c.text(30,1260,'G | All path boards have minimax value 0 (draw under optimal play). Full canonical-domain values:',20)
 c.text(30,1300,f'loss-to-move: {values["domain_canonical"].get("-1",0)} | draw: {values["domain_canonical"].get("0",0)} | win-to-move: {values["domain_canonical"].get("1",0)}',21)
 c.text(30,1370,'Q15 gates weight expert outputs, not move confidence. A zero gate can still accompany an executed expert.',18)
 c.text(30,1410,'Inactive expert arrays are storage placeholders, never observed zero activations. Only the listed two experts executed.',18)
 c.text(30,1450,'Reference627: fresh exact host forwards matched saved target-stage fixtures. No new native replay or timing claim.',18)
 c.save(out,'routes015')
 cycle=t['records'][t['transient_length']:];matrix=Counter((x['previous'],x['opening']) for x in cycle);whole=Counter((x['previous'],x['opening']) for x in t['records']);counts=Counter(x['opening'] for x in cycle)
 c=Canvas(1580,1110);c.text(30,20,'H | No immediate repeats does not mean independent uniform openings',27)
 c.text(30,65,'Source: fixed seed $A7; opening-only LFSR; rejection sampling; exclude the preceding opening.',20)
 c.text(30,104,'Left: exact fixed-seed host orbit counts. Right: ideal unbiased conditional law, not measured C64 randomness.',18)
 c.text(30,158,'Previous -> next opening; cycle event counts',21)
 for j in range(9):c.text(110+j*61,208,j+1,18)
 for i in range(9):
  c.text(55,253+i*61,i+1,18)
  for j in range(9):
   n=matrix[i,j];xx=100+j*61;yy=245+i*61
   fill='#c4dfd9' if n else '#e1e5ec';fill='#e8d4cc' if i==j else fill;c.rect(xx,yy,55,55,fill);c.text(xx+15,yy+13,n,20)
 c.text(710,168,'Ideal abstraction',24)
 lines=['72 allowed directed transitions; diagonal forbidden.','P(next=j | previous=i) = 1/8 for j != i.','Uniform stationary marginal = 1/9 per opening.','Ideal law is conditional on sample success.','Correlated, not independent sampling.','Actual source-seeded host sequence','One transient transition, then a 248-event cycle.',f'{len(matrix)}/72 transitions appear in the cycle; {len(whole)}/72 incl. transient.','Fixed cycle frequencies below are NOT uniform.','This is code-state enumeration, not a fairness test.']
 for i,line in enumerate(lines):c.text(710,215+i*39,line,18)
 c.text(710,652,'opening      1   2   3   4   5   6   7   8   9',17,mono=True)
 c.text(710,690,'events   '+''.join(f'{counts[i]:4}' for i in range(9)),17,mono=True)
 c.text(710,731,'denominator = 248 for each fixed-cycle frequency',17)
 c.text(30,845,'I | First session game opens 5 deterministically; next 12 source-emulated openings:',21)
 c.text(30,888,' -> '.join(str(x['opening']+1) for x in t['records'][:12]),24,mono=True)
 c.text(30,950,'All 2295 combinations of previous square and nonzero PRNG state were separately enumerated and audited.',18)
 c.text(30,988,'All 72 nonrepeat transitions are possible across those states. A single fixed seed does not visit them all.',18)
 c.text(30,1032,'Host policy/PRNG emulation only. No empirical RNG fairness, native C64 sampling, timing or physical replay claim.',18)
 c.save(out,'sampler015')
 lines=['# Study015 — what continuous self-play actually explores','', '**Nine approved openings produce nine raw sequences but only seven symmetry-equivalent trajectory classes. Every game draws in nine marks. Across all branches, only 37/627 canonical and 64/4520 raw nonterminal decision boards are visited. Continuous replay is variety, not exhaustive validation.**','','![Actual board-sequence contact sheet](paths015.png)','','## Frozen scope and accepted source','',f'Manifest SHA-256 `{r["manifest_sha256"]}` was written before opening membership or new trajectory outcomes were calculated. Frozen packet: 5,195 bytes, SHA-256 `{r["packet_sha256"]}`. Application010 and model bytes are unchanged. Only the isolated study015 workspace is written; the active report is excluded from preservation because another worker owns it. No training, weight ablation, install, GPU, service, publication, browser or physical replay. This is **host policy emulation**, not new native C64 evidence. All 627 canonical / 4,520 raw boards were already trained/audited; no new model-held-out generalization.','', 'Source discovery confirms the opening-only scope: `graphical_game.asm:195–221` resets the session then marks later games; `:306–343` performs `policy_request`, then `auto_resolve_opening`, remembers the opening and commits. `wrapper.asm:119–129` validates history, canonicalizes, executes the full neural forward and restores the entire set. `auto_demo.asm:33–129` samples only mode0/history-length0/later-game calls and excludes the preceding approved opening if another exists. The frozen application010 listing contains the same call order and raw tie loop. This is source-bound host emulation, not a newly executed binary-equivalence proof.','', 'The empty-board forward actually executed first; its full signed scores were:','',f'`{opening["logits"]}`','', 'All nine legal signs are nonnegative. These are independent optimal-set membership scores, not categorical preferences. Every branch then executes a **fresh full neural forward for every AI mark**: 81 game forwards, plus one empty-board discovery forward and 627 fresh reference-domain forwards. No saved policy, minimax fallback or logits cache chooses a mark. The domain reference is evaluated after the games. Offline minimax is read only after neural selection to audit it.','', 'First session game: **'+ ' → '.join(map(str,r['first_game_sequence_one_based']))+'**. Later games sample only the opening; continuation always uses ordinary fresh raw-coordinate ties. The tie order is **5,2,4,6,8,3,7,9,1** (one-based). Entire recommended sets are inverse-restored and legally masked before this tie order is applied.','', '## Complete trajectory census','', '|Opening|Sequence, raw one-based|D4 class|Outcome / marks|','|---:|---|---|---|']
 for x in g:lines.append(f'|{x["opening"]+1}{" (first)" if x["is_first_deterministic"] else ""}|'+ ' → '.join(str(s+1) for s in x['sequence'])+f'|{cl[tuple(x["d4_key"])]}|{x["outcome"]} / {x["length"]}|')
 lines+=['', 'A D4-equivalent trajectory requires one fixed board rotation/reflection for the whole ordered sequence, preserving ply and player. It is not just matching final boards, treating all corners as one opening, or separately canonicalizing each time step. Raw-coordinate tie priority breaks trajectory equivariance even though the restored complete sets are equivariant. Thus three opening geometries (center/edge/corner) expand into seven full-path classes. There are 70 distinct raw states including six terminal states; decision-domain coverage excludes those terminal states. No terminal forward is fabricated.','', '![Routes, exact gates and coverage](routes015.png)','', '## Route and domain coverage','', '|Ordered expert IDs|Full627 boards|Unique path canonical boards|Game-step visits (81)|','|---|---:|---:|---:|']
 for rr in r['route_coverage']:lines.append(f'|{rr["route"]}|{rr["domain_boards"]}|{rr["unique_path_canonical_boards"]}|{rr["game_step_visits"]}|')
 lines+=['', 'Unique-board coverage and repeated visits are distinct denominators. The nine empty-board requests execute the same ordered route nine times but cover only one canonical board. Q15 gates sum to32768 and weight the two executed expert outputs; they are not confidence in a square. A selected expert with zero gate still executes. Inactive expert storage slots are unobserved placeholders, not measured zero activations. `game-stages015.npz` retains all 21 stages per game mark, including full logits, attentions, routes, both gates and selected expert paths. `domain-stages015.npz` retains the same stages on all627 reference boards.','', '|Pre-move ply|Full canonical domain|Unique canonical on paths|Unique raw on paths|','|---:|---:|---:|---:|']
 for p in ply:lines.append(f'|{p["ply"]}|{p["domain_canonical"]}|{p["path_unique_canonical"]}|{p["path_unique_raw"]}|')
 lines+=['',f'Full canonical minimax values, for side to move: `{values["domain_canonical"]}`. Path values: `{values["path_canonical"]}`. Optimal self-play never enters already-winning or already-losing positions, leaving important response cases unexercised. Even repeated route IDs do not establish that all boards or numerical states on those routes were covered.','', '## The opening sampler: conditional law versus fixed source orbit','', '![Source-bound opening transition map](sampler015.png)','', 'Under an **ideal unbiased candidate-source abstraction**, conditional on a successful bounded sample, the nine-opening no-repeat transition matrix has diagonal0 and every off-diagonal probability **1/8**. Its stationary marginal is **1/9** per raw opening; opening geometry has stationary masses1/9 center,4/9 edge,4/9 corner. Neither statement implies independent openings. The first game is deterministic rather than a stationary draw. The rejection threshold removes modulo bias under that ideal abstraction; a bounded9-attempt guard reports failure instead of manufacturing a square.','', f'The actual source does not draw independent random bytes. It resets an8-bit LFSR to `$A7`; it is not seeded by elapsed time, audio or activity. Exact host enumeration finds one transient transition then a **248-event deterministic joint-state cycle**. This cycle uses **{len(matrix)}/72** structurally allowed directed transitions (**{len(whole)}/72** including the transient). Its opening event counts, for screen squares1..9, are `{[counts[i] for i in range(9)]}`; divide by248 for the orbit limiting frequencies. These are code-state enumeration counts, **not empirical hardware sampling or an RNG fairness test**, and they are visibly not the ideal1/9 marginal. Restarting an unchanged session resets to the same seed.','', 'Separately, every previous-opening/nonzero-LFSR-state combination was enumerated:9×255=2,295 states. All72 off-diagonal transitions are possible across this state census, immediate repeats never occur, and the finite guard is not exhausted for these accepted nine-opening states. The nine neural branch games cover all possible continuation shapes; no need to rerun a continuation for each previous opening because no later turn consults that previous-opening state. The source seeded orbit is not9 independently chosen openings, nor an exhaustive nonrepeating schedule.','', 'The game guide’s “uniformly” wording should therefore be read as the rejection-sampler’s intended conditional selection rule, **not a demonstrated fairness property of this fixed deterministic LFSR**. No release or documentation edits were made by this study; this qualification is reported as a finding.','', '## Independent audit and reproducibility','', 'The separate auditor imports no production packet decoder, wrapper, minimax or neural arithmetic. It independently decodes the packet, uses arbitrary-size Python integers for the entire forward, reconstructs all21 stages at all81 game steps and all627 reference boards, constructs D4 from coordinate geometry, validates first-equal canonical transform choice, inverse-restores whole sets, reapplies raw tie priority, independently enumerates4,520 raw/627 canonical nonterminal boards and solves minimax. Every game-step complete set and chosen move is optimal. It also reconstructs all2,295 sampler state transitions and the fixed-seed cycle. Tests include failure-first missing implementation checks and independent rerun. The one development correction was removal of a false sorted-order assumption for the existing canonical fixture; set equality plus the fixture’s actual row order is now used. This changes no scope or outcomes.','', '## Why self-play is not learning, and cannot replace full auditing','', 'Self-play is **not learning**: model parameter bytes, scales and lookup tables remain frozen; no optimizer, feedback update or search is run in gameplay. The computer repeatedly evaluates that same network on new boards. The PRNG only resolves the opening tie of later games. Nine draws are an understandable live demonstration, not a proof that every defensive response, winning conversion, canonical inverse or tie case works. These paths miss590 of627 canonical decision boards and4,456 of4,520 raw boards. Exhaustive finite-domain policy auditing remains necessary.','', 'No model is bundled in the source/evidence ZIP. To reproduce, place the separately hash-verified frozen packet at `artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j` and follow `README-REPRODUCTION015.md`. No new C64/native execution, gameplay timings, physical hardware compatibility, RNG fairness or generalization is claimed. Study015 stops here; no016 is started.','']
 (out/'REPORT015.md').write_text('\n'.join(lines))
 metadata=dict(square_numbering='one-based123/456/789',expert_numbering='zero-based IDs',diagram_not_screenshot=True,path_rows=[x['opening']+1 for x in order],path_boards=sum(len(x['boards']) for x in g),gate_cells=sum(len(x['steps']) for x in g),d4_classes=cl if False else len(keys),route_table_rows=len(r['route_coverage']),fixed_seed_cycle_transition_support=len(matrix),fixed_seed_including_transient_support=len(whole),png_svg_pairs=['paths015','routes015','sampler015'])
 (out/'figure-metadata015.json').write_text(json.dumps(metadata,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();render(a.output)
