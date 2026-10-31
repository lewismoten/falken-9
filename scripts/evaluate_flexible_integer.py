"""Pinned effective F9F1 -> F9J2 exhaustive CPU-only direct conversion gates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from falken9.flexible_export import decode_model
from falken9.flexible_integer import FlexibleIntegerPolicy
from falken9.flexible_integer_export import convert,save,load
from falken9.canonical_training import load_data,evaluate
from falken9.integer_export import MATRICES

SOURCE = 'artifacts/flexible/refine-scratch/w8-h4-e4-k2-float-s23/packed/model.f9f'
SOURCE_SHA = '1dfbca8f62beeb000334c8a1163c0aaa3a50a858cbc3e5f3605ed4b589d6ce33'


def bits(value):
    return max(1,int(value).bit_length()+1)


def inventory_detail(c, inventory):
    tensors=[]
    for name,t in c['tensors'].items():
        q=t['codes']; tensors.append(dict(name=name,shape=list(q.shape),bits=t['bits'],
            bytes=q.numel()*t['bits']//8,exponent_bytes=len(t['exponents']),
            exponents=t['exponents'],category='matrix' if name in MATRICES else 'affine_or_embedding'))
    d,h,k=c['width'],c['expert_width'],c['topk']
    # Explicit conservative non-aliasing *proposed* scalar target schedule,
    # not Torch allocations and not an implemented target lifetime map.
    scratch=dict(token_vectors_7x9xd_int32=7*9*d*4,attention_scores_int32=81*4,
        attention_probabilities_uint16=81*2,global_vectors_8xd_int32=8*d*4,
        selected_expert_hidden_int32=k*h*4,selected_expert_output_int32=k*d*4,
        router_scores_int32=c['experts']*4,selected_indices_and_gates=k*3,
        output_logits_int32=9*4,scalar_wide_temporaries_16x8=16*8,
        board_and_wrapper_work_4x9=4*9)
    external=['falken9/flexible_integer.py','falken9/flexible_integer_export.py',
        'falken9/canonical_integer.py','falken9/canonical_integer_export.py','falken9/integer_model.py',
        'falken9/policy.py','falken9/symmetry.py','falken9/integer_export.py']
    matrix_elements=sum(t['codes'].numel() for n,t in c['tensors'].items() if n in MATRICES)
    matrix_bytes=sum(t['codes'].numel()*t['bits']//8 for n,t in c['tensors'].items() if n in MATRICES)
    exponent_bytes=sum(len(t['exponents']) for t in c['tensors'].values())
    macs_by_matrix={name:9*d*d for name in ('query.weight','key.weight','value.weight','projection.weight','readout.weight')}
    macs_by_matrix.update({'router.weight':c['experts']*d,'expert_w1':k*d*h,'expert_w2':k*d*h,'output.weight':9*d})
    dense_macs=sum(macs_by_matrix.values())
    reduced_macs=sum(count for name,count in macs_by_matrix.items() if c['tensors'][name]['bits']==8)
    return dict(packet=inventory,tensors=tensors,matrix_elements=matrix_elements,matrix_bytes=matrix_bytes,
        affine_and_embedding_bytes=inventory['parameter_bytes']-matrix_bytes,exponent_bytes=exponent_bytes,
        structural_descriptor_bytes=inventory['descriptor_and_scale_bytes']-exponent_bytes,
        logical_macs=dict(matrix_projections=dense_macs,attention_qk_and_pv=2*81*d,total=dense_macs+2*81*d),
        mixed_int8_projection_macs=reduced_macs,
        operation_cost_status='structural MAC counts only; INT8 storage does not prove faster C64 execution; no target cycles measured',
        scratch_proposal=scratch,
        scratch_proposal_total_bytes=sum(scratch.values()),
        scratch_status='conservative non-aliasing schedule proposal, not implemented target residency; host Torch memory excluded',
        external_host_sources={p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in external},
        decoder_kernel_6502_code_bytes=None,zero_page_bytes=None,stack_bytes=None,
        target_memory_capacity_assumed=None,target_residency_proven=False,
        floating_inference_tensors=0,compression='none; no decompression or float scales')


def diagnose(teacher, c, boards, logits, targets):
    """Localize sign failures against effective float layers without changing weights."""
    float_trace={}; handles=[]
    names={'norm1':'norm1','query':'query.weight','key':'key.weight','value':'value.weight',
           'projection':'projection.weight','readout':'readout.weight','norm2':'norm2',
           'router':'router.weight','output':'output.weight'}
    for name,key in names.items():
        def hook(module,args,result,key=key): float_trace[key]=result.detach().clone()
        handles.append(teacher.get_submodule(name).register_forward_hook(hook))
    with torch.no_grad(): fl,fr=teacher(boards,return_routes=True)
    for handle in handles: handle.remove()
    runtime=FlexibleIntegerPolicy(c,trace=True); il,ir=runtime(boards,True)
    failed=(((il>=0)!=targets.bool()) & (boards==0)).any(1)
    rows=[]
    for index in failed.nonzero().flatten().tolist():
        layers={}
        for name,ft in float_trace.items():
            it=runtime.trace.get(name)
            if it is not None and ft.shape==it.shape:
                delta=it[index].double()/(1<<c['frac'])-ft[index].double()
                layers[name]=dict(max_abs_difference=float(delta.abs().max()),float=ft[index].tolist(),integer=it[index].tolist())
        legal=boards[index]==0
        sign=(targets[index]*2-1)
        rows.append(dict(canonical_index=index,board=boards[index].tolist(),target=targets[index].tolist(),
            float_logits=fl[index].tolist(),integer_logits=il[index].tolist(),
            float_minimum_legal_signed_margin=float((fl[index]*sign)[legal].min()),
            integer_minimum_legal_signed_margin=int((il[index]*sign)[legal].min()),
            float_routes=fr[index].tolist(),integer_routes=ir[index].tolist(),layer_differences=layers))
    return rows


def evaluate_candidate(data, output, frac=11, matrix_bits=16, component_int8=(), public=True):
    start=time.monotonic(); output=Path(output);output.mkdir(parents=True,exist_ok=True)
    raw=Path(SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise ValueError('immutable effective F9F1 SHA mismatch')
    teacher=decode_model(raw).eval()
    c=convert(teacher,frac,matrix_bits,32,'early',True,component_int8)
    path=output/'model.f9j'; inventory=save(c,path); decoded=load(path)
    boards=data['canonical_boards']; runtime=FlexibleIntegerPolicy(decoded)
    logits,routes=runtime(boards,True); stats=json.loads(json.dumps(runtime.stats))
    ml,mr=FlexibleIntegerPolicy(c)(boards,True)
    result=evaluate(runtime,data,output,benchmark=False)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
    spec=importlib.util.spec_from_file_location('independent_scalar',Path('tests/test_canonical_integer_model.py'))
    oracle=importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
    sl=sr=0
    for index,board in enumerate(boards.tolist()):
        expected,expected_route=oracle.scalar_oracle(decoded,board)
        sl+=sum(a!=b for a,b in zip(expected,logits[index].tolist()))
        sr+=sum(a!=b for a,b in zip(expected_route,routes[index].tolist()))
    public_errors=None
    if public:
        representatives={}
        for history,bi in zip(data['histories'],data['history_indices'].tolist()): representatives.setdefault(bi,history)
        public_errors=0
        for bi,history in representatives.items():
            try: prediction=runtime.predict_history(history)
            except ValueError: prediction=None
            public_errors+=prediction!=data['labels'][bi]
    with torch.no_grad(): fl,fr=teacher(boards,return_routes=True)
    parity=int((logits!=ml).sum()); rp=int((routes!=mr).sum())
    result.update(inventory,source=SOURCE,source_sha256=SOURCE_SHA,
        source_sha256_after=hashlib.sha256(Path(SOURCE).read_bytes()).hexdigest(),
        artifact=str(path),artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        config=dict(width=c['width'],expert_width=c['expert_width'],experts=c['experts'],topk=c['topk'],
            frac=frac,matrix_bits=matrix_bits,component_int8=list(component_int8),activation_bits=32,
            output_bits=32,attention_mode='early',interpolate=True),
        materialized_logit_mismatches=parity,materialized_route_mismatches=rp,
        scalar_logit_mismatches=sl,scalar_route_mismatches=sr,scalar_boards=len(boards),
        public_wrapper_mismatches=public_errors,public_boards_checked=len(data['boards']) if public else 0,
        route_usage=torch.bincount(routes.flatten(),minlength=c['experts']).tolist(),
        route_boards_different_from_float=int((routes!=fr).any(1).sum()),
        statistics=stats,observed_signed_bits={n:bits(v) for n,v in stats['accumulators'].items()},
        matrix_envelope_signed_bits={n:bits(v) for n,v in stats['matrix_dot_envelope_bounds'].items()},
        operation_envelope_signed_bits={n:bits(v) for n,v in stats['operation_envelope_bounds'].items()},
        inventory_detail=inventory_detail(c,inventory),training_steps=0,trainable_tensors=[],
        arithmetic='F9J2 whole-integer CPU reference, integer-only nonlinearities, INT64 host intermediates; NOT 6502 acceptance',
        seconds=time.monotonic()-start)
    result['accepted']=bool(result['accepted'] and parity==rp==sl==sr==0 and public_errors==0 and result['source_sha256_after']==SOURCE_SHA)
    result['status']='accepted-host-integer' if result['accepted'] else 'rejected'
    (output/'canonical-results.json').write_text(json.dumps(dict(boards=boards.tolist(),targets=data['targets'].tolist(),
        logits=logits.tolist(),routes=routes.tolist(),float_logits=fl.tolist(),float_routes=fr.tolist()),indent=2)+'\n')
    if not result['accepted']:
        (output/'layer-diagnosis.json').write_text(json.dumps(diagnose(teacher,decoded,boards,logits,data['targets']),indent=2)+'\n')
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--frac',type=int,default=11);parser.add_argument('--bits',type=int,default=16)
    parser.add_argument('--component-int8',nargs='*',default=[])
    parser.add_argument('--output',default='artifacts/flexible-integer/q11-w16-a32-early-interp')
    parser.add_argument('--summary',default='results/flexible-integer-summary.json')
    args=parser.parse_args(); torch.set_num_threads(1)
    data=load_data('data/nonterminal-legal-histories.jsonl')
    result=evaluate_candidate(data,args.output,args.frac,args.bits,args.component_int8)
    summary_path=Path(args.summary)
    summary=json.loads(summary_path.read_text()) if summary_path.exists() else dict(candidates=[])
    summary['candidates']=[r for r in summary['candidates'] if r['artifact']!=result['artifact']]+[result]
    accepted=[r for r in summary['candidates'] if r['accepted']]
    summary['best']=min(accepted,key=lambda r:(r['total_bytes'],r['statistics']['maximum_abs_accumulator'])) if accepted else None
    summary['training_steps']=0; summary['target_6502']='not tested; no residency/physical-hardware claim'
    summary['scope']='direct effective-source conversion only; no QAT, trainable tensors, oracle, or source edits'
    summary['candidate_count']=len(summary['candidates'])
    summary['accepted_count']=len(accepted)
    summary['preferred_runtime_baseline']='artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
    summary['preferred_precision_preserving_mixed']='artifacts/flexible-integer/q11-mixed-e2-output-projection/model.f9j'
    summary['cost_selection_note']='best sorts encoded bytes then observed accumulator magnitude; not measured C64 cycles'
    summary['evaluator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('artifact','artifact_sha256','canonical_set_errors','board_move_errors','history_move_errors','total_bytes','route_usage','status','seconds')}),flush=True)


if __name__=='__main__': main()
