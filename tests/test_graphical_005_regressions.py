"""Executed UI regressions reported against delivered004; no host redraw stand-in."""
import json
import os
from pathlib import Path

import pytest

from scripts.build_graphical_app import build
from scripts.verify_graphical_app import GraphicalMachine
from scripts.verify_runtime import AuditedMemory


class TraceMemory(AuditedMemory):
    def __init__(self, regions):
        super().__init__(regions)
        self.trace = []
        self.cpu = None

    def __setitem__(self, at, value):
        if self.active and self.cpu is not None and (at == 0xd011 or 0x400 <= at < 0x7e8 or 0x2000 <= at < 0x4000 or 0xd800 <= at < 0xdbe8 or 0x7850 <= at < 0x7900):
            self.trace.append((self.cpu.processorCycles, self.cpu.pc, at, value))
        super().__setitem__(at, value)


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    return build(tmp_path_factory.mktemp('ui005'))


def traced_game(built, monkeypatch):
    monkeypatch.setattr('scripts.verify_graphical_app.AuditedMemory', TraceMemory)
    game = GraphicalMachine(built)
    game.cpu.memory.cpu = game.cpu
    game.until_input()
    game.cpu.memory.trace.clear()
    return game


def trace_key(game, key, name):
    game.cpu.memory.trace.clear()
    start = game.cpu.processorCycles
    game.key(key)
    trace = game.cpu.memory.trace
    den = [dict(cycle=c-start, pc=pc, value=v) for c,pc,a,v in trace if a == 0xd011]
    visual = {a for c,pc,a,v in trace if 0x400 <= a < 0x7e8 or 0x2000 <= a < 0x4000 or 0xd800 <= a < 0xdbe8}
    result = dict(name=name, prg_sha256=game.build['prg_sha256'], cycles=game.cpu.processorCycles-start,
                  den_writes=den, visual_distinct_addresses=len(visual),
                  unpack_stores=sum(pc == game.labels['unpack_store']+2 for _,pc,_,_ in trace))
    if os.environ.get('UI_TRACE_DIR'):
        out = Path(os.environ['UI_TRACE_DIR']); out.mkdir(parents=True, exist_ok=True)
        (out/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    return result, visual


def test_arrows_patch_selector_without_den_or_plane_unpack(built, monkeypatch):
    game = traced_game(built, monkeypatch)
    for key, expected in [(0x11, 2), (0x11, 0), (0x91, 2), (0x91, 1)]:
        result, visual = trace_key(game, key, 'arrow-'+str(key)+'-'+str(expected))
        assert game.get('mode') == expected
        assert not result['den_writes'], result
        allowed = {base+row*40+9 for base in (0x400, 0xd800) for row in (9,11,13)}
        assert visual <= allowed
        assert result['cycles'] < 4000
        assert game.cpu.sp == 255 and game.cpu.memory[1] == 0x37
        assert game.immutable_intact()


def test_normal_moves_patch_cells_without_den_or_full_plane_unpack(built, monkeypatch):
    game = traced_game(built, monkeypatch)
    game.key('2')
    for key in '532846917':
        result, visual = trace_key(game, key, 'move-'+key)
        assert not result['den_writes'], result
        assert len(visual) < 600
        assert result['cycles'] < 70000
        assert game.expected_board_planes_match()
    assert game.get('terminal') == 3
    assert game.immutable_intact()


def test_original_footer_and_exact_requested_badge_on_every_title_return(built):
    game = GraphicalMachine(built); game.until_input()
    for route in ('initial', 'info', 'game', 'replay'):
        if route == 'info': game.key('I'); game.key('Q')
        if route in ('game', 'replay'):
            game.key('2')
            if route == 'replay': game.key('5'); game.key('R')
            game.key('Q')
        for row, text in [(22, 'INFO'), (23, 'QUIT')]:
            assert game.text(row)[2:6] == text
            assert bytes(game.cpu.memory[0xd800+row*40+2:0xd800+row*40+6]) == bytes([1,12,12,12])
        for row,col,text in [(22,30,'FALCON-9'),(23,35,'1.0')]:
            assert game.text(row)[col:col+len(text)] == text
            assert bytes(game.cpu.memory[0xd800+row*40+col:0xd800+row*40+col+len(text)]) == bytes([6])*len(text)


def test_info_white_markdown_scroll_and_complete_repository_links(built):
    game = GraphicalMachine(built); game.until_input(); game.key('I')
    assert bytes(game.cpu.memory[0xd800+4*40+5:0xd800+4*40+34]) == bytes([1])*29
    rows = [game.text(r)[5:34].rstrip() for r in range(4,22)]
    assert 'FALCON-9' in ''.join(rows)
    for _ in range(100):
        before = game.planes(); game.key(0x11)
        if game.planes() == before: break
        rows.append(game.text(21)[5:34].rstrip())
    text = ''.join(rows)
    assert 'HTTPS://GITHUB.COM/LEWISMOTEN/FALCON-9' in text
    assert 'HTTPS://HUGGINGFACE.CO/LEWISMOTEN/FALCON-9' in text
    assert 'NOT YET PUBLISHED' in text
    assert 'QUIT: Q' in game.text(23)
    game.key('Q'); assert game.get('view') == 0


def test_info_footer_highlights_the_actual_quit_key_not_its_separator(built):
    game=GraphicalMachine(built);game.until_input();game.key('I')
    for _ in range(24):
        assert game.text(23)[26:33]=='QUIT: Q'
        assert game.cpu.memory[0xd800+23*40+32]==1
        assert bytes(game.cpu.memory[0xd800+23*40+26:0xd800+23*40+31])==bytes([12])*5
        game.key(0x11)


def test_original_console_outside_board_status_meter_and_lights_is_untouched(built):
    game = GraphicalMachine(built); game.until_input(); game.key('2')
    packed = Path(built['path']).parent.joinpath('graphics.bin').read_bytes()
    for plane, base, size in [('bitmap',0x2000,8000), ('screen',0x400,1000), ('color',0xd800,1000)]:
        region = built['graphics']['regions']['board_'+plane]
        original = packed[region['offset']:region['offset']+size]
        scale = 8 if plane == 'bitmap' else 1
        for row in (17,23):
            assert bytes(game.cpu.memory[base+row*40*scale:base+(row+1)*40*scale]) == original[row*40*scale:(row+1)*40*scale]
    game.key('5')
    assert bytes(game.cpu.memory[0x3218:0x3220]) == bytes.fromhex('0014414141411400')


def test_real_forward_progress_role_colors_commit_only_full_and_reset(built, monkeypatch):
    assert 'progress_begin' in built['labels'], 'missing actual compute meter'
    game = traced_game(built, monkeypatch); game.key('1')
    game.key('5', stop_at='neural_begin')
    assert game.get('progress_active') == 1 and game.get('progress_filled') == 0
    assert game.cpu.memory[0x63e] >> 4 == 6  # O blue, prior to compute
    game.cpu.memory.trace.clear(); game.until_input()
    fills = [v for _,_,a,v in game.cpu.memory.trace if a == game.labels['progress_filled']]
    assert fills[-1] == 0 and 48 in fills
    completion = fills.index(48)
    assert fills[:completion] == sorted(fills[:completion])
    assert max(fills[:completion]) < 48 and len(set(fills[:completion])) > 8
    full_write = next(i for i,(_,_,a,v) in enumerate(game.cpu.memory.trace) if a == game.labels['progress_filled'] and v == 48)
    assert any(0x2000 <= a < 0x3180 for _,_,a,_ in game.cpu.memory.trace[:full_write])
    assert game.get('progress_active') == 0 and game.get('progress_filled') == 0
    assert game.cpu.memory[0x63e] >> 4 == 0
    assert not [1 for _,_,a,_ in game.cpu.memory.trace if a == 0xd011]
    # First automatic side X: inspect BEFORE running the nine-forward match.
    game.key('Q'); game.key('0', stop_at='neural_begin')
    assert game.cpu.memory[0x63e] >> 4 == 2


def test_activity_is_dispersed_and_preserves_all_live_state(built):
    from scripts.verify_app import AppMachine
    assert 'activity_cells' in built, 'missing reviewed button footprint'
    cells = built['activity_cells']
    assert len(cells) >= 7 and min(cells) % 40 < 15 and max(cells) % 40 > 25
    machine = AppMachine(built, audit=True)
    machine.put('activity_phase', 0, 1)
    machine.cpu.a=0x83; machine.cpu.x=0x79; machine.cpu.y=0xa7
    zp=bytes(machine.cpu.memory[:256]); port=machine.cpu.memory[1]
    machine.call('activity_tick')
    assert (machine.cpu.a,machine.cpu.x,machine.cpu.y) == (0x83,0x79,0xa7)
    assert machine.cpu.p & machine.cpu.DECIMAL
    assert bytes(machine.cpu.memory[:256]) == zp and machine.cpu.memory[1] == port
    allowed={*range(0x100,0x200), built['labels']['activity_phase'], built['labels']['activity_prng'], built['labels']['audio_pending'],*(0x400+c for c in cells)}
    assert machine.cpu.memory.addresses <= allowed
    assert set(0x400+c for c in cells) <= machine.cpu.memory.addresses


def test_precommit_meter_is_visually_distinct_from_complete(built):
    from scripts.verify_app import AppMachine
    machine=AppMachine(built)
    machine.put('progress_color',0x60,1)
    before=machine.cpu.memory[built['labels']['progress_thresholds']+31]
    images=[]
    for filled in (before,48):
        machine.put('progress_filled',filled,1)
        cpu=machine.cpu;cpu.sp=0xfd;cpu.pc=built['labels']['paint_progress']
        cpu.memory[0x1fe:0x200]=[0xff,1];cpu.p=cpu.UNUSED|cpu.INTERRUPT
        while cpu.pc!=0x200:cpu.step()
        images.append(bytes(cpu.memory[0x31f0:0x3258]))
    assert images[0]!=images[1], 'outline must not conceal the last unfilled interior pixel'


def test_policy_failure_clears_meter_and_replay_restores_known_state(built):
    game=GraphicalMachine(built);game.until_input();game.key('1')
    game.key('5',stop_at='neural_begin')
    game.cpu.memory[built['labels']['history_length']]=10  # real policy validation error
    game.until_input()
    assert game.get('neural_failed')==1 and game.get('move_result')==0
    assert game.get('progress_active')==0 and game.get('progress_filled')==0
    assert game.get('activity_phase')==0 and not game.phases
    assert game.cpu.sp==255 and game.cpu.memory[1]==0x37
    game.key('R');assert game.get('history_length')==0 and game.get('neural_failed')==0
    assert game.expected_board_planes_match()
    game.key('Q');game.key('I');game.key('Q')
    assert game.get('view')==0 and game.immutable_intact()


def test_progress_callback_preserves_live_state_and_exact_meter_footprint(built):
    from scripts.verify_app import AppMachine
    m=AppMachine(built,audit=True)
    for name,value in [('progress_active',1),('progress_event_index',0),('progress_filled',0),('progress_color',0x60),('activity_phase',0)]:m.put(name,value,1)
    zp=bytes(m.cpu.memory[:256]);turn=bytes(m.cpu.memory[0x3218:0x3220]);vectors=bytes(m.cpu.memory[0x6000:0x7800])
    m.cpu.a=0x83;m.cpu.x=0x79;m.cpu.y=0xa7
    result=m.call('progress_event')
    assert (m.cpu.a,m.cpu.x,m.cpu.y)==(0x83,0x79,0xa7) and m.cpu.p&m.cpu.DECIMAL and result['carry']==0
    assert bytes(m.cpu.memory[:256])==zp and bytes(m.cpu.memory[0x6000:0x7800])==vectors
    assert bytes(m.cpu.memory[0x3218:0x3220])==turn
    cells=[0x63e+i for i in range(13) if i!=5]
    allowed={*range(0x100,0x200),built['labels']['activity_phase'],built['labels']['activity_prng'],built['labels']['audio_pending'],*range(built['labels']['progress_active'],built['labels']['progress_pattern']+1),*(0x400+c for c in built['activity_cells']),*cells,*(0x2000+(c-0x400)*8+i for c in cells for i in range(8))}
    assert m.cpu.memory.addresses<=allowed
