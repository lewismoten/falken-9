"""Canonical full-optimal-set experiments; no minimax or oracle at inference."""
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
from falken9.canonical_model import predict_sets
from falken9.policy import board_from_history
from falken9.symmetry import canonicalize, transform_move, restore_moves, TRANSFORMS, transform_board

DATASET_SHA256 = 'a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597'
BULK = {'query.weight', 'key.weight', 'value.weight', 'projection.weight', 'expert_w1', 'expert_w2'}


def load_data(path, verify_digest=True):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if verify_digest and digest != DATASET_SHA256:
        raise ValueError('dataset digest mismatch')
    canonical_boards, targets, canonical_index = [], [], {}
    boards, board_indices, transforms, labels, sets, histories, history_indices = [], [], [], [], [], [], []
    unique = {}
    restoration_errors = 0
    for line in path.open():
        row = json.loads(line)
        board = tuple({'.': 0, 'X': 1, 'O': 2}[c] for c in row['board'] if c != '/')
        if board_from_history(row['history']) != board:
            raise ValueError('history/board mismatch')
        full_set = frozenset(row['optimal_moves'])
        if not full_set or any(board[ord(m)-97] for m in full_set):
            raise ValueError('empty or illegal optimal set')
        ordered = [m for m in 'ebdfhcgia' if m in full_set]
        if row['optimal_move'] != ordered[0]:
            raise ValueError('deterministic label/tie mismatch')
        if board not in unique:
            canonical, transform = canonicalize(board)
            canonical_set = frozenset(transform_move(m, transform) for m in full_set)
            target = [float(chr(97+i) in canonical_set) for i in range(9)]
            if canonical not in canonical_index:
                canonical_index[canonical] = len(canonical_boards)
                canonical_boards.append(canonical); targets.append(target)
            ci = canonical_index[canonical]
            if targets[ci] != target:
                raise ValueError('canonical optimal-set conflict')
            restoration_errors += restore_moves(canonical_set, transform) != ordered
            unique[board] = len(boards)
            boards.append(board); board_indices.append(ci); transforms.append(transform)
            labels.append(row['optimal_move']); sets.append(full_set)
        bi = unique[board]
        if labels[bi] != row['optimal_move'] or sets[bi] != full_set:
            raise ValueError('board label conflict')
        histories.append(row['history']); history_indices.append(bi)
    # Exercise every transformation, including stabilizers of symmetric boards.
    transform_errors = 0
    for board, full_set in zip(boards, sets):
        for transform in TRANSFORMS:
            changed = transform_board(board, transform)
            transformed_set = [transform_move(m, transform) for m in full_set]
            transform_errors += set(restore_moves(transformed_set, transform)) != set(full_set)
            canonical, wrapper = canonicalize(changed)
            canonical_set = [transform_move(m, wrapper) for m in transformed_set]
            ci = canonical_index[canonical]
            expected = {chr(97+i) for i, value in enumerate(targets[ci]) if value}
            transform_errors += set(canonical_set) != expected
    return dict(canonical_boards=torch.tensor(canonical_boards, dtype=torch.long), targets=torch.tensor(targets),
                boards=boards, board_canonical_indices=board_indices, transforms=transforms,
                labels=labels, sets=sets, histories=histories, history_indices=torch.tensor(history_indices),
                dataset_sha256=digest, dataset_path=str(path), restoration_errors=restoration_errors,
                transform_errors=transform_errors, transformations_checked=len(boards)*8)


def payload_estimate(model):
    from falken9.canonical_model import encode_model
    payload, inventory = encode_model(model)
    scales=sum(row['scale_count']*4 for row in inventory)
    weights=sum(row['bytes']-row['scale_count']*4 for row in inventory)
    return dict(inventory=inventory, weight_bytes=weights, scale_bytes=scales, header_bytes=16,
                symmetry_and_tie_bytes=81, nonlinearity_lut_bytes=0, alignment_bytes=0,
                total_encoded_bytes=len(payload), parameter_count=sum(p.numel() for p in model.parameters()),
                status='exact F9C1 encoding size; host FP32 arithmetic; no C64 runtime',
                decoder_and_kernel_code_bytes=None, activation_peak_bytes=None,
                fp32_nonlinearities='LayerNorm, sqrt, softmax, GELU; no LUT used by host runtime')


@torch.no_grad()
def packed_gate(model,data,output):
    from falken9.canonical_model import encode_model, decode_model
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    model.cpu().eval()
    payload, inventory=encode_model(model)
    path=output/'model.f9c'; path.write_bytes(payload)
    # Read actual file, independently materialize, then exhaust both paths.
    decoded=decode_model(path.read_bytes()).eval()
    boards=data['canonical_boards']
    a=model(boards); b=decoded(boards)
    result=dict(encoded_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),inventory=inventory,
                max_abs_logit_error=float((a-b).abs().max()),
                routes_equal=bool(torch.equal(model(boards,return_routes=True)[1],decoded(boards,return_routes=True)[1])),
                fake=evaluate(model,data,output/'fake'),decoded=evaluate(decoded,data,output/'decoded'))
    (output/'packed-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


@torch.no_grad()
def evaluate(model, data, output, device='cpu', benchmark=True):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    model.eval(); model.to(device)
    boards = data['canonical_boards'].to(device)
    start = time.perf_counter()
    logits = model(boards)
    forward_seconds = time.perf_counter()-start
    masks = predict_sets(logits, boards).cpu()
    targets = data['targets'].bool()
    canonical_errors = (masks != targets).any(1)
    signed = logits.cpu() * (data['targets']*2-1)
    legal = data['canonical_boards'] == 0
    actual, set_errors, board_errors, counterexamples = [], [], [], []
    restoration_start = time.perf_counter()
    for bi, (board, ci, transform, expected, full_set) in enumerate(zip(data['boards'], data['board_canonical_indices'], data['transforms'], data['labels'], data['sets'])):
        members = [chr(97+i) for i in masks[ci].nonzero().flatten().tolist()]
        restored = restore_moves(members, transform)
        move = restored[0] if restored else None
        actual.append(move); set_errors.append(set(restored) != set(full_set)); board_errors.append(move != expected)
        if set_errors[-1] or board_errors[-1]:
            counterexamples.append(dict(board_index=bi, board=board, canonical_index=ci, transform=transform,
                                        expected_set=sorted(full_set), actual_set=restored, expected_move=expected,
                                        actual_move=move, canonical_logits=logits[ci].cpu().tolist()))
    errors = torch.tensor(board_errors); set_errors_t = torch.tensor(set_errors)
    history_errors = errors[data['history_indices']]
    history_set_errors = set_errors_t[data['history_indices']]
    restoration_seconds = time.perf_counter()-restoration_start
    # Persist all board counterexamples, plus all affected history identifiers.
    (output/'counterexamples.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in counterexamples))
    with (output/'history-counterexamples.jsonl').open('w') as stream:
        for hi in (history_errors | history_set_errors).nonzero().flatten().tolist():
            bi = int(data['history_indices'][hi])
            stream.write(json.dumps(dict(history=data['histories'][hi], board_index=bi,
                                         expected=data['labels'][bi], actual=actual[bi],
                                         move_error=board_errors[bi], set_error=set_errors[bi]))+'\n')
    result = dict(canonical_count=len(boards), board_count=len(board_errors), history_count=len(data['histories']),
                  canonical_set_errors=int(canonical_errors.sum()), canonical_bit_errors=int((masks != targets).sum()),
                  board_move_errors=int(errors.sum()), history_move_errors=int(history_errors.sum()),
                  board_set_errors=int(set_errors_t.sum()), history_set_errors=int(history_set_errors.sum()),
                  empty_canonical_sets=int((masks.sum(1)==0).sum()), minimum_legal_signed_margin=float(signed[legal].min()),
                  restoration_errors=data['restoration_errors'], transform_errors=data['transform_errors'],
                  transformations_checked=data['transformations_checked'], dataset_sha256=data['dataset_sha256'],
                  accepted=not bool(canonical_errors.any()) and not bool(history_errors.any()) and data['transform_errors']==0,
                  history_gate='every validated history indexed into evaluated board-dependent canonical neural outputs; no policy lookup at inference',
                  arithmetic='host FP32 / optional fake weight quantization; NOT integer or C64 accepted',
                  forward_seconds=forward_seconds, restoration_seconds=restoration_seconds)
    if benchmark and device == 'cpu':
        for _ in range(3): model(boards)
        start = time.perf_counter()
        for _ in range(10): model(boards)
        result['cpu_benchmark'] = dict(threads=torch.get_num_threads(), batch=len(boards), repeats=10,
                                      neural_boards_per_second=len(boards)*10/(time.perf_counter()-start),
                                      includes_canonicalization=False, includes_restoration=False,
                                      host_cpu=platform.processor(), target_6502_cycles=None)
    (output/'evaluation.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def train_candidate(model, data, output, steps=3000, seconds=90, lr=.003, seed=11, device='cpu', eval_every=100, teacher=None):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    random.seed(seed); torch.manual_seed(seed); torch.use_deterministic_algorithms(True)
    model.to(device)
    boards, targets = data['canonical_boards'].to(device), data['targets'].to(device)
    legal = boards == 0
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0)
    start = time.monotonic(); best = (len(boards)+1, float('inf')); trace=[]
    for step in range(1, steps+1):
        model.train(); optimizer.zero_grad(set_to_none=True)
        logits = model(boards)
        loss = F.binary_cross_entropy_with_logits(logits[legal], targets[legal])
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5); optimizer.step()
        if step % eval_every == 0 or step == steps or time.monotonic()-start >= seconds:
            model.eval()
            with torch.no_grad():
                logits = model(boards)
                errors = int((predict_sets(logits, boards) != targets.bool()).any(1).sum())
                current_loss = F.binary_cross_entropy_with_logits(logits[legal], targets[legal]).item()
            item = dict(step=step, canonical_set_errors=errors, loss=current_loss, seconds=time.monotonic()-start)
            trace.append(item); print(json.dumps(dict(candidate=output.name, **item)), flush=True)
            if (errors,current_loss) < best:
                best=(errors,current_loss)
                torch.save(dict(config=asdict(model.config), state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                                step=step, seed=seed, loss=current_loss, canonical_set_errors=errors, teacher=teacher), output/'best.pt')
            if errors == 0 or time.monotonic()-start >= seconds: break
    checkpoint=torch.load(output/'best.pt', map_location=device, weights_only=False)
    model.load_state_dict(checkpoint['state_dict'])
    gate=evaluate(model,data,output,device)
    result=dict(config=asdict(model.config), seed=seed, lr=lr, loss_contract='BCE on all legal canonical set memberships; zero-logit threshold',
                requested_steps=steps, steps_completed=step, seconds=time.monotonic()-start, best_step=checkpoint['step'],
                teacher=teacher, trainable_tensors=[n for n,p in model.named_parameters() if p.requires_grad],
                checkpoint=str(output/'best.pt'), checkpoint_sha256=hashlib.sha256((output/'best.pt').read_bytes()).hexdigest(),
                checkpoint_bytes=(output/'best.pt').stat().st_size, gate=gate, trace=trace, payload_estimate=payload_estimate(model),
                environment=dict(python=sys.version, torch=torch.__version__, cuda=torch.version.cuda, device=device,
                                 platform=platform.platform(), threads=torch.get_num_threads(), argv=sys.argv,
                                 env={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','PYTHONPATH','CUDA_VISIBLE_DEVICES']}))
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def run_quantized_stage(teacher_path,data,output,precision,island_precision='float',steps=4000,seconds=60,lr=.001,seed=11):
    """Direct materialization, then bounded QAT from a passing teacher.

    Island-only stages freeze non-island tensors. Bulk stages explicitly allow
    full-network adaptation, with every trainable name recorded.
    """
    from falken9.canonical_model import CanonicalPolicy, CanonicalConfig, ISLANDS
    import struct
    teacher_path=Path(teacher_path); output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    checkpoint=torch.load(teacher_path,map_location='cpu',weights_only=False)
    if checkpoint['canonical_set_errors'] != 0:
        raise ValueError('teacher has not passed full-set gate')
    config=CanonicalConfig(checkpoint['config']['width'],checkpoint['config']['expert_width'],precision,island_precision)
    model=CanonicalPolicy(config); model.load_state_dict(checkpoint['state_dict'])
    teacher=dict(path=str(teacher_path),sha256=hashlib.sha256(teacher_path.read_bytes()).hexdigest())
    direct=packed_gate(model,data,output/'direct')
    direct_pass=direct['fake']['accepted'] and direct['decoded']['accepted'] and direct['max_abs_logit_error']==0
    frozen={}
    if precision=='float' and island_precision!='float':
        for name,p in model.named_parameters():
            if name not in ISLANDS:
                p.requires_grad_(False); frozen[name]=p.detach().clone()
    frozen_digests={name:hashlib.sha256(struct.pack('<'+'f'*p.numel(),*p.flatten().tolist())).hexdigest() for name,p in frozen.items()}
    if direct_pass:
        torch.save(dict(config=asdict(config),state_dict=model.state_dict(),step=0,seed=seed,canonical_set_errors=0,teacher=teacher),output/'best.pt')
        result=dict(config=asdict(config),seed=seed,lr=lr,steps_completed=0,best_step=0,teacher=teacher,
                    checkpoint=str(output/'best.pt'),checkpoint_sha256=hashlib.sha256((output/'best.pt').read_bytes()).hexdigest(),
                    payload_estimate=payload_estimate(model),gate=direct['decoded'],trainable_tensors=[],seconds=0)
        status='accepted-direct-materialization'
    else:
        result=train_candidate(model,data,output,steps=steps,seconds=seconds,lr=lr,seed=seed,teacher=teacher)
        status='accepted-QAT' if result['gate']['accepted'] else 'rejected-bounded-QAT'
    identity=all(torch.equal(dict(model.named_parameters())[name].detach(),p) for name,p in frozen.items())
    if not identity: raise AssertionError('frozen tensor changed')
    packed=packed_gate(model,data,output/'packed')
    result.update(status=status,direct=direct,packed=packed,frozen_byte_identity=identity,frozen_sha256=frozen_digests)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
