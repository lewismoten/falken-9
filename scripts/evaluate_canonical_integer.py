"""Direct conversion and exhaustive F9J2 neural policy verification, CPU only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from falken9.canonical_model import decode_model
from falken9.canonical_training import load_data,evaluate
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.canonical_integer_export import convert,save,load

SOURCE='artifacts/canonical/qat/w8-h4-float-islands-int8-refine-s23/packed/model.f9c'
SOURCE_SHA='6e10652115c9f373f34b6158eeb6f87a1bec1e7db66a2ee8a96bf5b3dd380464'


def diagnose_legacy(data,output='artifacts/integer-range'):
    from falken9.integer_export import load as load_old
    from falken9.integer_model import IntegerPolicy,select_moves
    from falken9.range_integer_model import RangeIntegerPolicy
    source=Path('artifacts/integer/w8-int8-q8/model.f9i')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    old=IntegerPolicy(load_old(source)); wide=RangeIntegerPolicy(load_old(source))
    boards=torch.tensor(data['boards'],dtype=torch.int64)
    labels=torch.tensor([ord(m)-97 for m in data['labels']])
    a=[];b=[];ar=[];br=[]
    for batch in boards.split(256):
        x,r=old(batch,True);y,s=wide(batch,True)
        a.append(x);b.append(y);ar.append(r);br.append(s)
    a=torch.cat(a);b=torch.cat(b); ar=torch.cat(ar);br=torch.cat(br)
    op=select_moves(a,boards);wp=select_moves(b,boards); om=op!=labels;wm=wp!=labels
    result=dict(old_board_misses=int(om.sum()),old_history_misses=int(om[data['history_indices']].sum()),wide_board_misses=int(wm.sum()),wide_history_misses=int(wm[data['history_indices']].sum()),old_clamp_equals_wide=bool(torch.equal(a,b.clamp(-32768,32767))),route_mismatches=int((ar!=br).sum()),changed_logits=int((a!=b).sum()),old_stats=old.stats,wide_stats=wide.stats,source=str(source),source_sha256=digest,source_sha256_after=hashlib.sha256(source.read_bytes()).hexdigest(),contract='diagnostic final output INT32 only; old F9I1 packet semantics and rejection unchanged')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'board-results.json').write_text(json.dumps(dict(old_logits=a.tolist(),wide_logits=b.tolist(),old_routes=ar.tolist(),wide_routes=br.tolist(),old_predictions=op.tolist(),wide_predictions=wp.tolist())))
    return result


def evaluate_candidate(source,data,output,frac=11,matrix_bits=16,activation_bits=32,attention_mode='early',interpolate=True,scalar=True,public=False):
    torch.set_num_threads(1); start=time.monotonic()
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    raw=Path(source).read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    if digest!=SOURCE_SHA: raise ValueError('expected immutable accepted effective F9C1 weights')
    teacher=decode_model(raw).eval()
    c=convert(teacher,frac,matrix_bits,activation_bits,attention_mode,interpolate)
    path=output/'model.f9j'; inventory=save(c,path); decoded=load(path)
    runtime=CanonicalIntegerPolicy(decoded); memory=CanonicalIntegerPolicy(c)
    b=data['canonical_boards']; logits,routes=runtime(b,True); ml,mr=memory(b,True)
    stats=json.loads(json.dumps(runtime.stats))
    materialized=int((logits!=ml).sum()); route_parity=int((routes!=mr).sum())
    result=evaluate(runtime,data,output,benchmark=False)
    scalar_logits=scalar_routes=None
    if scalar:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
        spec=importlib.util.spec_from_file_location('scalar_canonical_integer',Path(__file__).resolve().parents[1]/'tests/test_canonical_integer_model.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
        scalar_logits=scalar_routes=0
        for i,board in enumerate(b.tolist()):
            expected,route=oracle.scalar_oracle(decoded,board)
            scalar_logits+=sum(a!=v for a,v in zip(expected,logits[i].tolist()))
            scalar_routes+=sum(a!=v for a,v in zip(route,routes[i].tolist()))
    public_errors=None
    if public:
        representatives={}
        for history,bi in zip(data['histories'],data['history_indices'].tolist()): representatives.setdefault(bi,history)
        public_errors=0
        for bi,history in representatives.items():
            try: actual=runtime.predict_history(history)
            except ValueError: actual=None
            public_errors+=actual!=data['labels'][bi]
    with torch.no_grad(): teacher_logits,teacher_routes=teacher(b,return_routes=True)
    stage_bits={name:max(1,value.bit_length()+1) for name,value in stats['accumulators'].items()}
    result.update(inventory,source=str(source),source_sha256=digest,source_sha256_after=hashlib.sha256(Path(source).read_bytes()).hexdigest(),artifact=str(path),artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frac=frac,matrix_bits=matrix_bits,activation_bits=activation_bits,output_bits=32,attention_mode=attention_mode,interpolate=interpolate,materialized_logit_mismatches=materialized,materialized_route_mismatches=route_parity,scalar_logit_mismatches=scalar_logits,scalar_route_mismatches=scalar_routes,scalar_canonical_boards=len(b) if scalar else 0,public_wrapper_mismatches=public_errors,public_boards_checked=len(data['boards']) if public else 0,statistics=stats,observed_signed_bits=stage_bits,route_boards_different_from_float=int((routes!=teacher_routes).any(1).sum()),route_usage=torch.bincount(routes.flatten(),minlength=c['experts']).tolist(),arithmetic='F9J2 whole integer, INT64 host intermediates; no target acceptance',seconds=time.monotonic()-start)
    result['accepted']=bool(result['accepted'] and materialized==0 and route_parity==0 and scalar_logits==0 and scalar_routes==0 and (public_errors is None or public_errors==0) and inventory['total_bytes']<=8192)
    result['status']='accepted-host-integer' if result['accepted'] else 'rejected'
    (output/'canonical-results.json').write_text(json.dumps(dict(boards=b.tolist(),logits=logits.tolist(),routes=routes.tolist(),float_logits=teacher_logits.tolist(),float_routes=teacher_routes.tolist()),indent=2)+'\n')
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',default=SOURCE);p.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl');p.add_argument('--output',default='artifacts/canonical-integer/direct');p.add_argument('--frac',nargs='+',type=int,default=[8,9,10,11]);p.add_argument('--bits',nargs='+',type=int,default=[8,16]);p.add_argument('--attention',nargs='+',default=['legacy','early','rational']);p.add_argument('--activation-bits',nargs='+',type=int,default=[32]);p.add_argument('--nearest',action='store_true');p.add_argument('--public',action='store_true');p.add_argument('--summary',default='results/canonical-integer-summary.json');a=p.parse_args()
    torch.set_num_threads(1);data=load_data(a.dataset); diagnosis=diagnose_legacy(data); results=[]
    for F in a.frac:
        for bits in a.bits:
            for ab in a.activation_bits:
                for mode in a.attention:
                    tag=f'q{F}-w{bits}-a{ab}-{mode}-'+('nearest' if a.nearest else 'interp')
                    result=evaluate_candidate(a.source,data,Path(a.output)/tag,F,bits,ab,mode,not a.nearest,True,a.public)
                    results.append(result)
                    print(json.dumps({k:result[k] for k in ('artifact','canonical_set_errors','board_move_errors','history_move_errors','total_bytes','status','seconds')}),flush=True)
    accepted=[r for r in results if r['accepted']]
    best=min(accepted,key=lambda r:(r['total_bytes'],r['statistics']['maximum_abs_accumulator'])) if accepted else min(results,key=lambda r:(r['canonical_set_errors'],r['history_move_errors']))
    summary=dict(command=sys.argv,candidates=results,best=best,legacy_range_diagnosis=json.loads(Path('artifacts/integer-range/diagnosis.json').read_text()),training_steps=0,target_6502='unstarted; host exact whole-integer research artifact only',next_stage='assembled range-aware kernels and target lifetime map; no QAT needed for accepted direct conversion')
    summary['provenance']={str(path):dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in [Path(__file__),Path('falken9/canonical_integer.py'),Path('falken9/canonical_integer_export.py'),Path('falken9/range_integer_model.py')]}
    Path(a.summary).write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__': main()
