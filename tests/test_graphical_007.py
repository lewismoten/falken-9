"""Mission007 regressions through actual assembled input dispatch."""
from pathlib import Path
import pytest
from scripts.build_graphical_app import build
from scripts.verify_graphical_app import GraphicalMachine
from tests.test_graphical_005_regressions import TraceMemory, trace_key

@pytest.fixture(scope='module')
def built(tmp_path_factory):
    return build(tmp_path_factory.mktemp('ui007'))

def machine(built, monkeypatch):
    monkeypatch.setattr('scripts.verify_graphical_app.AuditedMemory', TraceMemory)
    game=GraphicalMachine(built);game.cpu.memory.cpu=game.cpu;game.until_input()
    return game

def test_badge_actual_title_planes_and_return_paths(built):
    game=GraphicalMachine(built);game.until_input()
    for route in ('initial','info','game','replay'):
        if route=='info':game.key('I');game.key('Q')
        if route in ('game','replay'):
            game.key('2')
            if route=='replay':game.key('5');game.key('R')
            game.key('Q')
        for row,col,text in ((22,30,'FALCON-9'),(23,35,'1.0')):
            assert game.text(row)[col:col+len(text)]==text
            assert bytes(game.cpu.memory[0xd800+row*40+col:0xd800+row*40+col+len(text)])==bytes([6])*len(text)

def test_real_midgame_and_terminal_replay_never_blanks_or_unpacks(built,monkeypatch):
    game=machine(built,monkeypatch);game.key('2')
    fresh=bytes(game.cpu.memory[0x2000:0x4000]),game.planes()
    for keys in ('54','14253','152347','532846917'):
        for key in keys:game.key(key)
        result,_=trace_key(game,'R','replay-'+keys)
        assert not result['den_writes'],result
        assert result['unpack_stores']==0,result
        assert (bytes(game.cpu.memory[0x2000:0x4000]),game.planes())==fresh
        assert game.get('history_length')==game.get('terminal')==game.get('neural_failed')==0
        assert game.get('activity_phase')==game.get('progress_filled')==0
        assert bytes(game.cpu.memory[game.labels['painted_board']:game.labels['painted_board']+9])==bytes(9)
        assert game.expected_board_planes_match() and game.immutable_intact()

def test_all_three_reviewed_light_bands_change_without_other_plane_writes(built,monkeypatch):
    game=machine(built,monkeypatch);game.key('1');game.key('5',stop_at='neural_begin')
    before=bytes(game.cpu.memory[0x400:0x7e8]);game.cpu.memory.trace.clear();game.until_input()
    cells=built['activity_cells']
    assert {c//40 for c in cells}=={16,19,21}
    changed={a-0x400 for _,_,a,v in game.cpu.memory.trace if 0x400<=a<0x7e8 and v!=before[a-0x400]}
    assert all(any(c in changed for c in cells if c//40==r) for r in (16,19,21))
    assert all(game.cpu.memory[0x400+c]==before[c] for c in cells)

def test_footer_exact_paired_glyphs_and_state_style(built):
    assert 'game_footer' in built
    game=GraphicalMachine(built);game.until_input();game.key('2')
    for keys,terminal in (('',0),('14253',1),('152347',2),('532846917',3)):
        for key in keys:game.key(key)
        assert game.get('terminal')==terminal
        footer=built['game_footer']
        for cell,hexglyph in zip(footer['cells'],footer['glyphs']):
            assert bytes(game.cpu.memory[0x2000+8*cell:0x2000+8*cell+8]).hex()==hexglyph
        assert [game.cpu.memory[0x400+c]>>4 for c in footer['replay_cells']]==([1,12,12,12,12] if terminal else [11,6,6,6,6])
        assert [game.cpu.memory[0x400+c]>>4 for c in footer['quit_cells']]==[1,12,12,12]
        game.key('R')

def test_graphical_disk_packaging_names_and_exact_prg(built,tmp_path):
    from scripts.build_app import package_disk, extract_disk, disk_geometry
    gate=dict(status='passed',prg_sha256=built['prg_sha256'],draws=1,model_wins=1,executed_neural_calls=7)
    disk=package_disk(built,gate,tmp_path,stem='falken9-007-graphical',title='FALKEN9 GRAPHIC')
    path=Path(disk['path']);assert path.name=='falken9-007-graphical.d64'
    assert extract_disk(path)==Path(built['prg_path']).read_bytes()
    _,offsets=disk_geometry();at=offsets[18,0]+0x90
    assert path.read_bytes()[at:at+16]==b'FALKEN9 GRAPHIC'.ljust(16,b'\xa0')

def test_continuous_auto_each_game_runs_real_opening_policy(built,monkeypatch):
    assert 'auto_pausing' in built['labels'],'missing continuous demonstration'
    game=machine(built,monkeypatch);game.key('0')
    assert game.neural_calls==9
    assert game.get('terminal')==3 and game.get('auto_pausing')==1
    first=game.get('history',0)-97;assert first==4;calls=game.neural_calls
    game.cpu.memory.active=False
    start=game.get('auto_pause_start')+256*game.get('auto_pause_start',1)
    game.cpu.memory[built['labels']['audio_ticks']:built['labels']['audio_ticks']+2]=((start+120)&65535).to_bytes(2,'little')
    game.cpu.memory.active=True
    result,_=trace_key(game,0,'automatic-replay')
    assert not result['den_writes'] and result['unpack_stores']==0
    assert game.neural_calls-calls==game.get('history_length')
    assert game.get('terminal') in (1,2,3) and game.get('auto_pausing')==1
    game.key('Q');assert game.get('view')==0 and game.cpu.sp==255
    calls=game.neural_calls;game.key('0')
    assert game.neural_calls-calls==9

def test_later_opening_sampler_uses_only_actual_original_coordinate_set(built):
    assert 'auto_resolve_opening' in built['labels'],'missing model-set tie resolution'
    from scripts.verify_app import AppMachine
    m=AppMachine(built,audit=True)
    for name,value in [('mode',0),('auto_later',1),('history_length',0),('terminal',0),('neural_failed',0),('auto_last_opening',7)]:m.put(name,value,1)
    for i in range(9):m.put(m.labels['original_board']+i,0,1);m.put(m.labels['original_set']+i,int(i in (2,7,8)),1)
    audio=bytes(m.cpu.memory[0x5480:0x54a0]);lights=m.get('activity_prng',1,False)
    selected=set()
    for seed in range(256):
        m.put('auto_opening_prng',seed,1)
        result=m.call('auto_resolve_opening')
        assert not result['carry'] and result['cycles']<4000
        move=m.get('selected_move',1,False);selected.add(move)
        assert move in (2,8) and m.get('move_result',1,False)==move+1
    assert selected=={2,8}
    assert bytes(m.cpu.memory[0x5480:0x54a0])==audio and m.get('activity_prng',1,False)==lights
    for i in range(9):m.put(m.labels['original_set']+i,int(i==7),1)
    assert not m.call('auto_resolve_opening')['carry'] and m.get('selected_move',1,False)==7
    m.put(m.labels['original_set']+7,0,1)
    assert m.call('auto_resolve_opening')['carry'] and m.get('move_result',1,False)==0
    # Other turns and modes retain the wrapper result without consuming RNG.
    for mode,length,later in ((1,0,1),(2,0,1),(0,1,1),(0,0,0)):
        m.put('mode',mode,1);m.put('history_length',length,1);m.put('auto_later',later,1)
        m.put('selected_move',4,1);m.put('move_result',5,1);state=m.get('auto_opening_prng',1,False)
        assert not m.call('auto_resolve_opening')['carry']
        assert m.get('selected_move',1,False)==4 and m.get('move_result',1,False)==5 and m.get('auto_opening_prng',1,False)==state

def test_auto_boundary_mute_then_quit_prevents_another_request(built):
    game=GraphicalMachine(built);game.until_input();game.key('0',stop_at='auto_turn')
    game.queue.extend(map(ord,'MQ'));game.until_input()
    assert game.get('view')==0 and game.neural_calls==1
    assert game.get('audio_enabled')==0 and game.get('auto_pausing')==0
    assert game.cpu.sp==255 and game.cpu.memory[1]==0x37

def test_uniform_rejection_geometry_for_every_approved_count(built):
    from collections import Counter
    from scripts.verify_app import AppMachine
    m=AppMachine(built)
    for name,v in [('mode',0),('auto_later',1),('history_length',0),('terminal',0),('neural_failed',0),('auto_last_opening',255)]:m.put(name,v,1)
    for n in range(1,10):
        for i in range(9):m.put(m.labels['original_board']+i,0,1);m.put(m.labels['original_set']+i,int(i<n),1)
        m.put('auto_opening_prng',1,1);counts=Counter()
        for _ in range((255//n)*n):
            assert not m.call('auto_resolve_opening')['carry']
            counts[m.get('selected_move',1,False)]+=1
        assert set(counts)==set(range(n)) and len(set(counts.values()))==1,(n,counts)

def test_sampler_consumes_the_executed_inverse_set_not_canonical_indices(built):
    from scripts.verify_app import AppMachine
    m=AppMachine(built)
    for name,v in [('mode',0),('auto_later',1),('history_length',0),('terminal',0),('neural_failed',0),('auto_last_opening',255)]:m.put(name,v,1)
    for i,t in enumerate((2,5,8,1,4,7,0,3,6)):
        m.put(m.labels['original_board']+i,0,1);m.put(m.labels['selected_transform']+i,t,1)
        m.put(m.labels['logits']+4*i,1000 if i in (0,4) else -1,4)
    assert not m.call('restore_set')['carry']
    assert [i for i in range(9) if m.get(m.labels['original_set']+i,1,False)]==[4,6]
    selected=set()
    for seed in range(256):
        m.put('auto_opening_prng',seed,1);assert not m.call('auto_resolve_opening')['carry'];selected.add(m.get('selected_move',1,False))
    assert selected=={4,6}
