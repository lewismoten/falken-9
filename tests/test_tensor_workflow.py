"""Independent packet and scalar-decoding contract for the release inspector."""
import hashlib
import importlib.util
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
SHA = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'


def module():
    path = ROOT / 'scripts/render_tensor_workflow.py'
    assert path.exists(), 'production tensor workflow generator is missing'
    spec = importlib.util.spec_from_file_location('tensor_workflow', path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_decode_every_scalar_from_accepted_source():
    mod = module()
    result = mod.decode_packet(SOURCE)
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA == result['source']['sha256']
    assert result['source']['bytes'] == 5195
    assert len(result['tensors']) == 21
    assert [t['name'] for t in result['tensors']] == [
        'position','expert_w1','expert_b1','expert_w2','expert_b2','occupancy.weight','side.weight',
        'norm1.weight','norm1.bias','query.weight','key.weight','value.weight','projection.weight',
        'readout.weight','readout.bias','norm2.weight','norm2.bias','router.weight','router.bias','output.weight','output.bias']
    # Independent physical payload traversal, no generator constants/decoder reuse.
    pos = struct.calcsize('<4s10BHH') + 81
    descriptors = []
    for _ in range(21):
        start = pos
        bits, rank, count = struct.unpack_from('<BBH', raw, pos)
        pos += 4
        shape = list(raw[pos:pos + rank]); pos += rank
        exps = list(struct.unpack_from('<' + 'b' * count, raw, pos)); pos += count
        descriptors.append((bits, shape, exps, start, pos))
    for t, (bits, shape, exps, start, end) in zip(result['tensors'], descriptors):
        n = math.prod(shape)
        payload = raw[pos:pos + n * bits // 8]
        codes = list(struct.unpack('<' + 'h' * n, payload))
        assert t['shape'] == shape and t['exponents'] == exps
        assert t['codes'] == codes
        assert t['payload_sha256'] == hashlib.sha256(payload).hexdigest()
        assert t['descriptor_sha256'] == hashlib.sha256(raw[start:end]).hexdigest()
        assert t['payload_offset'] == pos
        for index, (code, value) in enumerate(zip(codes, t['values'])):
            if len(exps) == 1:
                exponent = exps[0]
            elif t['name'].startswith('expert_w'):
                expert = index // (shape[1] * shape[2])
                output = index % shape[2]
                exponent = exps[expert * shape[2] + output]
            else:
                exponent = exps[index // shape[-1]]
            assert value == math.ldexp(code, exponent)
        pos += len(payload)
    assert pos + 2052 == len(raw)


def test_rendered_workflow_has_exact_cell_coverage_and_safe_geometry(tmp_path):
    mod = module()
    assert hasattr(mod, 'render'), 'same-geometry PNG/SVG workflow renderer is missing'
    meta = mod.render(SOURCE, tmp_path / 'workflow')
    from PIL import Image
    import xml.etree.ElementTree as ET
    assert Image.open(tmp_path / 'workflow.png').size == tuple(meta['canvas'])
    svg = ET.parse(tmp_path / 'workflow.svg').getroot()
    ns = {'s': 'http://www.w3.org/2000/svg'}
    assert len(svg.findall('.//s:rect[@data-scalar]', ns)) == sum(t['scalar_count'] for t in meta['tensors'])
    seen = {}
    for panel in meta['panels']:
        t = next(t for t in meta['tensors'] if t['name'] == panel['tensor'])
        for cell in panel['cells']:
            key = panel['tensor'], cell['physical_index']
            assert key not in seen
            seen[key] = True
            assert cell['value'] == t['values'][cell['physical_index']]
            assert cell['color'] == mod.value_color(cell['value'], t['color_absmax'])
            x0, y0, x1, y1 = cell['bounds']
            assert 0 <= x0 < x1 <= meta['canvas'][0]
            assert 0 <= y0 < y1 <= meta['canvas'][1]
    assert len(seen) == sum(t['scalar_count'] for t in meta['tensors'])
    assert meta['architecture']['attention'] == 'full bidirectional, one head, no mask'
    assert meta['architecture']['routing'] == 'stable top-2; selected-score Q15 softmax'
    assert meta['architecture']['selected_expert_ids'] is None
    assert meta['architecture']['normalizations'] == ['norm1', 'norm2']
    assert len(meta['experts']) == 4
    assert meta['scalar_count'] == 1405
    assert meta['contract'] == dict(frac=11,width=8,expert_width=4,experts=4,topk=2,
                                   activation_bits=32,output_bits=32,attention_mode='early',
                                   interpolate=True,attention_factor=11585,attention_denominator=32768)
    svg_cells = {r.attrib['data-scalar']:r for r in svg.findall('.//s:rect[@data-scalar]',ns)}
    for panel in meta['panels']:
        if panel['tensor'].startswith('expert_w'):
            rows, cols = (4,8) if panel['tensor']=='expert_w1' else (8,4)
            assert (panel['rows'],panel['columns']) == (rows,cols)
            expected = [panel['expert']*rows*cols+col*rows+row for row in range(rows) for col in range(cols)]
            assert [cell['physical_index'] for cell in panel['cells']] == expected
        for cell in panel['cells']:
            assert svg_cells[f"{panel['tensor']}:{cell['physical_index']}"].attrib['fill'] == cell['color']
    # Expert container bounds derive from their full W1/b1 + W2/b2 extents.
    for expert in meta['experts']:
        l, top, r, bottom = expert['bounds']
        for panel in meta['panels']:
            if panel.get('expert') == expert['id']:
                a,b,c,d = panel['bounds']
                assert l < a < c < r and top < b < d < bottom
    # Every routed line segment stays outside grid interiors.
    for connector in meta['connectors']:
        for (x0,y0),(x1,y1) in zip(connector['points'], connector['points'][1:]):
            assert x0 == x1 or y0 == y1
            for panel in meta['panels']:
                l,t,r,b = panel['bounds']
                if x0 == x1:
                    assert not (l < x0 < r and max(min(y0,y1),t) < min(max(y0,y1),b))
                else:
                    assert not (t < y0 < b and max(min(x0,x1),l) < min(max(x0,x1),r))
    for label in meta['labels']:
        l,t,r,b = label['bounds']
        assert 0 <= l <= r <= meta['canvas'][0] and 0 <= t <= b <= meta['canvas'][1]
        for panel in meta['panels']:
            a,c,d,e = panel['bounds']
            assert max(l,a) >= min(r,d) or max(t,c) >= min(b,e), label['text']
    for label in meta['labels']:
        if label['bounds'][0] == 43:
            assert label['bounds'][2] <= 265, label['text']
    assert 'not reconstructable' in meta['disclaimer']
    assert 'fill="None"' not in (tmp_path / 'workflow.svg').read_text()
    # PNG centers must encode exactly the scalar colors in the structural record.
    image = Image.open(tmp_path / 'workflow.png')
    for panel in meta['panels']:
        for cell in panel['cells']:
            l,t,r,b = cell['bounds']
            assert image.getpixel(((l+r)//2,(t+b)//2)) == tuple(bytes.fromhex(cell['color'][1:]))
    # Explicitly verify the bypass lane does not strike Q/K/V headers.
    skip = next(a for a in meta['connectors'] if a['name']=='embedding-residual')
    for (x0,y0),(x1,y1) in zip(skip['points'],skip['points'][1:]):
        for label in meta['labels']:
            l,t,r,b = label['bounds']
            if y0 == y1:
                assert not (t < y0 < b and max(min(x0,x1),l) < min(max(x0,x1),r)), label['text']
    assert mod.value_color(0, 1) == '#000000'
    assert mod.value_color(1, 1) == '#ffe34a'
    assert mod.value_color(.5, 1) == '#28ac4b'
    assert mod.value_color(-1, 1) == '#426dff'
    assert mod.value_color(-.5, 1) == '#174bb0'


def test_versioned_output_names_are_reproducible(tmp_path):
    mod = module()
    stem = tmp_path / 'model-v1.0.0-tensor-workflow'
    mod.render(SOURCE, stem)
    paths = [Path(str(stem)+'.'+extension) for extension in ('png','svg','json')]
    before = [path.read_bytes() for path in paths]
    mod.render(SOURCE, stem)
    assert [path.read_bytes() for path in paths] == before


def test_rejects_nonaccepted_source(tmp_path):
    source = tmp_path / 'changed.f9j'
    source.write_bytes(SOURCE.read_bytes()[:-1] + b'!')
    import pytest
    with pytest.raises(ValueError, match='accepted'):
        module().decode_packet(source)
