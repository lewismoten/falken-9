#!/usr/bin/env python3
"""Independent saved-evidence arithmetic audit; no policy execution or search."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from falken9.flexible_integer_export import load
from scripts.build_runtime import FOUR_MODEL

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rnd(x,d):return (1 if x>=0 else -1)*((abs(x)+d//2)//d)
def clamp(x,bits=32):return max(-(1<<(bits-1)),min((1<<(bits-1))-1,x))
def audit(out):
    out=Path(out);read=lambda n:json.loads((out/n).read_text());base=read('baseline-vectors005.json');vecs=read('intervention-vectors005.json');means=read('training-means005.json');bs=base['boards'];st=base['stages'];c=load(FOUR_MODEL)
    w=c['tensors']['projection.weight']['codes'].tolist();es=c['tensors']['projection.weight']['exponents'];counts=[]
    for vv in vecs:
        pc=vc=0
        for i in range(627):
            values=means['value_integer'] if vv['id']=='value-position-mean' else st['board_value'][i]
            for q in range(9):
                p=vv['effective_attention_probs'][i][q];assert sum(p)==32768 and min(p)>=0
                attended=[clamp(rnd(sum(int(p[k])*int(values[k][h]) for k in range(9)),32768)) for h in range(8)]
                assert attended==vv['attended'][i][q],(vv['id'],i,q,'attended');vc+=8
                if vv['id']=='projection-position-mean':projected=means['projection_integer'][q]
                else:
                    projected=[]
                    for h in range(8):
                        dot=sum(int(attended[j])*int(w[h][j]) for j in range(8));e=es[h];projected.append(clamp(dot*(1<<e) if e>=0 else rnd(dot,1<<(-e))))
                assert projected==vv['projected'][i][q],(vv['id'],i,q,'projected');pc+=8
        counts.append(dict(id=vv['id'],scalar_attended_checks=vc,scalar_projected_checks=pc))
    # Scores are exactly local in Q/K occupancy+position+side, while normalized
    # probabilities can change due to the other seven keys/normalization.
    scoregroups={};pgroups={};localgroups={};pvchanges=0
    for i,b in enumerate(bs):
        ply=sum(x!=0 for x in b);side=1+ply%2
        occ=lambda s:0 if b[s]==0 else 1 if b[s]==side else 2
        for q in range(9):
            lk=(ply,q,occ(q));local=tuple(st['board_embedding'][i][q]+st['board_query'][i][q]+st['board_key'][i][q]+st['board_value'][i][q]);localgroups.setdefault(lk,set()).add(local)
            for k in range(9):
                dot=sum(int(st['board_query'][i][q][h])*int(st['board_key'][i][k][h]) for h in range(8));score=clamp(rnd(rnd(dot,1<<c['frac'])*c['attention_factor'],c['attention_denominator']))
                assert score==st['attention_scores'][i][q][k]
                key=(ply,q,k,occ(q),occ(k));scoregroups.setdefault(key,set()).add(score);pgroups.setdefault(key,set()).add(st['attention_probs'][i][q][k])
    assert all(len(x)==1 for x in scoregroups.values());assert all(len(x)==1 for x in localgroups.values())
    # Read-time denominator/coverage checks, kept separate from generation logic.
    pairs=read('matched-relocations005.json');coverage=read('matching-coverage005.json');fold=base['fold'];labels=base['candidate_labels']
    for r in coverage:
        task=r['task'];f=r['fold'];n=sum(int(fold[i]==f and labels[i][s][task]) for i in range(627) for s in range(9));covered=sum(x['task']==task and x['fold']==f for x in pairs);assert n==r['positive_candidates'] and covered==r['matched_positive_candidates']
    for ext in ('png','svg'):
        for name in ('attention-overview005','attention-contrasts005'):assert (out/f'{name}.{ext}').is_file()
    summary=dict(scope='Independent scalar saved-evidence reconstruction, no new interventions or policy execution',audit_source_sha256=sha(__file__),model_sha256=sha(FOUR_MODEL),interventions=19,total_attended_scalar_checks=sum(x['scalar_attended_checks'] for x in counts),total_projected_scalar_checks=sum(x['scalar_projected_checks'] for x in counts),counts=counts,native_qk_score_scalar_checks=627*81,score_control_strata=len(scoregroups),score_control_strata_varying=sum(len(x)>1 for x in scoregroups.values()),probability_control_strata=len(pgroups),probability_control_strata_varying=sum(len(x)>1 for x in pgroups.values()),embedding_qkv_control_strata=len(localgroups),embedding_qkv_control_strata_varying=sum(len(x)>1 for x in localgroups.values()),matched_records=len(pairs),coverage_recount_equal=True,figures_exist=True)
    (out/'independent-audit005.json').write_text(json.dumps(summary,separators=(',',':'))+'\n')
    (out/'INDEPENDENT-AUDIT005.md').write_text(f"# Independent005 evidence audit\n\n- Scalar exact P×V rounding/clamp reconstructed {summary['total_attended_scalar_checks']} attended values and {summary['total_projected_scalar_checks']} projection values over all19 saved interventions.\n- Native Q·K/early-scale scores: {summary['native_qk_score_scalar_checks']} independently reproduced.\n- Fixed ply/query/key/own-opponent occupancy: {summary['score_control_strata_varying']}/{summary['score_control_strata']} score strata vary, versus {summary['probability_control_strata_varying']}/{summary['probability_control_strata']} probability strata. This is whole-row softmax denominator and fixed leftover sensitivity, not a nonlocal Q/K feature.\n- Fixed ply/square/own-opponent occupancy: {summary['embedding_qkv_control_strata_varying']}/{summary['embedding_qkv_control_strata']} embedding/QKV strata vary. Local embeddings do not themselves inspect distant board geometry.\n- Recounted {len(pairs)} legal matched relocation records and every class/fold positive/matched denominator.\n\nInterpretation: learned local position/occupancy vectors interact across the board through attention normalization, value summation, projection and globally flattened readout. These tests establish exact input dependence and finite causal sensitivity, not a dedicated line/threat circuit or new generalization.\n")
    print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();audit(a.output)
