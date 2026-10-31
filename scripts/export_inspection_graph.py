#!/usr/bin/env python3
"""Export accepted F9J2 arithmetic as portable, exact INT64 ONNX functions.

No training, floating-point inference, board lookup or custom runtime kernels.
Run from the repository: .venv/bin/python scripts/export_inspection_graph.py
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import onnx
from onnx import helper as H, numpy_helper as NH, TensorProto as T

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from falken9.canonical_integer_export import load

PACKET = ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
EXPECTED = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
DOMAIN = 'org.falken9.integer'


class Builder:
    def __init__(self):
        self.nodes = []
        self.i = 0

    def op(self, kind, *inputs, **attrs):
        self.i += 1
        out = f'{kind}_{self.i}'
        self.nodes.append(H.make_node(kind, list(inputs), [out], name=out, **attrs))
        return out

    def c(self, value):
        return self.op('Constant', value=NH.from_array(np.asarray(value, dtype=np.int64)))

    def sum(self, x, axis, keep=1):
        return self.op('ReduceSum', x, self.c([axis]), keepdims=keep)

    def unsq(self, x, axis):
        return self.op('Unsqueeze', x, self.c([axis]))

    def clamp(self, x, lo, hi):
        return self.op('Min', self.op('Max', x, self.c(lo)), self.c(hi))

    def sat(self, x):
        return self.clamp(x, -(1 << 31), (1 << 31)-1)

    def rd(self, x, denominator):
        if not isinstance(denominator, str):
            denominator = self.c(denominator)
        half = self.op('Div', denominator, self.c(2))
        positive = self.op('Div', self.op('Add', self.op('Abs', x), half), denominator)
        # ORT 1.31.1 CPU Sign(INT64) misclassifies some positive values >2**31.
        sign = self.op('Where', self.op('Less', x, self.c(0)), self.c(-1), self.c(1))
        return self.op('Mul', sign, positive)

    def norm(self, x, weight, bias):
        centered = self.op('Sub', x, self.rd(self.sum(x, -1), 8))
        var = self.op('Add', self.rd(self.sum(self.op('Mul', centered, centered), -1), 8), self.c(42))
        root = self.op('Mul', var, self.c(0))
        # Full 31-bit floor-isqrt, avoiding floating initialization or truncation.
        for bit in range(30, -1, -1):
            candidate = self.op('Add', root, self.c(1 << bit))
            root = self.op('Where', self.op('LessOrEqual', self.op('Mul', candidate, candidate), var), candidate, root)
        z = self.rd(self.op('Mul', centered, self.c(2048)), root)
        return self.sat(self.op('Add', self.rd(self.op('Mul', z, weight), 2048), bias))

    def linear(self, x, w, multiplier, divisor, bias=None, expert=False):
        if expert:
            products = self.op('Mul', self.unsq(x, -1), w)
        else:
            products = self.op('Mul', self.unsq(x, -1), self.op('Transpose', w, perm=[1, 0]))
        dot = self.sum(products, -2, 0)
        y = self.rd(self.op('Mul', dot, multiplier), divisor)
        if bias is not None:
            y = self.op('Add', y, bias)
        return self.sat(y)

    def lookup(self, x, table, offset=0):
        u = self.clamp(self.op('Add', self.op('Mul', x, self.c(32)), self.c(offset*2048)), 0, 512*2048)
        i = self.op('Div', u, self.c(2048))
        remainder = self.op('Mod', u, self.c(2048))
        left = self.op('Gather', table, i, axis=0)
        right = self.op('Gather', table, self.clamp(self.op('Add', i, self.c(1)), 0, 512), axis=0)
        return self.rd(self.op('Add', self.op('Mul', left, self.op('Sub', self.c(2048), remainder)), self.op('Mul', right, remainder)), 2048)

    def gelu(self, x, table):
        return self.sat(self.op('Where', self.op('Greater', x, self.c(16384)), x,
            self.op('Where', self.op('Less', x, self.c(-16384)), self.c(0), self.lookup(x, table, 256))))

    def softmax(self, scores, table, width):
        maximum = self.op('ReduceMax', scores, self.c([-1]), keepdims=1)
        exp = self.lookup(self.op('Sub', maximum, scores), table)
        p = self.op('Div', self.op('Mul', exp, self.c(32768)), self.sum(exp, -1))
        first = self.op('ArgMax', scores, axis=-1, keepdims=1, select_last_index=0)
        mask = self.op('Cast', self.op('Equal', first, self.c(list(range(width)))), to=T.INT64)
        return self.op('Add', p, self.op('Mul', mask, self.op('Sub', self.c(32768), self.sum(p, -1))))


def build_model(packet=PACKET):
    raw = Path(packet).read_bytes()
    if len(raw) != 5195 or hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('not the accepted 5195-byte F9J2 packet')
    candidate = load(packet)
    assert (candidate['frac'], candidate['width'], candidate['expert_width'], candidate['experts'], candidate['topk'], candidate['attention_mode'], candidate['interpolate']) == (11, 8, 4, 4, 2, 'early', True)
    initializers = []
    functions = []
    nodes = []
    def init(name, values):
        initializers.append(NH.from_array(np.asarray(values, dtype=np.int64), name))
        return name
    for name, t in candidate['tensors'].items():
        init(name, t['codes'].numpy())
        if len(t['exponents']) > 1:
            exps = np.array(t['exponents'])
            if name.startswith('expert_w'):
                exps = exps.reshape(4, -1)
            init(name+'.multiply', 2 ** np.maximum(exps, 0))
            init(name+'.divide', 2 ** np.maximum(-exps, 0))
    init('exp.lut', candidate['tables']['exp'])
    init('gelu.lut', candidate['tables']['gelu'])
    def stage(name, inputs, outputs, compute, doc):
        b = Builder()
        result = compute(b, *inputs)
        if isinstance(result, str): result = [result]
        for src, dst in zip(result, outputs): b.nodes.append(H.make_node('Identity', [src], [dst]))
        functions.append(H.make_function(DOMAIN, name, inputs, outputs, b.nodes, [H.make_opsetid('', 18)], doc_string=doc))
        nodes.append(H.make_node(name, inputs, outputs, domain=DOMAIN, name=name, doc_string=doc))
    def linargs(name, bias=None):
        return [name, name+'.multiply', name+'.divide'] + ([bias] if bias else [])
    def embed(b, board, occ, pos, side):
        occupied = b.op('Cast', b.op('Not', b.op('Equal', board, b.c(0))), to=T.INT64)
        side_id = b.op('Mod', b.sum(occupied, -1, 0), b.c(2))
        return b.sat(b.op('Add', b.op('Add', b.op('Gather', occ, board, axis=0), pos), b.unsq(b.op('Gather', side, side_id, axis=0), 1)))
    stage('OccupancyPositionSide', ['board','occupancy.weight','position','side.weight'], ['embedding'], embed, 'Add occupancy, absolute position and parity-side embeddings. Canonical occupancy input; no history/symmetry wrapper inside ONNX.')
    stage('TokenNormalization', ['embedding','norm1.weight','norm1.bias'], ['normalized_tokens'], lambda b,*a:b.norm(*a), 'Exact rounded mean/variance, epsilon 42, 31-step floor integer sqrt, Q11 affine, INT32 clamp.')
    def qkv(b,z,*weights):
        return [b.linear(z,*weights[i:i+3]) for i in range(0,9,3)]
    stage('QueryKeyValue', ['normalized_tokens']+sum([linargs(n+'.weight') for n in ('query','key','value')], []), ['query','key','value'], qkv, 'Three learned 8-to-8 projections with per-output binary exponents. INT64 Mul/ReduceSum, not unsupported integer MatMul.')
    def attention(b,q,k,v,exp):
        dots = b.sum(b.op('Mul', b.unsq(q,2), b.unsq(k,1)), -1, 0)
        scores = b.sat(b.rd(b.op('Mul', b.rd(dots,2048), b.c(candidate['attention_factor'])), candidate['attention_denominator']))
        p = b.softmax(scores,exp,9)
        return b.sat(b.rd(b.sum(b.op('Mul', b.unsq(p,-1), b.unsq(v,1)), 2, 0),32768))
    stage('FullBoardAttention', ['query','key','value','exp.lut'], ['attended'], attention, 'All 9 tokens attend all 9 tokens, no causal mask. Early-round scaled QK, interpolated exp LUT, Q15 probabilities with remainder to first argmax, weighted V.')
    stage('AttentionProjResidual', ['attended','embedding']+linargs('projection.weight'), ['attention_residual'], lambda b,a,x,*w:b.sat(b.op('Add',x,b.linear(a,*w))), 'Learned 8-to-8 output projection and token residual.')
    stage('FlattenReadoutGELU', ['attention_residual']+linargs('readout.weight','readout.bias')+['gelu.lut'], ['readout'], lambda b,x,w,m,d,bias,lut:b.gelu(b.linear(b.op('Reshape',x,b.c([1,72])),w,m,d,bias),lut), 'Flatten 9x8 to 72, learned 72-to-8 readout and interpolated Q11 GELU.')
    stage('ReadoutNormalization', ['readout','norm2.weight','norm2.bias'], ['normalized_readout'], lambda b,*a:b.norm(*a), 'Exact integer normalization and learned Q11 affine.')
    def route(b,z,w,m,d,bias,exp):
        s=b.linear(z,w,m,d,bias)
        first=b.op('ArgMax',s,axis=-1,keepdims=1,select_last_index=0)
        masked=b.op('Where',b.op('Equal',first,b.c([0,1,2,3])),b.c(-(1<<62)),s)
        second=b.op('ArgMax',masked,axis=-1,keepdims=1,select_last_index=0)
        routes=b.op('Concat',first,second,axis=1)
        gates=b.softmax(b.op('GatherElements',s,routes,axis=1),exp,2)
        return routes,gates
    stage('StableTop2Router', ['normalized_readout']+linargs('router.weight','router.bias')+['exp.lut'], ['routes','gates'], route, 'Learned E=4 router. Stable top-2 descending score, lower expert index wins ties. Softmax only the two selected scores.')
    expert_inputs = ['normalized_readout','routes','gelu.lut']+linargs('expert_w1','expert_b1')+linargs('expert_w2','expert_b2')
    def experts(b,z,r,lut,w1,m1,d1,b1,w2,m2,d2,b2):
        # Select weights before either dot product: only 2 expert MLPs execute.
        selected = [b.op('Gather',a,r,axis=0) for a in (w1,m1,d1,b1,w2,m2,d2,b2)]
        w1,m1,d1,b1,w2,m2,d2,b2=selected
        hidden=b.gelu(b.linear(b.unsq(z,1),w1,m1,d1,b1,expert=True),lut)
        return b.linear(hidden,w2,m2,d2,b2,expert=True)
    stage('GatherTop2Experts', expert_inputs, ['selected_expert_vectors'], experts, 'All four physical [expert,input,output] tensors retained. Dynamically Gather the two selected weights/biases/exponents BEFORE 8-to-4 GELU, 4-to-8 computation. No all-expert dense execution.')
    stage('GatedMergeResidual', ['selected_expert_vectors','gates','readout'], ['merged'], lambda b,e,g,x:b.sat(b.op('Add',x,b.rd(b.sum(b.op('Mul',e,b.unsq(g,-1)),1,0),32768))), 'Q15 weighted sum of the two expert vectors, round half away, add readout residual and INT32 clamp.')
    stage('NineMembershipScores', ['merged']+linargs('output.weight','output.bias'), ['scores'], lambda b,*a:b.linear(*a), 'Nine signed INT32-domain membership scores represented as INT64. Empty canonical squares with score >=0 are learned optimal members; inverse symmetry and ebdfhcgia tie selection are external.')
    graph=H.make_graph(nodes,'FALKEN-9 v1.0.0 exact integer inspection', [H.make_tensor_value_info('board',T.INT64,[1,9])], [H.make_tensor_value_info('scores',T.INT64,[1,9]),H.make_tensor_value_info('routes',T.INT64,[1,2])], initializers)
    shapes = {'embedding':[1,9,8], 'normalized_tokens':[1,9,8], 'query':[1,9,8], 'key':[1,9,8], 'value':[1,9,8], 'attended':[1,9,8], 'attention_residual':[1,9,8], 'readout':[1,8], 'normalized_readout':[1,8], 'gates':[1,2], 'selected_expert_vectors':[1,2,8], 'merged':[1,8]}
    graph.value_info.extend(H.make_tensor_value_info(n,T.INT64,s) for n,s in shapes.items())
    model=H.make_model(graph,functions=functions,opset_imports=[H.make_opsetid('',18),H.make_opsetid(DOMAIN,1)],producer_name='falken9 exact integer inspection exporter',producer_version='1.0.0',ir_version=10)
    model.doc_string='Derived inspection artifact, not C64 deployment bytes. Exact F9J2 arithmetic expressed using standard ONNX INT64 operations inside expandable local functions. Fixed canonical board input; history legality, canonicalization, inverse symmetry and final policy selection remain external.'
    H.set_model_props(model, {'source_packet_sha256':EXPECTED,'source_packet_bytes':'5195','source_packet_path':str(Path(packet).relative_to(ROOT)), 'arithmetic':'Q11 W16 A32; exact half-away rounding; floor-isqrt; early attention; interpolated LUT; stable E4 K2 sparse execution', 'tensor_lineage':json.dumps({n:{'shape':list(t['codes'].shape),'bits':t['bits'],'exponents':t['exponents']} for n,t in candidate['tensors'].items()},sort_keys=True)})
    return model


def validate_model(model):
    import onnxruntime as ort
    from falken9.canonical_training import load_data
    from falken9.symmetry import restore_moves
    sys.path.insert(0, str(ROOT/'tests'))
    from test_canonical_integer_model import scalar_oracle
    onnx.checker.check_model(model, full_check=True)
    session = ort.InferenceSession(model.SerializeToString(), providers=['CPUExecutionProvider'])
    data = load_data(ROOT/'data/nonterminal-legal-histories.jsonl')
    candidate = load(PACKET)
    boards = data['canonical_boards'].numpy()
    scores, routes, references, reference_routes = [], [], [], []
    for board in boards:
        actual, route = session.run(None, {'board':board.reshape(1,9)})
        expected, expected_route = scalar_oracle(candidate, board.tolist())
        scores.append(actual[0]); routes.append(route[0])
        references.append(expected); reference_routes.append(expected_route)
    scores, routes = np.asarray(scores), np.asarray(routes)
    masks = (scores >= 0) & (boards == 0)
    targets = data['targets'].numpy().astype(bool)
    board_set_errors = board_move_errors = 0
    board_errors = []
    for ci, transform, label, expected_set in zip(data['board_canonical_indices'],data['transforms'],data['labels'],data['sets']):
        restored = restore_moves([chr(97+i) for i in range(9) if masks[ci,i]], transform)
        set_error = set(restored) != set(expected_set)
        move_error = not restored or restored[0] != label
        board_set_errors += set_error; board_move_errors += move_error
        board_errors.append(bool(set_error or move_error))
    report = dict(checker='onnx.checker.check_model(full_check=True): PASS',
        runtime=ort.__version__,provider=session.get_providers(),onnx_version=onnx.__version__,
        canonical_count=len(boards),score_values_compared=int(scores.size),route_values_compared=int(routes.size),
        score_mismatch_boards=int(np.any(scores != np.asarray(references),axis=1).sum()),
        route_mismatch_boards=int(np.any(routes != np.asarray(reference_routes),axis=1).sum()),
        max_abs_score_error=int(np.abs(scores-np.asarray(references)).max()),
        canonical_set_errors=int(np.any(masks != targets,axis=1).sum()),
        canonical_membership_bit_errors=int((masks != targets).sum()),
        independent_scalar_oracle=True,oracle_path='tests/test_canonical_integer_model.py:scalar_oracle',
        board_count=len(board_errors),board_set_errors=int(board_set_errors),board_move_errors=int(board_move_errors),
        indexed_history_count=len(data['histories']),indexed_history_errors=int(np.array(board_errors)[data['history_indices'].numpy()].sum()),
        history_boundary='History results are externally restored/indexed from ONNX canonical outputs, not ONNX history-wrapper execution.',
        dataset_sha256=data['dataset_sha256'],
        output_trace_sha256=hashlib.sha256(scores.astype('<i8').tobytes()+routes.astype('<i8').tobytes()).hexdigest())
    assert report['canonical_count'] == 627
    assert not any(report[k] for k in ['score_mismatch_boards','route_mismatch_boards','canonical_set_errors','board_set_errors','board_move_errors','indexed_history_errors'])
    return report


def main():
    output=ROOT/'inspection/falken9-model-v1.0.0.onnx'
    output.parent.mkdir(exist_ok=True)
    model=build_model()
    onnx.checker.check_model(model,full_check=True)
    onnx.save_model(model,output,save_as_external_data=False)
    # Validate bytes read from the delivered file, not just the builder object.
    report=validate_model(onnx.load(output))
    report['artifact_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    (output.parent/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    candidate=load(PACKET)
    source_paths=['falken9/canonical_integer.py','falken9/integer_model.py','falken9/canonical_integer_export.py','tests/test_canonical_integer_model.py','scripts/export_inspection_graph.py']
    lineage=[]
    by_name={t.name:NH.to_array(t) for t in model.graph.initializer}
    for name,t in candidate['tensors'].items():
        codes=t['codes'].numpy().astype('<i8')
        assert np.array_equal(codes,by_name[name])
        lineage.append(dict(name=name,shape=list(codes.shape),packet_storage_bits=t['bits'],onnx_dtype='INT64',codes_int64_le_sha256=hashlib.sha256(codes.tobytes()).hexdigest(),exponents=t['exponents'],matrix_layout='[expert,input,output]' if name.startswith('expert_w') else '[output,input]' if codes.ndim==2 and len(t['exponents'])>1 else 'native',onnx_initializer=name))
    manifest=dict(schema='falken9-inspection-v1',role='Derived exact-integer inspection graph, not deployment packet',source_packet=dict(path=str(PACKET.relative_to(ROOT)),bytes=5195,sha256=EXPECTED),onnx=dict(path=str(output.relative_to(ROOT)),bytes=output.stat().st_size,sha256=report['artifact_sha256'],external_data_files=[],opset=18,ir_version=10,top_level_nodes=len(model.graph.node),functions=len(model.functions),function_body_nodes=sum(len(f.node) for f in model.functions),initializers=len(model.graph.initializer)),input=dict(name='board',dtype='INT64',shape=[1,9],precondition='Canonical reachable nonterminal board, occupancy 0 empty / 1 X / 2 O. Domain preconditions are external, not validated by this graph.'),outputs=[dict(name='scores',dtype='INT64',shape=[1,9],semantic='Signed INT32-domain Q11 membership scores; legal empty squares >=0 are selected.'),dict(name='routes',dtype='INT64',shape=[1,2],semantic='Stable score-descending expert IDs in 0..3')],contract=dict(frac=11,width=8,expert_width=4,experts=4,topk=2,activation_bits=32,output_bits=32,rounding='nearest, ties away from zero',normalization_epsilon=42,isqrt='31 unrolled exact integer bit tests',attention='full nine-token board; early round; factor '+str(candidate['attention_factor'])+'/32768',lookup='linear interpolation of accepted 513-entry integer LUTs',softmax='Q15; remainder to first argmax',expert_execution='Gather selected weights before Mul/ReduceSum; two expert MLPs, not four',wrapper='External history validation, canonical symmetry, inverse move symmetry, ebdfhcgia tie order'),source_file_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},tensor_count=len(lineage),tensor_lineage=lineage,validation='inspection/validation.json',render_provenance='artifacts/inspection/netron/provenance.json',notes=['No float fallback or custom kernels. ONNX local functions expand into standard ONNX operators.','INT64 Sign avoided: observed ORT 1.31.1 CPU misclassification for 2290000000; Less/Where sign used instead.','This ONNX gate does not independently execute or certify the assembled 6502 implementation.'])
    (output.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'path':str(output.relative_to(ROOT)),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'checker':'pass','functions':len(model.functions),'top_level_nodes':len(model.graph.node)},indent=2))

if __name__=='__main__':main()
