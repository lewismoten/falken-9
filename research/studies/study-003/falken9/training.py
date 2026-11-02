"""Self-contained supervised training and complete history gate; no game solver."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import os
import platform
import random
import sys
import time
import torch
from torch.nn import functional as F
from falken9.model import select_moves


def load_dataset(path):
    path = Path(path)
    boards, labels, histories, indices, unique = [], [], [], [], {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        board = tuple({'.':0,'X':1,'O':2}[c] for c in row['board'] if c != '/')
        if len(board) != 9: raise ValueError('invalid board length')
        label = ord(row['optimal_move'])-ord('a')
        if board[label] != 0: raise ValueError('occupied target')
        if board not in unique:
            unique[board] = len(boards); boards.append(board); labels.append(label)
        index = unique[board]
        if labels[index] != label: raise ValueError('inconsistent board labels')
        histories.append(row['history']); indices.append(index)
    return dict(boards=torch.tensor(boards,dtype=torch.long), labels=torch.tensor(labels,dtype=torch.long),
                histories=histories, history_indices=torch.tensor(indices), history_count=len(histories),
                dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), dataset_path=str(path),
                label_consistency=True)


@torch.no_grad()
def evaluate(model, data, output, device='cpu'):
    output = Path(output); output.mkdir(parents=True,exist_ok=True)
    model.eval()
    predictions=[]; losses=[]
    for boards, labels in zip(data['boards'].split(512),data['labels'].split(512)):
        logits=model(boards.to(device))
        predictions.append(select_moves(logits,boards.to(device)).cpu())
        losses.append(F.cross_entropy(logits.masked_fill(boards.to(device)!=0,-torch.inf),labels.to(device),reduction='sum').item())
    predictions=torch.cat(predictions)
    misses=predictions != data['labels']
    history_misses=misses[data['history_indices']]
    with (output/'counterexamples.jsonl').open('w') as stream:
        for i in history_misses.nonzero().flatten().tolist():
            b=int(data['history_indices'][i])
            stream.write(json.dumps(dict(history=data['histories'][i],board=data['boards'][b].tolist(),expected=chr(97+int(data['labels'][b])),actual=chr(97+int(predictions[b]))))+'\n')
    result=dict(board_count=len(misses),history_count=data['history_count'],board_mismatches=int(misses.sum()),history_mismatches=int(history_misses.sum()),loss=sum(losses)/len(misses),accepted=not bool(misses.any()),dataset_sha256=data['dataset_sha256'],board_dependent_by_construction=True,label_consistency=data['label_consistency'],arithmetic='host-float-or-fake-quant; NOT integer/C64 accepted')
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def packed_gate(model, data, output):
    """CPU fake/materialized exhaustive parity; not an integer arithmetic gate."""
    from falken9.export import export_model, load_packed
    from falken9.model import CompactPolicy
    output=Path(output)
    metadata=export_model(model,output/'model.f9q')
    decoded=load_packed(output/'model.f9q')
    fake=CompactPolicy(model.config).cpu().eval()
    fake.load_state_dict({k:v.detach().cpu() for k,v in model.state_dict().items()})
    maximum=0.
    with torch.no_grad():
        for boards in data['boards'].split(512):
            maximum=max(maximum,float((fake(boards)-decoded(boards)).abs().max()))
    result=dict(metadata=metadata,parity_max_abs_logit_error=maximum,fake_cpu_gate=evaluate(fake,data,output/'fake-cpu','cpu'),decoded_gate=evaluate(decoded,data,output/'decoded-cpu','cpu'))
    (output/'packed-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def train_candidate(model,data,output,steps=2000,seconds=120,lr=.003,seed=11,device='cuda',eval_every=100):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    model.to(device)
    boards=data['boards'].to(device); labels=data['labels'].to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0)
    best=(len(boards)+1,float('inf')); start=time.monotonic(); trace=[]
    for step in range(1,steps+1):
        model.train(); optimizer.zero_grad(set_to_none=True)
        logits=model(boards).masked_fill(boards != 0,-torch.inf)
        loss=F.cross_entropy(logits,labels)
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5); optimizer.step()
        if step%eval_every==0 or step==steps or time.monotonic()-start>=seconds:
            model.eval()
            with torch.no_grad():
                logits=model(boards); count=int((select_moves(logits,boards)!=labels).sum())
                current_loss=F.cross_entropy(logits.masked_fill(boards!=0,-torch.inf),labels).item()
            trace.append(dict(step=step,loss=current_loss,board_mismatches=count,seconds=time.monotonic()-start))
            print(json.dumps(dict(candidate=output.name,**trace[-1])),flush=True)
            if (count,current_loss)<best:
                best=(count,current_loss)
                torch.save(dict(config=asdict(model.config),state_dict=model.state_dict(),step=step,seed=seed,loss=current_loss,board_mismatches=count),output/'best.pt')
            if count==0 or time.monotonic()-start>=seconds: break
    checkpoint=torch.load(output/'best.pt',map_location=device,weights_only=False)
    model.load_state_dict(checkpoint['state_dict'])
    gate=evaluate(model,data,output,device)
    inventory={name:dict(shape=list(p.shape),elements=p.numel(),bytes=p.numel()*p.element_size()) for name,p in model.named_parameters()}
    result=dict(config=asdict(model.config),seed=seed,lr=lr,requested_steps=steps,steps_completed=step,best_step=checkpoint['step'],seconds=time.monotonic()-start,checkpoint=str(output/'best.pt'),checkpoint_sha256=hashlib.sha256((output/'best.pt').read_bytes()).hexdigest(),checkpoint_bytes=(output/'best.pt').stat().st_size,parameter_count=sum(p.numel() for p in model.parameters()),float_tensor_bytes=sum(p.numel()*p.element_size() for p in model.parameters()),inventory=inventory,trace=trace,gate=gate,environment=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0) if device=='cuda' else None,platform=platform.platform(),argv=sys.argv,env={k:os.environ.get(k) for k in ['CUBLAS_WORKSPACE_CONFIG','OMP_NUM_THREADS','PYTHONPATH','CUDA_VISIBLE_DEVICES']}))
    if model.config.precision != 'float':
        result['packed']=packed_gate(model,data,output)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
