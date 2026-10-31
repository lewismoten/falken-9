"""Bounded CPU training with exact canonical-set gates and recorded lineage."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import platform
import random
import sys
import time
import torch
from torch.nn import functional as F
from falken9.canonical_training import evaluate
from falken9.canonical_model import predict_sets
from falken9.flexible_model import FlexiblePolicy, FlexibleConfig
from falken9.flexible_export import encode_model, decode_model


def initialize_from_checkpoint(model,path,selected_experts=None):
    path = Path(path)
    checkpoint = torch.load(path,map_location='cpu',weights_only=False)
    state = checkpoint['state_dict']
    selected_experts = selected_experts if selected_experts is not None else list(range(model.config.experts))
    if len(selected_experts) != model.config.experts or len(set(selected_experts)) != len(selected_experts):
        raise ValueError('invalid selected expert bank')
    own = model.state_dict()
    for name in own:
        value = state[name]
        if name.startswith('expert_') or name.startswith('router.'):
            value = value[selected_experts]
        if own[name].shape != value.shape: raise ValueError('incompatible source dimensions')
        own[name] = value.clone()
    model.load_state_dict(own)
    return dict(kind='checkpoint-selected-bank-warmstart',source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                selected_experts=selected_experts,source_config=checkpoint['config'])


@torch.no_grad()
def route_inventory(model,boards):
    _,routes = model(boards,return_routes=True)
    c=model.config; d,h,e,k=c.width,c.expert_width,c.experts,c.active
    counts=torch.bincount(routes.flatten(),minlength=e).tolist()
    entries=[]
    for index in range(e):
        entries.append(dict(expert=index,selections=counts[index],weight_elements=2*d*h,bias_elements=h+d,
                            tensors={name:dict(shape=list(p[index].shape),elements=p[index].numel(),
                                              l1=float(p[index].abs().sum()))
                                     for name,p in model.named_parameters() if name.startswith('expert_')}))
    shared=4*9*d*d+2*81*d+9*d*d+e*d+9*d
    return dict(canonical_selection_counts=counts,participating_experts=sum(x>0 for x in counts),
                distinct_routes=len(set(tuple(x) for x in routes.tolist())),sparse=k<e,
                gating='selected-full-E-softmax' if k==1 else 'selected-K-softmax',
                expert_macs_per_board=k*2*d*h,shared_macs_per_board=shared,total_macs_per_board=shared+k*2*d*h,
                training_expert_macs_forward_per_board=k*2*d*h,inference_expert_macs_per_board=k*2*d*h,
                training_backward='autograd through selected K banks and gate; additional backward work not included in forward MACs',
                deployment='gathers only selected K expert matrices; stable lower-ID routing ties',
                excludes='embedding additions, normalization, nonlinearities, biases, sorting, softmax and wrapper; NOT 6502 cycles',
                per_expert_weights=entries)


@torch.no_grad()
def packed_gate(model,data,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    model.cpu().eval()
    payload,inventory=encode_model(model)
    path=output/'model.f9f'; path.write_bytes(payload)
    decoded=decode_model(path.read_bytes()).eval()
    boards=data['canonical_boards']
    a,ar=model(boards,return_routes=True); b,br=decoded(boards,return_routes=True)
    result=dict(encoded_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),inventory=inventory,
                max_abs_logit_error=float((a-b).abs().max()),routes_equal=torch.equal(ar,br),
                decoded=evaluate(decoded,data,output/'decoded',benchmark=False),routes=route_inventory(decoded,boards),
                byte_ledger=dict(header=24,coordinate_wrapper=81,tensors=sum(x['bytes'] for x in inventory),
                                 scales=sum(x['scale_count']*4 for x in inventory),
                                 fp32_vector_islands=sum(x['bytes'] for x in inventory if x['bits']==32 and len(x['shape'])==1),
                                 total_fp32_tensor_bytes=sum(x['bytes'] for x in inventory if x['bits']==32),
                                 lut=0,alignment=0,total=len(payload),decoder_kernel_bytes=None),
                arithmetic=f'{model.config.precision} stored matrices / FP32 vector islands and nonlinearities; no integer/C64 claim')
    (output/'packed-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def policy_loss(logits,targets,legal,hard_mining=0):
    """Full legal-bit BCE plus optional worst-64-pattern BCE; labels unchanged."""
    losses=F.binary_cross_entropy_with_logits(logits,targets,reduction='none')
    base=losses[legal].mean()
    per_board=(losses*legal).sum(1)/legal.sum(1).clamp_min(1)
    return base+hard_mining*per_board.topk(min(64,len(per_board))).values.mean()


def train_candidate(model,data,output,steps=6000,seconds=60,lr=.003,seed=11,eval_every=100,lineage=None,hard_mining=0):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    random.seed(seed); torch.manual_seed(seed); torch.use_deterministic_algorithms(True)
    model.cpu(); boards=data['canonical_boards']; targets=data['targets']; legal=boards==0
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0)
    best=(len(boards)+1,float('inf')); trace=[]; start=time.monotonic(); router_gradient=0
    for step in range(1,steps+1):
        model.train(); optimizer.zero_grad(set_to_none=True)
        logits=model(boards)
        loss=policy_loss(logits,targets,legal,hard_mining)
        loss.backward()
        router_gradient=max(router_gradient,float(model.router.weight.grad.abs().sum()))
        torch.nn.utils.clip_grad_norm_(model.parameters(),5); optimizer.step()
        if step%eval_every==0 or step==steps or time.monotonic()-start>=seconds:
            model.eval()
            with torch.no_grad():
                logits=model(boards)
                errors=int((predict_sets(logits,boards)!=targets.bool()).any(1).sum())
                value=F.binary_cross_entropy_with_logits(logits[legal],targets[legal]).item()
            item=dict(step=step,errors=errors,loss=value,seconds=time.monotonic()-start)
            trace.append(item); print(json.dumps(dict(candidate=output.name,**item)),flush=True)
            if (errors,value)<best:
                best=(errors,value)
                torch.save(dict(config=asdict(model.config),state_dict={n:p.detach().clone() for n,p in model.state_dict().items()},
                                step=step,seed=seed,hard_mining=hard_mining,canonical_set_errors=errors,lineage=lineage or {'kind':'from-scratch'}),output/'best.pt')
            if errors==0 or time.monotonic()-start>=seconds: break
    checkpoint=torch.load(output/'best.pt',map_location='cpu',weights_only=False)
    model.load_state_dict(checkpoint['state_dict'])
    gate=evaluate(model,data,output/'float-or-qat',benchmark=False)
    packed=packed_gate(model,data,output/'packed')
    result=dict(config=asdict(model.config),hard_mining=hard_mining,seed=seed,lr=lr,steps_completed=step,best_step=checkpoint['step'],seconds=time.monotonic()-start,
                gate=gate,packed=packed,lineage=checkpoint['lineage'],router_max_gradient_l1=router_gradient,
                checkpoint=str(output/'best.pt'),checkpoint_sha256=hashlib.sha256((output/'best.pt').read_bytes()).hexdigest(),
                checkpoint_bytes=(output/'best.pt').stat().st_size,trace=trace,
                ranking='canonical complete-set error count, then BCE; no policy oracle at inference',
                environment=dict(python=sys.version,torch=torch.__version__,device='cpu',threads=torch.get_num_threads(),
                                 platform=platform.platform(),argv=sys.argv),
                accepted=gate['accepted'] and packed['decoded']['accepted'] and packed['max_abs_logit_error']==0 and packed['routes_equal']
                         and packed['routes']['participating_experts']>1 and router_gradient>0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
