#!/usr/bin/env python3
"""Restore original model inspectors with an explicitly derived dark Netron view."""
from pathlib import Path
import argparse, hashlib, json, re, shutil
import xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    'workflow_png':'assets/model-v1.0.0-tensor-workflow.png',
    'workflow_svg':'assets/model-v1.0.0-tensor-workflow.svg',
    'netron_png':'artifacts/inspection/netron/falken9-model-v1.0.0.png',
    'netron_svg':'artifacts/inspection/netron/falken9-model-v1.0.0.svg',
}
PINS={
    'workflow_png':'81e3af15bc66a9bc87e21e025f99f47109a17d8e1e239f3fe9b8e33bb4a508f7',
    'workflow_svg':'dacef58524a47696e7cba92f00d1ea2a11f9ed9c96f32f1204efe61a99f49a6a',
    'netron_png':'887396291f33ad313809494ca7a9c4281dd926fe4cb9e0cc80ddd83669639bb2',
    'netron_svg':'07a7bd3b52deb087e962df60eb15fe2d76c304547834cd73c5b94283beff9430',
}
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def dark_netron(svg):
    root=ET.fromstring(svg)
    # Inherited SVG black becomes readable off-white, without touching labels.
    root.set('fill','#dce6ef')
    for e in root.iter():
        text=e.tag.rsplit('}',1)[-1] in ('text','tspan')
        def recolor(prop,value):
            if prop=='fill':
                if e.get('id')=='background': return '#101820'
                if text: return '#dce6ef' if value not in ('none','transparent') else value
                return {'rgb(0, 0, 0)':'#a7b8ca','rgb(51, 51, 51)':'#2b4257','rgb(255, 255, 255)':'#16222e','rgb(238, 238, 238)':'#233344','rgba(220, 0, 0, 0.9)':'#e6978b'}.get(value,value)
            if prop=='stroke':
                return {'rgb(0, 0, 0)':'#a7b8ca','rgb(51, 51, 51)':'#5d7186'}.get(value,value)
            return value
        for key in ('fill','stroke'):
            if key in e.attrib: e.set(key,recolor(key,e.attrib[key]))
        if 'style' in e.attrib:
            style=re.sub(r'(?P<key>fill|stroke):\s*(?P<value>[^;]+)',lambda m:m['key']+': '+recolor(m['key'],m['value'].strip()),e.attrib['style'])
            e.set('style',style)
    return ET.tostring(root,encoding='utf-8')

def prepare(root,output,rendered_png=None):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists(): raise ValueError('Output must be new; original assets are never overwritten')
    for role,name in SOURCES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=PINS[role]: raise ValueError('Original inspector changed: '+role)
    rendered_png = Path(rendered_png) if rendered_png else root/'assets/interpretability/model-inspection/netron-dark.png'
    png = rendered_png.read_bytes()
    if hashlib.sha256(png).hexdigest() != '33982cf05690532e9745e16e1c9ec3ae073dde1b948b71f41d00d40bf7ae8ff9':
        raise ValueError('Expected independently captured Chromium dark-graph PNG')
    with Image.open(rendered_png) as im:
        if im.size != (648,1750): raise ValueError('Unexpected browser raster dimensions')
    output.mkdir(parents=True)
    copies={'workflow_png':'tensor-workflow.png','workflow_svg':'tensor-workflow.svg','netron_png':'netron-original.png','netron_svg':'netron-original.svg'}
    for role,name in copies.items(): shutil.copyfile(root/SOURCES[role],output/name)
    svg=dark_netron((root/SOURCES['netron_svg']).read_bytes())
    (output/'netron-dark.svg').write_bytes(svg)
    (output/'netron-dark.png').write_bytes(png)
    manifest={'schema':'falken9-model-inspection-presentation-v1','presentation_only':True,'source_model_sha256':'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1','source_onnx_sha256':'0e92767ffdae27b9cbd7682583839d4541419fb9bedf47dfaec73a0b00ee5160','originals':{r:{'path':p,'sha256':PINS[r],'copied_as':copies[r]} for r,p in SOURCES.items()},'dark_derivative':{'origin':'Original native Netron 9.3.4 SVG export','method':'Only fill and stroke colors changed, including inherited text fill. No text, geometry, paths, dimensions, topology or weights changed. Not a fresh native Netron export.','rasterizer':'Chrome/145.0.7632.6 SVG Image.decode and canvas.drawImage, canvas.toDataURL PNG encoder','png_dimensions':[648,1750],'png_source':'Separately browser-rendered, SHA-pinned input. This preparer promotes that verified raster; it does not silently substitute another font renderer.'},'files':[]}
    for p in sorted(output.iterdir()):
        manifest['files'].append({'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'README.md').write_text('''# Original model inspection diagrams\n\nThe tensor workflow is copied byte-for-byte from the original decoded parameter\ninspector. Each heatmap cell is a scalar, not a bit or byte; normalization is per\ntensor, all four expert banks are shown, and only two execute per inference.\nIt is not reconstructable model data or an activation trace.\n\nThe dark connection graph is a color-only presentation of the original native\nNetron 9.3.4 export: labels, tensor dimensions, residual branches and graph\ngeometry are unchanged. Its PNG is browser-rendered with Chromium, not represented as\na fresh native Netron capture. The exact original light PNG/SVG are preserved.\nThese are inspection views, not the C64 packet or new hardware acceptance.\n\n- [Tensor workflow PNG](tensor-workflow.png) / [SVG](tensor-workflow.svg).\n- [Dark graph PNG](netron-dark.png) / [SVG](netron-dark.svg).\n- [Original graph PNG](netron-original.png) / [SVG](netron-original.svg).\n- [Source and derivative hashes](provenance.json).\n''')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(prepare(ROOT,a.output),indent=2))
