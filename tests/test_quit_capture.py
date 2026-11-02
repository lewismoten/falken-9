"""Quit contracts; synthetic matrix tests are NOT native key coverage."""
from pathlib import Path
import pytest
from py65.devices.mpu6502 import MPU
from scripts.build_graphical_app import build
from scripts.verify_graphical_app import GraphicalMachine

@pytest.fixture(scope='module')
def built(tmp_path_factory):return build(tmp_path_factory.mktemp('quit009'))

class Matrix(list):
    def __init__(self,raw,held=False,pa=0x7f,ddra=255,ddrb=0):
        super().__init__([0]*65536);self[0x800:0x800+len(raw)]=raw
        self[0xdc00:0xdc04]=[pa,0xff,ddra,ddrb];self.held=held;self.reads=[];self.writes=[];self.active=True
    def __getitem__(self,k):
        if isinstance(k,int) and self.active:
            self.reads.append(k)
            if k==0xdc01 and self.held:return 0xbf
        return super().__getitem__(k)
    def __setitem__(self,k,v):
        if getattr(self,'active',False) and isinstance(k,int):self.writes.append(k)
        return super().__setitem__(k,v)

def call(cpu,address):
    cpu.sp=0xd0;cpu.stPushWord(0x17ff);cpu.pc=address
    for _ in range(2000):
        cpu.step()
        if cpu.pc==0x1800:return
    raise AssertionError('unbounded sampler')

@pytest.mark.parametrize('held',[False,True])
@pytest.mark.parametrize('pa,ddra,ddrb',[(0x7f,255,0),(0x7e,255,0),(0xff,255,0),(0x7f,0,0),(0x7f,255,64)])
def test_read_only_matrix_latches_only_supported_stock_column(built,held,pa,ddra,ddrb):
    assert 'quit_sample' in built['labels'],'missing raster-owned quit intent sampler'
    labels=built['labels'];mem=Matrix(Path(built['path']).read_bytes(),held,pa,ddra,ddrb);cpu=MPU(memory=mem)
    mem[labels['quit_active']]=1;mem.writes.clear();zp=bytes(mem[:256])
    call(cpu,labels['quit_sample'])
    assert bool(mem[labels['quit_pending']])==bool(held and (pa,ddra,ddrb)==(0x7f,255,0))
    assert not any(0xdc00<=a<=0xddff for a in mem.writes)
    assert 0xdc0d not in mem.reads,'sampler must not acknowledge pending interrupts'
    assert bytes(mem[:256])==zp and cpu.sp==0xd0
    assert set(mem.writes)<=set(range(0x100,0x200))|{labels['quit_pending'],labels['quit_down']}

@pytest.mark.parametrize('stage',['graph_board_attention','graph_board_norm2','graph_full_forward'])
def test_cancel_actual_forward_normal_unwind_no_partial_mark(built,stage):
    assert 'quit_pending' in built['labels'],'missing latched quit intent'
    g=GraphicalMachine(built);g.until_input();g.key(0x91);title=g.planes();g.key('0',stop_at=stage)
    zp=g.zp_before;g.cpu.memory[g.labels['quit_pending']]=0x80
    g.until_input()
    assert g.get('view')==0 and g.get('history_length')==0
    assert g.get('move_result')==0 and g.get('auto_pausing')==0
    assert g.get('activity_phase')==0 and g.get('audio_protected')==0
    assert bytes(g.cpu.memory[0x20:0x80])==zp and g.cpu.sp==255
    assert g.cpu.memory[1]==0x37 and g.planes()==title and g.immutable_intact()

@pytest.mark.parametrize('port',[0x36,0x37])
@pytest.mark.parametrize('held',[False,True])
def test_matrix_raster_irq_uses_stock_frame_and_preserves_live_cpu(built,port,held):
    from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT
    labels=built['labels'];mem=Matrix(Path(built['path']).read_bytes(),held)
    mem[0xe000:]=Path(DEFAULT_VICE_ROOT/'usr/share/vice/C64/kernal-901227-03.bin').read_bytes()
    mem[0x314:0x316]=labels['audio_irq'].to_bytes(2,'little');mem[1]=port
    mem[labels['audio_protected']]=1;mem[labels['quit_active']]=1;mem[0xd019]=1
    cpu=MPU(memory=mem);cpu.pc=0x1800;cpu.sp=0xb9;cpu.p=0x69;cpu.a=0x83;cpu.x=0xa7;cpu.y=0x79
    zp=bytes(mem[:256]);before=(cpu.pc,cpu.sp,cpu.p,cpu.a,cpu.x,cpu.y);mem.writes.clear();cpu.irq()
    for _ in range(2000):
        assert cpu.pc not in (0xea31,0xea87),'KERNAL scanner entered live ZP'
        cpu.step()
        if cpu.pc==0x1800:break
    else:raise AssertionError('IRQ did not return')
    # Py65 materializes the nonphysical B bit on PLP/RTI; compare actual CPU flags.
    assert (before[0],before[1],before[2]&~cpu.BREAK,*before[3:])==(cpu.pc,cpu.sp,cpu.p&~cpu.BREAK,cpu.a,cpu.x,cpu.y)
    assert bytes(mem[:256])==zp
    assert bool(mem[labels['quit_pending']])==held
    assert not any(0xdc00<=a<=0xddff for a in mem.writes)

@pytest.mark.parametrize('held',[False,True])
def test_release_guard_discards_only_cancel_bytes_and_is_bounded(built,held):
    l=built['labels'];mem=Matrix(Path(built['path']).read_bytes());cpu=MPU(memory=mem)
    mem[l['quit_blocked']]=1;mem[l['quit_down']]=int(held)
    queue=b'QIQMqQ2Q';mem[0x277:0x277+len(queue)]=queue;mem[0xc6]=len(queue)
    call(cpu,l['quit_release_guard'])
    assert mem[0xc6]==3 and bytes(mem[0x277:0x27a])==b'IM2'
    assert mem[l['quit_blocked']]==int(held)
    mem[0xc6]=255;before=bytes(mem[0x277:0x281]);call(cpu,l['quit_release_guard'])
    assert mem[0xc6]==255 and bytes(mem[0x277:0x281])==before

def test_short_matrix_pulse_is_latched_after_release_before_slow_stage_returns(built):
    """Composed real ROM frame + injected matrix, not native timing coverage."""
    from scripts.verify_runtime import AuditedMemory
    from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT
    class PulseMemory(AuditedMemory):
        held=False
        def __getitem__(self,k):
            if k==0xdc01:return 0xbf if self.held else 0xff
            return super().__getitem__(k)
    g=GraphicalMachine(built);g.until_input();g.key('0',stop_at='graph_readout_only')
    mem=g.cpu.memory;mem.__class__=PulseMemory;mem.active=False
    mem[0xe000:]=Path(DEFAULT_VICE_ROOT/'usr/share/vice/C64/kernal-901227-03.bin').read_bytes()
    mem[0xdc00:0xdc04]=[0x7f,0xff,0xff,0];mem[0xd019]=1;mem.active=True
    cpu=g.cpu;pc=cpu.pc;sp=cpu.sp
    def raster(held):
        mem.held=held;cpu.irq()
        for _ in range(2000):
            assert cpu.pc not in (0xea31,0xea87)
            cpu.step()
            if cpu.pc==pc:return
        raise AssertionError('IRQ failed normal return')
    raster(True);assert g.get('quit_pending')==0x80 and cpu.sp==sp
    raster(False);assert g.get('quit_down')==0 and g.get('quit_pending')==0x80
    assert cpu.pc==g.labels['graph_readout_only'],'matrix released before stage resumed'
    g.until_input()
    assert g.get('view')==0 and g.get('history_length')==0 and g.get('move_result')==0
    assert g.cpu.sp==255 and g.get('audio_protected')==0 and g.immutable_intact()
