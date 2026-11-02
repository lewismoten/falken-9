"""Presentation-only restoration of the original model inspection diagrams."""
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET
import hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('inspection_figures',ROOT/'scripts/prepare_model_inspection_figures.py')
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def semantics(svg):
    root=ET.fromstring(svg)
    for e in root.iter():
        for key in ('fill','stroke'):
            e.attrib.pop(key,None)
        if 'style' in e.attrib:
            values=[s.strip() for s in e.attrib['style'].split(';') if s.strip()]
            e.set('style',';'.join(s for s in values if s.split(':',1)[0].strip() not in ('fill','stroke')))
    return ET.tostring(root)

def test_dark_native_graph_preserves_all_noncolor_semantics():
    m=load();s=(ROOT/m.SOURCES['netron_svg']).read_bytes()
    result=m.dark_netron(s)
    assert semantics(s)==semantics(result)
    root=ET.fromstring(result)
    background=root.find('{http://www.w3.org/2000/svg}rect')
    assert background is not None and background.get('fill')=='#101820'
    assert root.get('fill')=='#dce6ef'

def test_stage_restores_originals_and_promotes_verified_browser_derivative(tmp_path):
    m=load();before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in m.SOURCES.values()}
    out=tmp_path/'inspection'
    manifest=m.prepare(ROOT,out)
    for role,name in [('workflow_png','tensor-workflow.png'),('workflow_svg','tensor-workflow.svg'),('netron_png','netron-original.png'),('netron_svg','netron-original.svg')]:
        assert (out/name).read_bytes()==(ROOT/m.SOURCES[role]).read_bytes()
    assert semantics((out/'netron-dark.svg').read_bytes())==semantics((out/'netron-original.svg').read_bytes())
    with Image.open(out/'netron-dark.png') as im:
        assert im.size==(648,1750)
        assert im.convert('RGB').getpixel((0,0))==(16,24,32)
    assert manifest['presentation_only'] is True
    assert before=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in m.SOURCES.values()}
