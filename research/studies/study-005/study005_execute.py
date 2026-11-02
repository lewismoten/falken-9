#!/usr/bin/env python3
"""005 execution-only serialization repair; frozen study design/source unchanged.
The first attempt stopped before any intervention at JSON serialization of
NumPy int64 geometry counts. Normalize NumPy scalars/arrays to JSON values;
no numeric calculation, selection, matching, or intervention change.
"""
import argparse,json
from pathlib import Path
import numpy as np
import study005_run as study

def normalize(x):
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,np.ndarray):return x.tolist()
    raise TypeError(type(x).__name__)
def put(p,v):Path(p).write_text(json.dumps(v,separators=(',',':'),allow_nan=False,default=normalize)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    amendment=Path(__file__).parent/'amendment-study005.json'
    record=json.loads(amendment.read_text())
    for n,h in record['repair_source_sha256'].items():assert study.sha(Path(__file__).parent/n)==h
    def render_late(out):
        import study005_render
        study005_render.render(out)
    def report_late(out):
        import study005_render
        study005_render.corrected_report(out,original_report)
    original_report=study.report
    study.put=put
    study.render=render_late
    study.report=report_late
    study.run(a.output)
    (Path(a.output)/'amendment005.json').write_bytes(amendment.read_bytes())
    put(Path(a.output)/'execution-repairs005.json',dict(manifest_unchanged=True,amendment_sha256=study.sha(amendment),repair_source_sha256=record['repair_source_sha256']))
