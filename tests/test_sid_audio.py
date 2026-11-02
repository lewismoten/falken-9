"""Real assembled SID service; flat RAM tests do not establish audible output."""
import pytest
from scripts.build_graphical_app import build
from scripts.verify_app import AppMachine
from scripts.verify_graphical_app import GraphicalMachine
from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT

@pytest.fixture(scope='module')
def built(tmp_path_factory):return build(tmp_path_factory.mktemp('sid007'))

@pytest.mark.parametrize('event,min_frames,min_sustain',[(3,6,8),(4,10,10),(5,12,10)])
def test_foreground_cues_hold_nonzero_envelope_then_release(built,event,min_frames,min_sustain):
    """Electrical support for audibility, not a substitute for PCM/listening."""
    m=AppMachine(built,audit=True);m.call('audio_init')
    m.cpu.a=event;m.call('audio_event');m.call('audio_tick')
    assert m.cpu.memory[0xd412]&1==0,'must retain deferred gate-on'
    assert m.cpu.memory[0xd414]>>4>=min_sustain,'foreground sustain must not decay to zero'
    m.call('audio_tick');assert m.cpu.memory[0xd412]&1
    active=1
    while active<128:
        m.call('audio_tick')
        if not m.cpu.memory[0xd412]&1:break
        active+=1
    assert min_frames<=active<=24,'finite useful gate duration'
    assert m.get('audio_sfx_priority',1,False)==0
    assert m.get('audio_sfx_left',1,False)==0


def test_reserved_voice_priority_retrigger_and_quiet_event_contract(built):
    m=AppMachine(built,audit=True);m.call('audio_init')
    def event(n):m.cpu.a=n;m.call('audio_event')
    def tick():m.call('audio_tick')
    event(5);tick();tick()
    assert m.cpu.memory[0xd412]&1
    pitch=bytes(m.cpu.memory[0xd40e:0xd410])
    for lower in (1,2,3,4):
        event(lower);tick()
        assert m.get('audio_sfx_priority',1,False)==5
        assert bytes(m.cpu.memory[0xd40e:0xd410])==pitch
    event(5);tick();assert m.cpu.memory[0xd412]==0
    tick();assert m.cpu.memory[0xd412]&1
    for _ in range(30):tick()
    for lower in (1,2):
        event(lower);tick()
        assert m.cpu.memory[0xd414]>>4==0,'thinking/scroll remain restrained'
        for _ in range(35):tick()
    assert m.cpu.memory[0xd412]==0
    assert m.cpu.memory[0xd418]==5,'balance is not a global volume boost'
    assert m.cpu.memory[0xd406]==0x48 and m.cpu.memory[0xd40d]==0x58


def test_accepted_navigation_but_boundary_and_invalid_marks_are_silent(built):
    g=GraphicalMachine(built);g.until_input()
    def clear():
        g.cpu.memory.active=False;g.cpu.memory[g.labels['audio_pending']]=0;g.cpu.memory.active=True
    clear();g.key(0x91);assert g.get('audio_pending')==3
    clear();g.key(0x91);assert g.get('audio_pending')==3
    g.key('I');clear();g.key(0x91);assert g.get('audio_pending')==0
    g.key(0x11);assert g.get('audio_pending')==2
    g.key('Q');g.key('2');g.key('1');assert g.get('audio_pending')==4
    clear();g.key('1');assert g.get('audio_pending')==0
    g.key('4');assert g.get('audio_pending')==5


def test_original_score_advances_actual_sid_and_releases_sfx(built):
    assert 'audio_tick' in built['labels'],'missing continuous SID driver'
    m=AppMachine(built,audit=True)
    m.call('audio_init')
    m.put('audio_enabled',1,1);m.put('audio_step',31,1);m.put('audio_frames',1,1);m.put('audio_period',30,1)
    zp=bytes(m.cpu.memory[:256]);states=[]
    for i in range(1000):
        if i==10:m.cpu.a=4;m.call('audio_event')
        m.call('audio_tick')
        states.append(bytes(m.cpu.memory[0xd400:0xd419]))
    assert len({s[:2] for s in states})>=3 and len({s[7:9] for s in states})>=3
    assert any(s[18]&1 for s in states) and not states[-1][18]&1
    assert max(s[24] for s in states)<=5
    assert bytes(m.cpu.memory[:256])==zp
    assert m.get('audio_sfx_left',1,False)==0

def test_distinct_marks_priority_mute_and_actual_noop_dispatch(built):
    assert 'audio_event' in built['labels']
    game=GraphicalMachine(built);game.until_input()
    game.key('I');game.key(0x91);assert game.get('audio_pending')==0
    game.key(0x11);assert game.get('audio_pending')==2
    game.key('Q');game.key('2');game.key('1');assert game.get('audio_pending')==4
    game.key('1');assert game.get('audio_pending')==4
    game.key('4');assert game.get('audio_pending')==5
    game.key('M');assert game.get('audio_enabled')==0
    assert all(game.cpu.memory[0xd400+i]==0 for i in (4,11,18,24))
    game.key('M');assert game.get('audio_enabled')==1
    game.key('Q');game.key('Q');assert game.get('audio_enabled')==0

@pytest.mark.parametrize('port',[0x36,0x37])
@pytest.mark.parametrize('flags',[0x20,0x21,0x28,0x69,0xe9])
def test_stock_rom_irq_frame_preserves_every_live_contract(built,port,flags):
    assert 'audio_irq' in built['labels']
    from pathlib import Path
    from py65.devices.mpu6502 import MPU
    rom=(DEFAULT_VICE_ROOT/'usr/share/vice/C64/kernal-901227-03.bin').read_bytes()
    mem=list(bytes(65536));image=Path(built['path']).read_bytes();mem[0x800:0x800+len(image)]=image
    mem[0xe000:]=rom;mem[0x314:0x316]=list(built['labels']['audio_irq'].to_bytes(2,'little'))
    mem[1]=port;mem[built['labels']['audio_protected']]=1;mem[built['labels']['audio_enabled']]=1
    mem[built['labels']['audio_period']]=30;mem[0xd019]=1
    cpu=MPU(memory=mem);cpu.pc=0x1800;cpu.sp=0xb9;cpu.p=flags;cpu.a=0x83;cpu.x=0xa7;cpu.y=0x79
    zp=bytes(mem[:256]);before=(cpu.pc,cpu.sp,cpu.p,cpu.a,cpu.x,cpu.y)
    cpu.irq();start=cpu.processorCycles
    for _ in range(2000):
        assert cpu.pc not in (0xea31,0xea87),'KERNAL scanner ran against live neural ZP'
        cpu.step()
        if cpu.pc==before[0]:break
    else:pytest.fail('unbalanced IRQ return')
    assert (cpu.pc,cpu.sp,cpu.p & ~cpu.BREAK,cpu.a,cpu.x,cpu.y)==(before[0],before[1],before[2] & ~cpu.BREAK,*before[3:])
    assert bytes(mem[:256])==zp and mem[1]==port
    assert cpu.processorCycles-start<1500

def test_unprotected_cia_chains_with_exact_stock_entry_contract(built):
    from pathlib import Path
    from py65.devices.mpu6502 import MPU
    rom=(DEFAULT_VICE_ROOT/'usr/share/vice/C64/kernal-901227-03.bin').read_bytes()
    outputs=[]
    for hooked in (False,True):
        mem=list(bytes(65536));raw=Path(built['path']).read_bytes();mem[0x800:0x800+len(raw)]=raw;mem[0xe000:]=rom
        target=built['labels']['audio_irq'] if hooked else 0xea31
        mem[0x314:0x316]=target.to_bytes(2,'little');mem[0xd019]=0
        mem[built['labels']['audio_protected']]=0
        mem[built['labels']['audio_old_irq']:built['labels']['audio_old_irq']+2]=b'\x31\xea'
        cpu=MPU(memory=mem);cpu.pc=0x1800;cpu.sp=0xb9;cpu.p=0xe9;cpu.a=0x83;cpu.x=0xa7;cpu.y=0x79
        cpu.irq()
        for _ in range(100):
            if cpu.pc==0xea31:break
            cpu.step()
        else:pytest.fail('did not chain normal KERNAL')
        outputs.append((cpu.a,cpu.x,cpu.y,cpu.p&~cpu.BREAK,cpu.sp,bytes(mem[:256])))
    assert outputs[0]==outputs[1]
