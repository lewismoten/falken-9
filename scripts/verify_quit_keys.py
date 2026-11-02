"""XTest key events in our isolated VICE display, never KERNAL queue input.

Monitor stepping pauses CPU time, not physical key-state semantics. Evidence
records CPU clocks at instruction stops, not host latency or browser coverage.
"""
from pathlib import Path
import ctypes as C
import json, os, re
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT

class KeyVice(Vice):
    def resume(self):
        self.command('x')
    def setup_keys(self):
        env=Path(f'/proc/{self.process.pid}/environ').read_bytes().split(b'\0')
        display=next(x.split(b'=',1)[1] for x in env if x.startswith(b'DISPLAY='))
        self.x=C.CDLL('libX11.so.6');self.xt=C.CDLL('libXtst.so.6')
        self.x.XOpenDisplay.argtypes=[C.c_char_p];self.x.XOpenDisplay.restype=C.c_void_p
        self.d=self.x.XOpenDisplay(display);assert self.d
        self.x.XDefaultRootWindow.argtypes=[C.c_void_p];self.x.XDefaultRootWindow.restype=C.c_ulong
        self.x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        self.x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_char_p)]
        self.x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
        self.x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];self.x.XKeysymToKeycode.restype=C.c_uint
        self.x.XSync.argtypes=[C.c_void_p,C.c_int]
        self.x.XAutoRepeatOff.argtypes=[C.c_void_p]
        self.x.XAutoRepeatOff(self.d)  # isolated Xvfb only: monitor pauses must not queue host repeats
        self.xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
        def walk(w):
            name=C.c_char_p();self.x.XFetchName(self.d,w,C.byref(name))
            title=name.value.decode(errors='replace') if name.value else ''
            if 'VICE' in title and 'monitor' not in title.lower():return w,title
            root=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();n=C.c_uint()
            self.x.XQueryTree(self.d,w,C.byref(root),C.byref(parent),C.byref(children),C.byref(n))
            for i in range(n.value):
                found=walk(children[i])
                if found:return found
        self.window,self.window_title=walk(self.x.XDefaultRootWindow(self.d))
        self.x.XSetInputFocus(self.d,self.window,1,0);self.x.XSync(self.d,0)
        self.events=[]
    def event(self,key,down):
        code=self.x.XKeysymToKeycode(self.d,ord(key))
        assert self.xt.XTestFakeKeyEvent(self.d,code,int(down),0)
        self.x.XSync(self.d,0)
        self.events.append(dict(key=key,down=down,source='XTestFakeKeyEvent',window=self.window_title))
    def steps(self,n):return self.command(f'step ${n:x}')
    def until(self,label,*,forbid_commit=False):
        self.command('delete');self.command(f"break {self.labels[label]:04x}")
        if forbid_commit:self.command(f"break {self.labels['commit_square']:04x}")
        self.command('x')
        assert self.registers()[0]==self.labels[label], 'post-cancel commit or unexpected stop'
    def clock(self):
        text=self.command('r');return int(re.search(r'\s(\d+)\s*\n\(C:',text)[1])

def baseline(built,image,output):
    v=KeyVice(built,image,output,DEFAULT_VICE_ROOT,audio=False)
    try:
        v.setup_keys();assert v.value('view')==0
        v.command('delete');v.command(f"break {v.labels['graph_board_attention']:04x}")
        v.event('0',True);v.steps(100000);v.event('0',False)
        v.command('x');assert v.registers()[0]==v.labels['graph_board_attention']
        assert v.value('audio_protected')==1
        before=dict(history_length=v.value('history_length'),queue=v.memory(0xc6)[0],cia=list(v.memory(0xdc00,4)))
        v.command('delete');v.event('q',True);v.steps(100000)
        held=dict(queue=v.memory(0xc6)[0],cia=list(v.memory(0xdc00,4)),view=v.value('view'))
        v.event('q',False);v.steps(100000)
        released=dict(queue=v.memory(0xc6)[0],cia=list(v.memory(0xdc00,4)),view=v.value('view'))
        v.command(f"break {v.labels['input_wait']:04x}");v.command('x')
        result=dict(status='red-reproduced' if v.value('view')==2 else 'unexpected',image=str(image),prg_sha256=built['prg_sha256'],before=before,held=held,released=released,final_view=v.value('view'),final_history=v.history(),events=v.events,boundary='Native XTest press/release during actual full NN; no KERNAL queue writes')
        Path(output,'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        assert result['status']=='red-reproduced'
    finally:v.close()

def verify_keys(built,image,output,*,ntsc=False,stages=None,human=None):
    v=KeyVice(built,image,output,DEFAULT_VICE_ROOT,audio=True,ntsc=ntsc)
    cases=[]
    try:
        v.setup_keys()
        # All game-start and quit controls below are real XTest events.
        specs=stages or [('graph_board_attention',0,False),('graph_attention_softmax_row',0,False),('graph_board_norm2',0,False),('output_head',0,False),('graph_board_attention',3,False),('graph_board_attention',9,False),('graph_board_attention',0,True),('auto_pause_begin',0,False)]
        for stage,skip,muted in specs:
            assert v.value('view')==0
            if muted:
                v.event('m',True);v.steps(100000);v.event('m',False);v.steps(100000)
                assert v.value('audio_enabled')==0
            v.command('delete');v.command(f"break {v.labels[stage]:04x}")
            if skip:v.command(f'ignore 1 {skip}')
            start='1' if human else '0'
            v.event(start,True);v.steps(100000);v.event(start,False)
            if human:
                v.steps(100000);assert v.value('view')==2
                v.event(human,True);v.steps(100000);v.event(human,False)
            if v.registers()[0]!=v.labels[stage]:v.command('x')
            assert v.registers()[0]==v.labels[stage]
            assert v.value('audio_protected')==int(stage!='auto_pause_begin')
            history=v.history();port=v.memory(1)[0];cia=list(v.memory(0xdc00,4))
            v.command('delete')
            if stage=='auto_pause_begin':v.command(f"break {v.labels['auto_exit']:04x}")
            else:v.command(f"watch store {v.labels['quit_pending']:04x}")
            press=v.clock();v.event('q',True);v.command('x');capture=v.clock()
            pending=v.value('quit_pending');matrix=list(v.memory(0xdc00,4))
            if stage=='auto_pause_begin':
                assert v.registers()[0]==v.labels['auto_exit']
                capture_source='raster-latch' if pending==0x80 else 'GETIN from real stock-ROM matrix scan'
            else:
                assert pending==0x80 and matrix[0]==127 and matrix[1]&64==0
                capture_source='raster-latch'
            v.event('q',False)
            for _ in range(2):
                v.until('input_wait',forbid_commit=True)
                if v.value('view')==0:break
            menu=v.clock()
            assert v.value('view')==0 and v.value('history_length')==0
            assert v.value('move_result')==0 and v.value('auto_pausing')==0
            assert v.value('audio_protected')==0 and v.memory(1)[0]==port
            assert v.registers()[1][3]==255
            v.command('delete');v.steps(100000)
            assert v.value('view')==0 and v.value('quit_down')==0
            assert list(v.memory(0xdc00,4))==[127,255,255,0]
            name=f'{stage}-skip{skip}-mute{int(muted)}'
            v.command(f'screenshot "{Path(output)/(name+"-menu.png")}" 2')
            cases.append(dict(stage=stage,capture_source=capture_source,captured_pending=pending,captured_matrix=matrix,skipped_requests=skip,muted=muted,later_game=bool(skip>=9),history_before=history,cia_before=cia,press_clock=press,capture_clock=capture,menu_clock=menu,press_to_capture_cycles=capture-press,press_to_menu_cycles=menu-press,stack=255,view=0,no_canceled_mark=True))
            Path(output,'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
            if muted:
                v.event('m',True);v.steps(100000);v.event('m',False);v.steps(100000)
                assert v.value('audio_enabled')==1
        # Held Q must not become title/session quit; release, then INFO is usable.
        v.command('delete');v.command(f"break {v.labels['graph_board_attention']:04x}")
        v.event('0',True);v.steps(100000);v.event('0',False)
        if v.registers()[0]!=v.labels['graph_board_attention']:v.command('x')
        v.command('delete');v.command(f"watch store {v.labels['quit_pending']:04x}")
        v.event('q',True);v.command('x');v.until('input_wait',forbid_commit=True)
        v.command('delete');v.steps(200000)
        assert v.value('view')==0 and v.value('quit_blocked')==1 and v.value('quit_down')==1
        v.event('q',False)
        for _ in range(10):
            v.steps(100000)
            if v.value('quit_blocked')==0:break
        assert v.value('view')==0 and v.value('quit_blocked')==0, (v.memory(0xdc00,4),v.value('quit_down'))
        v.event('i',True);v.steps(100000);v.event('i',False);v.steps(100000)
        assert v.value('view')==1
        v.event('q',True);v.steps(100000);v.event('q',False);v.steps(100000);assert v.value('view')==0
        # A genuinely release-separated title Q must still end the session.
        v.event('q',True);v.steps(100000);v.event('q',False);v.steps(100000)
        assert v.value('view')==3 and v.value('audio_enabled')==0
        assert v.memory(0x314,2)==b'\x31\xea'
        assert all(v.memory(a)[0]==0 for a in (0xd404,0xd40b,0xd412,0xd418))
        result=dict(status='passed',fresh_title_Q_shutdown=True,prg_sha256=built['prg_sha256'],image=str(image),timing='NTSC' if ntsc else 'PAL',true_drive=Path(image).suffix=='.d64',cases=cases,held_Q_safe=True,info_after_release=True,events=v.events,boundary='XTest key-down/up into isolated native VICE Xvfb window; actual CIA matrix; NOT browser/physical C64')
        Path(output,'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result
    finally:v.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');p.add_argument('--output',type=Path,required=True);p.add_argument('--build',type=Path,default=Path('build/quit009/build.json'));p.add_argument('--image',type=Path);p.add_argument('--ntsc',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if a.baseline:
        b=json.loads((root/'artifacts/app/008-graphical/build.json').read_text());baseline(b,root/'artifacts/app/008-graphical/falken9-008-graphical.prg',a.output)
    else:
        b=json.loads(a.build.read_text());print(json.dumps(verify_keys(b,a.image or b['prg_path'],a.output,ntsc=a.ntsc),indent=2))
