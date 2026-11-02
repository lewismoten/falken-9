import research678_stage008 as a
import numpy as np

def test_preconfirmation_panel_uses_actual_descriptor_axes():
    assert hasattr(a,'coordinate_panel'),'missing architecture-validated coordinate panel'
    c={'width':8,'tensors':{'norm2.weight':{'shape':(8,)},'norm2.bias':{'shape':(8,)}}}
    merged=np.array([[0,8,1,2,3,4,5,6],[999,0,0,0,0,0,0,0]])
    coords,u=a.coordinate_panel(c,merged,np.array([0,2]))
    assert u==1 and len(coords)==38
    assert sum(n=='norm2.weight' for n,co,r in coords)==8
    assert sum(n=='norm2.bias' for n,co,r in coords)==8
    assert all(co[-1]<8 for n,co,r in coords if n.startswith('norm2'))
    assert [co for n,co,r in coords if n=='output.weight']==[(s,1) for s in range(9)]
