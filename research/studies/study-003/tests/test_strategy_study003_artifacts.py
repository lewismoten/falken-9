"""Independent saved-artifact recounts and measured figure bindings."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET


def test_saved_study_recounts_and_figure_contract(tmp_path):
    from scripts.model_strategy_study003 import run
    from scripts.render_strategy_study003 import render
    root=tmp_path/'study';run(root);render(root)
    read=lambda name:json.loads((root/name).read_text())
    cases=read('cases.json');raw=read('raw-alignment.json');rs={v['id']:v for v in read('results.json')}
    vectors=read('experiment-vectors.json');priority=[4,1,3,5,7,2,6,8,0]
    for experiment in vectors:
        bad=empty=set_change=tie=0
        logits=np.array(experiment['logits'])
        for row in raw:
            cid=row['canonical_index'];t=row['original_to_canonical'];b=row['board']
            chosen={j for j in range(9) if not b[j] and logits[cid,t[j]]>=0}
            target=set(row['optimal_set']);move=next((j for j in priority if j in chosen),-1)
            empty+=not bool(chosen);bad+=move not in target;set_change+=chosen!=target
            tie+=move in target and move!=row['baseline_move']
        stats=rs[experiment['id']]['raw']
        assert (bad,empty,set_change,tie)==(stats['nonoptimal_including_empty'],stats['empty_set'],stats['complete_set_change'],stats['equivalent_optimal_tie_change'])
    keys=('ply','side','own_corners','opponent_corners','own_edges','opponent_edges','center_own','center_opponent')
    for pair in read('donor-pairs.json'):
        receiver=cases[pair['receiver']];donor=cases[pair['donor']];e,u=pair['component'];task=pair['task']
        assert receiver['fold']!='train' and donor['fold']=='train'
        assert receiver['id']!=donor['id']
        assert receiver['routes']==donor['routes']
        assert all(receiver['labels'][k]==donor['labels'][k] for k in keys)
        assert max(abs(a-b) for a,b in zip(receiver['gates'],donor['gates']))==pair['gate_delta']<=4096
        assert sum(a!=b for a,b in zip(receiver['board'],donor['board']))==pair['hamming']
        assert (receiver['labels'][task]!=donor['labels'][task])==pair['cross_class']
        assert receiver['hidden'][e][u]==pair['receiver_activation']
        assert donor['hidden'][e][u]==pair['donor_activation']
    metadata=read('figure-metadata.json')
    assert set(metadata['callouts'])=={'A','B','C','P','M+','M-'}
    assert metadata['callouts']['A']['activation_coordinate']==['expert_hidden',1,0]
    assert metadata['callouts']['B']['activation_coordinate']==['expert_hidden',3,3]
    for item in metadata['figures']:
        assert Image.open(root/(item['name']+'.png')).size==tuple(item['size'])
        assert ET.parse(root/(item['name']+'.svg')).getroot().tag.endswith('svg')
        assert all(0<=b[0]<=b[2]<=item['size'][0] and 0<=b[1]<=b[3]<=item['size'][1] for b in item['text_bounds'])
    assert 'Unsupported' in (root/'REPORT.md').read_text()
