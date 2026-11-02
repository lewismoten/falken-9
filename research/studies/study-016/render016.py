"""Deterministic dual PNG/SVG visual-first evidence; no installs."""
import argparse,json,html
from fractions import Fraction as F
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
COLORS=['#126b56','#3267a8','#9a6021'];NAMES={'accepted':'Accepted raw priority','reversed':'Reversed priority','largest_score':'Largest score (offline)'}
def read(p):return json.loads(Path(p).read_text())
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
class Canvas:
 def __init__(self,w,h):
  self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>'];self.bounds=[]
 def rect(self,x,y,w,h,fill,stroke='none'):
  self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=None if stroke=='none' else stroke);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>')
 def line(self,pts,color,width=2):
  self.d.line(pts,fill=color,width=width);self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')
 def text(self,x,y,text,size=20,color='#203443'):
  text=str(text);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size);box=self.d.textbbox((x,y),text,font=font)
  assert box[0]>=0 and box[2]<self.im.width and box[3]<self.im.height,(text,box)
  self.bounds.append(box);self.d.text((x,y),text,font=font,fill=color);self.svg.append(f'<text x="{x}" y="{y+size}" font-family="DejaVu Sans" font-size="{size}" fill="{color}">{html.escape(text)}</text>')
 def board(self,x,y,b,approved=(),chosen=None,scores=None,cell=90):
  for i,v in enumerate(b):
   r,c=divmod(i,3);xx=x+c*cell;yy=y+r*cell
   self.rect(xx,yy,cell-3,cell-3,'#d8efe4' if i in approved else '#eff2f4')
   self.text(xx+6,yy+2,chr(97+i),13,'#687987')
   if v or i==chosen:self.text(xx+cell*.33,yy+cell*.24,'XO'[v-1] if v else 'O',int(cell*.43),'#a2550c' if i==chosen else '#203443')
   elif scores is not None:self.text(xx+8,yy+cell*.47,str(scores[i]),16,'#126b56' if i in approved else '#687987')
 def save(self,out,name):
  self.im.save(out/(name+'.png'));(out/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n')
def render(inp,out=None):
 inp=Path(inp);out=Path(out or inp);out.mkdir(exist_ok=True)
 r=read(inp/'results016.json');ex=read(inp/'example016.json');a=read(inp/'independent-audit016.json')
 c=Canvas(1600,990)
 c.text(35,22,'016 | Safe against every reply, different against random replies',34)
 c.text(35,80,'Exact offline game-DAG enumeration. Human: uniform among all legal squares on every turn.',23)
 c.text(35,117,'Three frozen policies, two player roles, no opening sampler. Green / blue / amber = wins; grey = draws.',20,'#53616c')
 for col,role in enumerate(('X','O')):
  x=40+col*790;ps=[p for p in r['panels'] if p['role']==role]
  c.text(x,185,'Model '+role+(' (first)' if role=='X' else ' (second)'),28)
  for i,p in enumerate(ps):
   y=245+i*160;c.text(x,y,NAMES[p['policy']],22,COLORS[i])
   w=float(F(p['win']));c.rect(x,y+40,715,32,'#dbe1e6');c.rect(x,y+40,715*w,32,COLORS[i])
   c.text(x,y+86,f"Win {p['win']} | Draw {p['draw']} | Loss 0",20)
   c.text(x,y+116,f"E[marks] {p['expected_terminal_marks']} | {p['supported_games']} supported histories",18,'#53616c')
 c.text(35,755,'A  All six: no losing history, even when every legal human reply is treated adversarially.',25,'#126b56')
 c.text(35,810,'B  As X: equal win probability, different lengths and histories. As O: accepted wins most of these three.',22)
 c.text(35,860,'Largest-score is an offline counterfactual, not confidence, deployed behavior, or an optimized best response.',20,'#53616c')
 c.text(35,900,'Supported histories are not equiprobable; legal-choice denominators change along a game.',20,'#53616c')
 c.text(35,940,'These exact probabilities apply only to the declared uniformly random legal opponent.',20,'#53616c')
 c.save(out,'roles-outcomes016')
 c=Canvas(1600,1200)
 c.text(35,22,'016 | Minimax membership is not a random-opponent ranking',34)
 c.text(35,83,'Measured board: human X played h; model O to move. Green = complete legal approved set.',22)
 c.text(45,139,'A  Raw-restored integer scores',23)
 c.board(45,185,ex['board'],approved=ex['approved'],scores=ex['raw_logits'])
 c.text(390,200,'Approved: b, e, g, i. All four have minimax draw value.',25)
 c.text(390,255,'Accepted selects e (4262); largest-score selects i (54749).',22)
 c.text(390,302,'Occupied h has a positive score, but legal masking removes it.',21,'#53616c')
 c.text(390,349,'Actual ordered route (2, 3); matching Q15 gates (32768, 0).',21,'#53616c')
 c.text(390,396,'Selected expert 3 still executed, despite its zero gate.',21,'#53616c')
 for i,p in enumerate(ex['conditional']):
  x=45+520*i;c.text(x,555,NAMES[p['policy']],23,COLORS[i])
  c.line([(805,480),(805,508),(x+110,508),(x+110,538)],COLORS[i],2)
  c.line([(x+103,530),(x+110,540),(x+117,530)],COLORS[i],2)
  c.board(x+35,610,ex['board'],chosen=p['move'],cell=75)
  c.text(x,862,f"B{i+1}  Choose {chr(97+p['move'])} | raw score {ex['raw_logits'][p['move']]}",21,COLORS[i])
  c.text(x,905,f"Win {p['win']} | Draw {p['draw']} | Loss 0",20)
  c.text(x,947,f"E[additional marks] = {p['expected_additional_marks']}",19,'#53616c')
 c.text(35,1040,'Exact values continue the named fixed policy on every later model turn; not an isolated one-move causal effect.',21)
 c.text(35,1080,'Reversed and largest-score choose the same first move but differ later. No confidence interpretation is valid.',21)
 c.text(35,1120,'Offline annotated evidence, not C64 screenshots. No runtime cache, policy, model or game change.',21,'#53616c')
 c.text(35,1160,'Example selected by frozen rule: first reachable differing-choice / differing-probability board in (ply, raw tuple) order.',19,'#53616c')
 c.save(out,'branching-example016')
 put(out/'figure-metadata016.json',dict(panels=6,offline_only=True,figures=['roles-outcomes016','branching-example016'],example_board=ex['board'],source_files=['results016.json','example016.json','independent-audit016.json'],annotation_semantics='exact full-policy continuation, not isolated move causality; membership not confidence',native_game_screenshots=False,render_backend='Pillow plus equivalent explicit SVG; no package installation',text_bounds_checked=True))
 # Visual-first human report with exact tables; no unmeasured strength claims.
 lines=['# Study016 — Fixed safe ties against a uniformly random legal opponent','',
 '**Conclusion.** All three predeclared policies are loss-free against every legal human reply from the empty board, as either role. Against the specific uniformly random legal opponent, they have identical win probability as X, but different win probabilities as O. The accepted priority wins most often among these three as O; no search for an optimal exploitative policy was performed.','',
 '![Roles, exact outcomes and game lengths](roles-outcomes016.png)','',
 '## Frozen design and numerical scope','',
 'The manifest was frozen before outcomes: exactly two roles and three policies. Accepted raw priority is `ebdfhcgia`; reversed priority is `aigchfdbe`; largest-score selects the greatest raw-restored integer score within the **legal nonnegative approved set**, resolving equal scores with accepted priority. Largest-score is an **offline counterfactual**, not confidence, not deployed behavior, and not a proposed runtime change. There is no opening randomness in human play.','',
 'The opponent independently selects uniformly among all currently empty legal squares at each human turn. Play stops at the first win or full board. Complete ordered histories have probability equal to the product of reciprocal human branching counts, not equal mass per history. All results are exact rational enumeration, not sampled matches or native-game replay.','',
 '## Exact outcomes and lengths','',
 '| Model | Fixed policy | Win | Draw | Loss | Expected terminal marks | Supported complete histories (W/D/L) |','|---|---|---:|---:|---:|---:|---:|']
 for p in r['panels']:lines.append(f"| {p['role']} | {NAMES[p['policy']]} | {p['win']} | {p['draw']} | {p['loss']} | {p['expected_terminal_marks']} | {p['supported_games']} ({'/'.join(map(str,p['supported_by_outcome']))}) |")
 lines+=['','Expected terminal marks means total X+O marks from the empty board, including the terminal move. Per-state additional-mark expectations are retained in each DAG file. Fewer marks does not itself imply a stronger worst-case policy.','',
 '## A measured branching counterexample','',
 '![Actual board, full approved set and exact continuation probabilities](branching-example016.png)','',
 'At raw board `.......X.` (X at h), O’s legal approved set is `{b,e,g,i}`. Their raw integer scores are b=1322, e=4262, g=9176, i=54749. Accepted chooses e; reversed and largest-score choose i. All are minimax-optimal with draw value, yet continuing each declared policy yields different random-opponent outcomes: accepted win 97/105, reversed 23/35, largest-score 6/7. Every loss probability is zero. The largest positive score is not the greatest measured full-policy win probability. These are **policy-continuation** comparisons: reversed and largest-score share the first move but diverge later, so the figure does not attribute their whole difference to that first move.','',
 'The example is selected by the manifest’s fixed ordering (ply then raw tuple), preferring the first reachable model decision board where declared choices and conditional win probabilities differ. No extra policy or posthoc outcome panel was added. The raw positive score on occupied h is correctly removed by legal masking.','',
 '## Reachability and routes','',
 '| Role | Policy | Raw decisions, all turns /4520 | Canonical decisions, all turns /627 | Raw model decisions | Canonical model decisions | Model history-prefix visits | Ordered routes |','|---|---|---:|---:|---:|---:|---:|---:|']
 for p in r['panels']:lines.append(f"| {p['role']} | {NAMES[p['policy']]} | {p['reachable_raw_decisions']} | {p['reachable_canonical_decisions']} | {p['reachable_raw_model_decisions']} | {p['reachable_canonical_model_decisions']} | {p['model_history_prefixes']} | {len(p['routes'])} |")
 lines+=['',f"Across all six panels the union is {r['union_raw_decisions']} raw / {r['union_canonical_decisions']} canonical decision boards (both turns), and {r['union_raw_model_decisions']} raw / {r['union_canonical_model_decisions']} canonical model decision boards. Denominators 4520/627 cover all legal reachable nonterminal boards, including boards not reached by any tested policy. Counts exclude terminal boards; terminal counts are retained in results016.json.",'',
 'Each result panel retains ordered route IDs, unique raw/canonical model-board counts and history-prefix multiplicities. Canonical route counts collapse board symmetry; raw counts do not. Routes are ordered expert IDs, not move probabilities. Expert gate values are Q15 computation weights, not confidence. Inactive expert stage placeholders in the NPZ are not measured activations.','',
 '| Role / policy | Ordered route | Raw model boards | Canonical model boards | Model prefix visits |','|---|---|---:|---:|---:|']
 for p in r['panels']:
  for route in p['routes']:lines.append(f"| {p['role']} / {p['policy']} | {tuple(route['route'])} | {route['raw_model_boards']} | {route['canonical_model_boards']} | {route['model_history_prefixes']} |")
 lines+=['','## Neural binding and independent verification','',
 'One actual production whole-network CPU batch binds **627 distinct canonical boards once each per run**, retaining every stage and all nine logits. These expand to 4520 raw boards using complete inverse sets and raw-restored scores; tie priority is reapplied in raw coordinates. The branch enumerator uses validated neural outputs only as an **offline analysis cache**. A branch traversal is not a neural forward. Nothing installs a cache or changes deployed inference. Reproduction and tests repeat the binding in distinct runs; those repeats are not additional unique-domain coverage.','',
 f"A separately decoded arbitrary-integer scalar network independently recomputed all 627 boards, matching {a['stage_array_checks']} stage arrays / {a['stage_scalar_checks']} integer entries, and independently checked geometry, full-set restoration, minimax membership and all three raw ties across 4520 boards. The independent audit imports no production decoder, neural forward, study DP or wrapper functions. The scalar implementation was copied unchanged from study015 and its source hash is locked.",'',
 'Primary exact rational recursive DAG DP is independently checked with a bottom-up Fraction DP. A third explicit complete-history traversal enumerates every legal human reply without memoization, sums rational leaf mass and length, verifies support counts and route reachability, and searches for a loss witness. All six have zero loss leaves and nonzero draw support, so worst-case value from the empty board is a draw. The offline minimax oracle audits neural membership **after** move selection; it never chooses deployed or counterfactual moves.','',
 'The all-domain audit contains losing states that cannot occur from the empty board under these safe policies. We do not claim that a policy can avoid defeat from an already forced-loss board. We also do not claim new held-out model generalization: all 4520 raw / 627 canonical boards were previously trained/audited.','',
 '## Evidence and reproducibility','',
 '- `domain016.npz`: real full neural stage observations and canonical board axis.\n- `raw-bindings016.json`: every raw board, selected canonical transform, full logits, approved set, choices, route and gates.\n- `dag-<role>-<policy>016.json`: reachable decisions, legal supported edges, history-prefix counts, exact per-state probabilities, lengths and complete-history counts. Role 1 is X, 2 is O.\n- `example016.json`: measured branching board and exact named-policy continuation values.\n- `independent-audit016.json`: separate packet/forward/geometry/minimax/DP/tree verification.\n- `figure-metadata016.json`: annotation semantics and source axes.\n- Root `manifest016.json`, source locks, RED/GREEN logs, preservation inventories and final verification bind the experiment.','',
 'Frozen packet: 5195 bytes, SHA256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. The source/evidence bundle excludes the packet, runtime binaries, checkpoints, secrets and private endpoints; supply the accepted packet separately for reproduction. No training, installs, GPU, export, publication, services, native/game/model edits or follow-up studies. Main protected files and all discovered prior studies are preservation-checked; mutable parent-owned documentation is excluded.','',
 '**Scope limit:** These probabilities describe only the declared uniformly random legal-human model. The accepted policy’s advantage here is not a claim of general playing strength, learned exploitability ranking or optimal exploitation of weak play. Study ends at016.','', '## Execution notes','', 'Matplotlib was unavailable; final PNG/SVG rendering uses existing Pillow and explicit SVG, with no installs or panel changes. The conservative initial main inventory also caught one concurrently parent-updated mutable research report, `artifacts/operations/research/parent-study015-verification.json`. Its original hashes remain disclosed in `preservation-exceptions016.json`; it is explicitly excluded as parent-owned documentation. All other inventoried protected main files and every file in prior isolated studies are verified unchanged. Study016 made no main-repository writes.','']
 (out/'REPORT016.md').write_text('\n'.join(lines))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output');a=p.parse_args();render(a.input,a.output)
