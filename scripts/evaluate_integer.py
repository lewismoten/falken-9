"""Materialize offline, then exhaustively evaluate integer-only CPU inference."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from falken9.integer_export import convert,save,load
from falken9.integer_model import IntegerPolicy,select_moves
from falken9.training import load_dataset


def evaluate_candidate(source,data,output,bits=8,frac=8,scalar_oracle=False):
    torch.set_num_threads(1)
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    source=Path(source); digest=hashlib.sha256(source.read_bytes()).hexdigest()
    start=time.monotonic()
    checkpoint=torch.load(source,map_location='cpu',weights_only=False)
    candidate=convert(checkpoint,bulk_bits=bits,frac=frac)
    path=output/'model.f9i'; inventory=save(candidate,path)
    runtime=IntegerPolicy(load(path)); memory=IntegerPolicy(candidate)
    predictions=[]; logits=[]; routes=[]; parity=0
    for boards in data['boards'].split(256):
        a,r=runtime(boards,return_routes=True); b=memory(boards)
        parity+=int((a!=b).sum()); predictions.append(select_moves(a,boards)); logits.extend(a.tolist());routes.extend(r.tolist())
    predictions=torch.cat(predictions)
    misses=predictions!=data['labels']; history_misses=misses[data['history_indices']]
    with (output/'counterexamples.jsonl').open('w') as stream:
        for i in history_misses.nonzero().flatten().tolist():
            b=int(data['history_indices'][i])
            stream.write(json.dumps(dict(history=data['histories'][i],board_index=b,board=data['boards'][b].tolist(),expected=int(data['labels'][b]),actual=int(predictions[b]),logits=logits[b],routes=routes[b]))+'\n')
    scalar_logits=scalar_routes=None
    if scalar_oracle:
        spec=importlib.util.spec_from_file_location('independent_integer_oracle',Path(__file__).resolve().parents[1]/'tests/test_integer_model.py')
        oracle=importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
        scalar_logits=scalar_routes=0
        for i,board in enumerate(data['boards'].tolist()):
            expected,route=oracle.scalar_oracle(candidate,board)
            scalar_logits+=sum(a!=b for a,b in zip(expected,logits[i]))
            scalar_routes+=sum(a!=b for a,b in zip(route,routes[i]))
    (output/'board-results.json').write_text(json.dumps(dict(logits=logits,routes=routes,predictions=predictions.tolist())))
    S=1<<frac; width=candidate['width']
    bounds=dict(matrix_dot_absolute_bound=9*width*32768*128,
                attention_dot_absolute_bound=width*32768**2,
                attention_scaled_absolute_bound=width*32768**2*candidate['attention_factor'],
                layernorm_square_sum_absolute_bound=width*65535**2,
                layernorm_affine_loose_absolute_bound=65535*S*32768,
                weighted_probability_absolute_bound=32768**2,
                largest_matrix_rescale_loose_absolute_bound=9*width*32768*128*(1<<16),
                int32_whole_model_safe=False,int64_whole_model_safe=True)
    assert max(v for v in bounds.values() if type(v) is int)<2**63
    result=dict(bounds=bounds,source=str(source),source_sha256=digest,source_sha256_after=hashlib.sha256(source.read_bytes()).hexdigest(),artifact=str(path),artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bits=bits,frac=frac,**inventory,board_count=len(misses),history_count=data['history_count'],board_mismatches=int(misses.sum()),history_mismatches=int(history_misses.sum()),materialized_logit_mismatches=parity,scalar_oracle_logit_mismatches=scalar_logits,scalar_oracle_route_mismatches=scalar_routes,scalar_oracle_boards=len(misses) if scalar_oracle else 0,dataset_sha256=data['dataset_sha256'],board_dependent_by_construction=True,arithmetic='integer-only INT64 host oracle; INT16 activations, no C64 claim',overflow_count=0,overflow_count_basis='checked analytic INT64 bounds; Python scalar arbitrary-width exhaustive oracle when enabled',statistics=runtime.stats,seconds=time.monotonic()-start)
    result['accepted']=not result['history_mismatches'] and parity==0 and scalar_logits==0 and scalar_routes==0
    result['status']='accepted' if result['accepted'] else 'rejected'
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--checkpoint',default='artifacts/training/float-search/w8-h8-float/best.pt')
    parser.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl')
    parser.add_argument('--output',default='artifacts/integer')
    parser.add_argument('--bits',type=int,nargs='+',default=[8,4])
    parser.add_argument('--frac',type=int,nargs='+',default=[8])
    parser.add_argument('--scalar-oracle',action='store_true')
    parser.add_argument('--summary',default='results/integer-summary.json')
    args=parser.parse_args(); torch.set_num_threads(1)
    data=load_dataset(args.dataset); results=[]
    for frac in args.frac:
        for bits in args.bits:
            result=evaluate_candidate(args.checkpoint,data,Path(args.output)/f'w8-int{bits}-q{frac}',bits,frac,args.scalar_oracle)
            results.append(result)
            print(json.dumps({k:result[k] for k in ['artifact','artifact_sha256','board_mismatches','history_mismatches','total_bytes','status','seconds']}),flush=True)
    summary=dict(command=sys.argv,candidates=results,live_process_status='this synchronous evaluator completed; no owned background processes',c64_full_model='unstarted',model_residency='unstarted',next_scoped_qat_change='One trainable-scope change only: unfreeze norm2.weight and norm2.bias, freeze every other predecessor tensor, and optimize through a surrogate matching this exact integer forward. Re-run materialized/scalar exhaustive gates. No training executed; no guarantee this scope fixes all misses.')
    summary['interpreter']=sys.executable
    summary['provenance']={str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [Path(__file__),Path('falken9/integer_model.py'),Path('falken9/integer_export.py'),Path('tests/test_integer_model.py')]}
    summary['storage_boundary']=dict(encoded_model_includes=['all parameters','all exponents','all descriptors','both LUTs','header'],host_decoded_code_tensor_bytes=2442*8,host_decoded_lut_tensor_bytes=1026*8,host_python_metadata_bytes='unmeasured',scratch=dict(peak_host_bytes='unmeasured; vectorized batch 256, INT64 physical tensors',target_peak_bytes='unstarted; no allocated target lifetime map',logical_int16_token_tensor_bytes=9*8*2,logical_int16_qkv_bytes=3*9*8*2,logical_uint16_attention_probabilities_bytes=9*9*2,logical_int16_attention_scores_bytes=9*9*2),target_code_bytes='unstarted; no compiled whole-model binary')
    Path(args.summary).write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__': main()
