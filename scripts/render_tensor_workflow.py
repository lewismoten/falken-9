#!/usr/bin/env python3
"""Deterministic decoded F9J2 scalar inspector, never a packed-model image."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import struct
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
ACCEPTED_SHA = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
NAMES = ('position', 'expert_w1', 'expert_b1', 'expert_w2', 'expert_b2', 'occupancy.weight', 'side.weight', 'norm1.weight', 'norm1.bias', 'query.weight', 'key.weight', 'value.weight', 'projection.weight', 'readout.weight', 'readout.bias', 'norm2.weight', 'norm2.bias', 'router.weight', 'router.bias', 'output.weight', 'output.bias')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode_packet(path=SOURCE) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if digest(raw) != ACCEPTED_SHA:
        raise ValueError('inspector requires the accepted immutable F9J2 source')
    magic, frac, width, hidden, experts, topk, ab, ob, mode, interp, count, factor, den = struct.unpack_from('<4s10BHH', raw)
    assert magic == b'F9J2' and count == len(NAMES)
    pos = struct.calcsize('<4s10BHH') + 81
    tensors = []
    for name in NAMES:
        start = pos
        bits, rank, n = struct.unpack_from('<BBH', raw, pos); pos += 4
        shape = list(raw[pos:pos + rank]); pos += rank
        exps = list(struct.unpack_from('<' + 'b' * n, raw, pos)); pos += n
        tensors.append(dict(name=name, bits=bits, shape=shape, exponents=exps,
                            descriptor_offset=start, descriptor_bytes=pos-start,
                            descriptor_sha256=digest(raw[start:pos])))
    for t in tensors:
        size = math.prod(t['shape']); end = pos + size * t['bits'] // 8
        codes = list(struct.unpack_from('<' + ('h' if t['bits'] == 16 else 'b') * size, raw, pos))
        values = []
        for i, code in enumerate(codes):
            shape, exps = t['shape'], t['exponents']
            if len(exps) == 1:
                e = exps[0]
            elif t['name'].startswith('expert_w'):
                e = exps[(i // (shape[1]*shape[2])) * shape[2] + i % shape[2]]
            else:
                e = exps[i // shape[-1]]
            values.append(math.ldexp(code, e))
        t.update(codes=codes, values=values, scalar_count=size, payload_offset=pos,
                 payload_bytes=end-pos, payload_sha256=digest(raw[pos:end]),
                 color_absmax=max(map(abs, values)),
                 exponent_axis='expert/output' if t['name'].startswith('expert_w') else ('tensor' if len(t['exponents'])==1 else 'output-row'))
        pos = end
    assert pos + 2052 == len(raw)
    return dict(source=dict(path=str(Path(path).relative_to(ROOT)), sha256=digest(raw), bytes=len(raw), magic='F9J2',
                            wrapper_sha256=digest(raw[18:99]), lookup_tables_sha256=digest(raw[pos:])),
                contract=dict(frac=frac, width=width, expert_width=hidden, experts=experts, topk=topk,
                              activation_bits=ab, output_bits=ob, attention_mode=('legacy','early','rational')[mode],
                              interpolate=bool(interp), attention_factor=factor, attention_denominator=den),
                tensors=tensors)


BG = '#0b1018'
FG = '#e5eaf0'
MUTED = '#aeb9ca'
WEIGHT = '#9275b5'
BIAS = '#4fc2ce'
FLOW = '#d8c65b'
BORDER = '#4d5869'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def value_color(value, maximum):
    """Piecewise linear signed transfer; normalized to the entire source tensor."""
    u = value / maximum if maximum else 0
    stops = [(-1, (66,109,255)), (-.5, (23,75,176)), (0,(0,0,0)),
             (.5,(40,172,75)), (1,(255,227,74))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if u <= b:
            f = max(0, (u-a)/(b-a))
            rgb = [round(x+(y-x)*f) for x,y in zip(ca,cb)]
            return '#' + ''.join(f'{v:02x}' for v in rgb)
    return '#ffe34a'


class Canvas:
    """One geometry stream painted to Pillow and serialized as vector SVG."""
    def __init__(self, width, height):
        from PIL import Image, ImageDraw, ImageFont
        self.image = Image.new('RGB', (width,height), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = {s:ImageFont.truetype(FONT,s) for s in (15,17,18,20,26)}
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    '<title>Falken-9 decoded accepted F9J2 tensor workflow</title>',
                    '<desc>Each cell is one decoded scalar; per-tensor normalization. Not a reconstructable packed-model image.</desc>',
                    f'<rect width="{width}" height="{height}" fill="{BG}"/>']
        self.labels = []
        self.connectors = []

    def rect(self, bounds, fill=BG, stroke=None, scalar=None):
        x,y,r,b = bounds
        self.draw.rectangle((x,y,r-1,b-1), fill=fill, outline=stroke)
        attr = f' data-scalar="{html.escape(scalar)}"' if scalar else ''
        self.svg.append(f'<rect x="{x}" y="{y}" width="{r-x}" height="{b-y}" fill="{fill or "none"}" stroke="{stroke or "none"}"{attr}/>')

    def text(self, x, y, text, size=17, color=FG, center=False):
        font = self.fonts[size]
        width = self.draw.textlength(text,font=font)
        if center:
            x -= width/2
        bounds = self.draw.textbbox((x,y),text,font=font,anchor='lt')
        self.draw.text((x,y),text,font=font,fill=color,anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="DejaVu Sans" font-size="{size}" dominant-baseline="text-before-edge">{html.escape(text)}</text>')
        self.labels.append(dict(text=text,bounds=list(bounds)))

    def arrow(self, name, points):
        self.connectors.append(dict(name=name,points=points))
        self.draw.line(points,fill=FLOW,width=2)
        (x0,y0),(x,y) = points[-2:]
        dx = 0 if x == x0 else (1 if x>x0 else -1)
        dy = 0 if y == y0 else (1 if y>y0 else -1)
        tip = [(x,y),(x-8*dx+4*dy,y-8*dy-4*dx),(x-8*dx-4*dy,y-8*dy+4*dx)]
        self.draw.polygon(tip,fill=FLOW)
        self.svg.append(f'<polyline points="{" ".join(f"{a},{b}" for a,b in points)}" fill="none" stroke="{FLOW}" stroke-width="2"/>')
        self.svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in tip)}" fill="{FLOW}"/>')

    def box(self, bounds, lines, size=17):
        self.rect(bounds,stroke=BORDER)
        x,y,r,b = bounds
        for i,line in enumerate(lines):
            self.text((x+r)/2,y+13+i*25,line,size=size,center=True)


def render(source=SOURCE, output=None):
    meta = decode_packet(source)
    output = Path(output or ROOT / 'assets/model-v1.0.0-tensor-workflow')
    output.parent.mkdir(parents=True,exist_ok=True)
    c = Canvas(1740,1300)
    tensors = {t['name']:t for t in meta['tensors']}
    panels = []

    def grid(name,x,y,cell=12,expert=None,vector=False):
        t = tensors[name]
        shape = t['shape']
        if expert is not None:
            if name.startswith('expert_w'):
                rows,cols = shape[2],shape[1]
                indexes = [[expert*shape[1]*shape[2]+col*shape[2]+row for col in range(cols)] for row in range(rows)]
            else:
                rows,cols = shape[1],1
                indexes = [[expert*shape[1]+row] for row in range(rows)]
        elif len(shape)==1 or vector:
            rows,cols = len(t['values']),1
            indexes = [[row] for row in range(rows)]
        else:
            rows,cols = shape
            indexes = [[row*cols+col for col in range(cols)] for row in range(rows)]
        bounds = [x,y,x+cols*cell,y+rows*cell]
        cells = []
        for row in range(rows):
            for col in range(cols):
                idx = indexes[row][col]
                value = t['values'][idx]
                color = value_color(value,t['color_absmax'])
                box = [x+col*cell,y+row*cell,x+(col+1)*cell,y+(row+1)*cell]
                cells.append(dict(physical_index=idx,value=value,color=color,bounds=box))
        # Borders outside cells; every cell retains its own complete filled extent.
        border = BIAS if ('bias' in name or name.startswith('expert_b')) else WEIGHT
        c.rect([x-2,y-2,x+cols*cell+2,y+rows*cell+2],fill=BG,stroke=border)
        for entry in cells:
            c.rect(entry['bounds'],entry['color'],scalar=f"{name}:{entry['physical_index']}")
        panels.append(dict(tensor=name,expert=expert,bounds=bounds,rows=rows,columns=cols,cells=cells,
                           orientation='output-by-input (transposed from physical input-by-output)' if name.startswith('expert_w') else 'physical row-major; affine vectors vertical'))
        return bounds

    def pair(name,bias,x,y,cell=12,expert=None):
        a = grid(name,x,y,cell,expert)
        b = grid(bias,a[2]+12,y,cell,expert)
        return [x,y,b[2],max(a[3],b[3])]

    c.text(30,23,'Falken-9 / accepted F9J2 tensor workflow',26)
    c.text(30,64,'Decoded inspector — not reconstructable. Not a raw packed-model PNG.',18,color=FLOW)
    c.text(30,96,'9 board tokens · width 8 · 4 learned experts / 2 active · Q11 / W16 / A32 · no board trace implied',17,color=MUTED)

    c.text(83,145,'Occupancy 3 × 8',17,center=True)
    grid('occupancy.weight',35,174)
    c.text(83,251,'Position 9 × 8',17,center=True)
    grid('position',35,280)
    c.text(83,430,'Side 2 × 8',17,center=True)
    grid('side.weight',35,459)
    # Addition is a true three-way embedding sum, not sequential transforms.
    c.arrow('occupancy-to-sum',[(133,192),(183,192),(183,305)])
    c.arrow('position-to-sum',[(133,328),(172,328)])
    c.arrow('side-to-sum',[(133,471),(183,471),(183,348)])
    c.text(183,313,'+',26,center=True,color=FLOW)
    c.arrow('sum-to-norm1',[(199,328),(252,328)])
    c.text(290,208,'Norm 1',20,center=True)
    c.text(290,237,'γ     β',17,center=True,color=MUTED)
    pair('norm1.weight','norm1.bias',268,268)
    c.arrow('norm1-to-qkv',[(307,316),(359,316)])

    c.rect([370,137,519,573],stroke=BORDER)
    c.text(444,147,'Input projections',17,center=True)
    for name,label,y in [('query','Query',201),('key','Key',337),('value','Value',473)]:
        c.text(444,y-27,f'{label} 8 × 8',17,center=True)
        grid(name+'.weight',396,y)
    c.text(444,578,'No Q/K/V bias',15,center=True,color=MUTED)
    c.arrow('qkv-to-attention',[(519,316),(564,316)])
    c.box([565,229,808,399],['Full board attention','1 head · 9 × 9 scores','scaled QKᵀ → softmax','Q15 probabilities × V','Bidirectional · no mask'])
    c.arrow('attention-to-projection',[(808,316),(865,316)])
    c.text(919,220,'Projection',20,center=True)
    c.text(919,247,'8 × 8 · no bias',15,center=True,color=MUTED)
    grid('projection.weight',872,276)
    c.arrow('projection-to-residual',[(970,316),(1038,316)])
    c.box([1040,267,1227,370],['+ embedding x','Attention residual','9 × 8'])
    c.arrow('embedding-residual',[(213,328),(225,328),(225,125),(1132,125),(1132,267)])
    c.text(805,140,'embedding skip',15,color=MUTED)
    c.arrow('residual-to-flatten',[(1227,316),(1280,316)])
    c.box([1281,267,1450,370],['Flatten board','9 × 8 → 72','position-major'])
    c.arrow('flatten-to-readout',[(1365,370),(1365,575),(630,575),(630,625)])

    c.text(630,641,'Readout · 72 → 8',20,center=True)
    pair('readout.weight','readout.bias',301,676,9)
    c.arrow('readout-to-gelu',[(978,712),(1000,712)])
    c.box([1001,681,1081,742],['GELU'],size=17)
    c.arrow('gelu-to-norm2',[(1081,712),(1111,712)])
    c.text(1140,625,'Norm 2',20,center=True)
    c.text(1140,654,'γ     β',17,center=True,color=MUTED)
    pair('norm2.weight','norm2.bias',1119,682)
    c.arrow('norm2-to-router',[(1157,712),(1220,712)])
    c.text(1300,628,'Router · 8 → 4',20,center=True)
    pair('router.weight','router.bias',1230,670)
    c.arrow('router-to-experts',[(1300,720),(1300,837),(810,837),(810,893)])
    c.rect([1047,816,1285,857],stroke=BORDER)
    c.text(1166,827,'Selected: 2 of 4',18,center=True)
    c.text(1394,756,'stable top-2',17,center=True,color=MUTED)
    c.text(1394,782,'selected-score softmax',15,center=True,color=MUTED)
    # The normalized readout feeds each selected expert, not the router scores.
    c.arrow('norm2-expert-input',[(1137,780),(1137,802),(391,802),(391,893)])
    c.text(748,779,'normalized readout z → selected expert inputs',15,center=True,color=MUTED)
    c.arrow('readout-residual',[(1040,742),(1040,867),(1325,867),(1325,1105),(1350,1105)])
    c.text(1176,875,'readout x skip',15,center=True,color=MUTED)

    expert_meta = []
    for expert in range(4):
        left = 371+expert*232
        first = pair('expert_w1','expert_b1',left+26,954,16,expert)
        # Derive next-layer anchor and all bounds from the actual first pair.
        second_y = first[3]+65
        second = pair('expert_w2','expert_b2',left+26,second_y,16,expert)
        right = max(first[2],second[2])+26
        bottom = second[3]+23
        bounds = [left,915,right,bottom]
        c.rect(bounds,fill=None,stroke=BORDER)
        c.text((left+right)/2,926,f'Expert {expert}',18,center=True)
        c.text((left+right)/2,first[3]+21,'GELU',17,center=True)
        # Short downward route remains wholly in the measured inter-layer gutter.
        c.arrow(f'expert-{expert}-gelu',[(left+94,first[3]+47),(left+94,second_y-6)])
        expert_meta.append(dict(id=expert,bounds=bounds,first_pair=first,second_pair=second,
                                w1='8 → 4 + bias',activation='GELU',w2='4 → 8 + bias'))
    bottom = max(e['bounds'][3] for e in expert_meta)
    c.rect([355,893,1291,bottom+15],fill=None,stroke=BORDER)
    c.text(501,869,'Learned expert bank',17,center=True,color=MUTED)
    c.arrow('selected-expert-weighted-merge',[(1291,1160),(1388,1160),(1388,1140)])
    c.box([1351,1015,1560,1140],['Q15 weighted sum','of selected 2 outputs','+ readout x residual','8-vector'])
    c.arrow('merge-to-membership',[(1560,1070),(1690,1070),(1690,266),(1638,266)])
    c.text(1570,181,'Output · 8 → 9',20,center=True)
    pair('output.weight','output.bias',1515,215)
    c.arrow('logits-to-wrapper',[(1570,325),(1570,365)])
    c.box([1480,366,1661,526],['9 signed INT32','membership logits','Outside the NN:','empty cells & logit ≥ 0','inverse symmetry','tie order ebdfhcgia'],size=15)

    # Source contract and semantic legend occupy the unused lower-left lane.
    c.rect([29,634,275,1252],stroke=BORDER)
    c.text(44,651,'Execution contract',18,color=FLOW)
    lines = ['Canonical full board','0 empty / 1 X / 2 O','Side = occupied count mod 2','No BOS, PAD or causal mask','Embedding sum → Norm 1','Norm 1 is per board token','Norm 2: readout 8-vector','GELU: readout & expert W1','Top-2 ties: stable index','No selected IDs without input','Q15 gates sum to 32768','Early attention factor:','Q11 rescale → 11585/32768','LUT GELU / exp: interpolated','INT32 activations and logits','Frozen source: 5195 bytes','F9J2 · 21 learned tensors','Cell = decoded scalar value','NOT bits / bytes / activations','Scale = integer code × 2^e','Color: per source tensor max','No cross-tensor comparison']
    for i,line in enumerate(lines):
        c.text(43,688+24*i,line,15,color=MUTED)
    c.text(313,1270,'Source SHA-256: '+meta['source']['sha256'],15,color=MUTED)
    # Compact legend above the experts, isolated from graph lanes.
    c.text(40,527,'Weights',15,color=MUTED)
    c.rect([150,525,165,540],stroke=WEIGHT)
    c.text(40,553,'Bias / β',15,color=MUTED)
    c.rect([150,551,165,566],stroke=BIAS)
    for j,(label,val) in enumerate([('large positive',1),('moderate positive',.5),('zero',0),('negative',-.5),('large negative',-1)]):
        c.rect([1490,560+j*29,1505,575+j*29],value_color(val,1),stroke=BORDER)
        c.text(1515,559+j*29,label,15,color=MUTED)
    meta.update(canvas=[1740,1300],panels=panels,experts=expert_meta,connectors=c.connectors,labels=c.labels,
                disclaimer='Decoded inspector — not reconstructable; NOT a raw packed-model PNG.',
                scalar_count=sum(t['scalar_count'] for t in meta['tensors']),
                color_normalization='signed piecewise linear color; value / max(abs(values)) per entire physical source tensor, shared across expert slices',
                scalar_unit='one decoded integer-code × power-of-two-exponent parameter per cell',
                architecture=dict(attention='full bidirectional, one head, no mask',normalizations=['norm1','norm2'],
                                  routing='stable top-2; selected-score Q15 softmax',selected_expert_ids=None,
                                  embedding='occupancy + absolute position + side',qkv_bias=False,
                                  residuals=['embedding + attention projection','readout + weighted expert sum'],
                                  activations=['readout GELU','expert W1 GELU'],flatten='9×8 position-major → 72',
                                  output='9 signed INT32 membership logits; wrapper outside NN'),
                rendering=dict(font=FONT,minimum_font_px=15,png_svg_same_geometry=True,
                               expert_orientation='physical [expert,input,output] transposed for output-row display; biases vertical per output lane'))
    files = {ext:Path(str(output)+'.'+ext) for ext in ('png','svg','json')}
    c.image.save(files['png'])
    files['svg'].write_text('\n'.join(c.svg+['</svg>'])+'\n')
    meta['outputs'] = {ext:dict(sha256=digest(files[ext].read_bytes()),bytes=files[ext].stat().st_size) for ext in ('png','svg')}
    files['json'].write_text(json.dumps(meta,indent=2)+'\n')
    assert digest(Path(source).read_bytes()) == meta['source']['sha256']
    return meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--output',type=Path,default=ROOT/'assets/model-v1.0.0-tensor-workflow')
    args = parser.parse_args()
    result = render(args.source,args.output)
    print(json.dumps(dict(source=result['source'],canvas=result['canvas'],tensors=len(result['tensors']),scalars=result['scalar_count'],outputs=result['outputs']),indent=2))
