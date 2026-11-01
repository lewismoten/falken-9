"""Stock-ROM VICE graphical lifecycle with exact packaged input and frames."""
from pathlib import Path
import hashlib
import json
import os
import re
import socket
import subprocess
import time

DEFAULT_VICE_ROOT=Path(os.environ.get('F9_VICE_ROOT',Path(__file__).resolve().parents[2]/'cp64/build/vice-local'))


class Vice:
    def __init__(self,built,image,output,root,*,audio=True,ntsc=False,audio_output='dummy'):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.built=built;self.labels=built['labels'];self.root=Path(root);self.sock=None
        r,w=os.pipe();self.xlog=(self.output/'xvfb.log').open('w')
        self.xvfb=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp'],pass_fds=(w,),stdout=self.xlog,stderr=subprocess.STDOUT)
        os.close(w)
        with os.fdopen(r) as f:display=':'+f.readline().strip()
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        env=os.environ.copy();env['DISPLAY']=display;env['LD_LIBRARY_PATH']=str(self.root/'usr/lib/x86_64-linux-gnu')
        rom=self.root/'usr/share/vice'
        self.command_line=[str(self.root/'usr/bin/x64'),'-default','-directory',str(rom),'-kernal',str(rom/'C64/kernal-901227-03.bin'),'-basic',str(rom/'C64/basic-901226-01.bin'),'-chargen',str(rom/'C64/chargen-901225-01.bin'),'-sound' if audio else '+sound','-warp','-remotemonitor','-remotemonitoraddress',f'ip4://127.0.0.1:{port}']
        self.command_line += ['-ntsc' if ntsc else '-pal']
        if audio:
            self.command_line += ['-sounddev',audio_output,'-soundwarpmode','1']
            if audio_output=='wav':self.command_line += ['-soundarg',str(self.output/'sid.wav')]
        if Path(image).suffix=='.d64':self.command_line+=['-drive8type','1541','-drive8truedrive','+virtualdev8']
        self.command_line+=['-autostart',str(image)]
        self.vlog=(self.output/'vice.log').open('w');self.mlog=(self.output/'monitor.log').open('w')
        self.process=subprocess.Popen(self.command_line,env=env,stdout=self.vlog,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+30
            while self.sock is None:
                try:self.sock=socket.create_connection(('127.0.0.1',port),timeout=.2)
                except OSError:
                    assert self.process.poll() is None,'VICE startup exited'
                    if time.monotonic()>deadline:raise TimeoutError('VICE monitor')
                    time.sleep(.1)
            self.sock.settimeout(.2);self.sock.sendall(b'\n');self.receive(15)
            self.command('sidefx off');self.command('delete')
            self.command(f"break {self.labels['input_wait']:04x}")
            self.command(f"break {self.labels['neural_begin']:04x}")
            self.command(f"break {self.labels['activity_tick']:04x}")
            self.command('disable 3')
            self.requests=[];self.acks=0;self.activity_captured=False
            self.resume()
        except BaseException:
            self.close();raise

    def receive(self,timeout=120):
        data=b'';deadline=time.monotonic()+timeout;seen=False
        while time.monotonic()<deadline:
            try:
                chunk=self.sock.recv(65536)
                if not chunk:raise RuntimeError('VICE disconnected')
                data+=chunk;seen=bool(re.search(rb'\(C:\$[0-9a-fA-F]+\)\s*$',data))
            except socket.timeout:
                if seen:break
        else:raise TimeoutError(f'VICE response {data[-1000:]!r}')
        text=data.decode(errors='replace');self.mlog.write(text);self.mlog.flush()
        assert 'ERROR --' not in text and 'Unknown resource' not in text,text
        return text
    def command(self,text,timeout=120):
        self.mlog.write('>>> '+text+'\n');self.mlog.flush();self.sock.sendall((text+'\n').encode());return self.receive(timeout)
    def registers(self):
        text=self.command('r');m=re.search(r'\.;([\da-fA-F]{4})\s+((?:[\da-fA-F]{2}\s+){6})',text)
        assert m,text
        return int(m[1],16),[int(x,16) for x in m[2].split()]
    def memory(self,address,count=1):
        text=self.command(f'm {address:04x} {address+count-1:04x}');result=[]
        for line in text.splitlines():
            if line.startswith('>C:'):result.extend(int(x,16) for x in line[9:60].split() if re.fullmatch('[0-9a-fA-F]{2}',x))
        assert len(result)>=count,(address,count,text)
        return bytes(result[:count])
    def value(self,name):return self.memory(self.labels[name])[0]
    def history(self):return self.memory(self.labels['history'],self.value('history_length')).decode() if self.value('history_length') else ''
    def resume(self):
        while True:
            self.command('x');pc,regs=self.registers()
            if pc==self.labels['neural_begin']:
                assert self.value('status_index')==2
                assert self.value('history_length')<=8
                self.acks+=1
                if not self.activity_captured:self.command('enable 3')
                continue
            if pc==self.labels['activity_tick']:
                self.command('disable 3')
                self.command('step $10000')
                assert self.value('activity_phase')>0
                self.command(f'screenshot "{self.output/"activity.png"}" 2')
                self.activity_captured=True
                continue
            assert pc==self.labels['input_wait'],hex(pc)
            assert regs[3]==255 and regs[5]==0x37,regs
            expected_irq=self.labels.get('audio_irq',0xea31) if self.value('view')!=3 else 0xea31
            assert self.memory(0x314,2)==expected_irq.to_bytes(2,'little')
            return
    def key(self,key):
        value=ord(key) if isinstance(key,str) else key
        self.command(f'> 0277 {value:02x}');self.command('> 00c6 01');self.resume()
    def capture(self,name):
        self.command('disable 1');self.command('disable 2')
        self.command('step $10000')
        self.command(f'screenshot "{self.output/(name+".png")}" 2')
        self.command('enable 1');self.command('enable 2');self.resume()
        path=self.output/(name+'.png');assert path.read_bytes().startswith(b'\x89PNG')
        return path
    def close(self):
        if self.sock is not None:
            if self.process.poll() is None:
                try:self.sock.sendall(b'quit\n');self.process.wait(5)
                except (OSError,subprocess.TimeoutExpired):pass
            self.sock.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.xvfb.terminate();self.xvfb.wait();self.xlog.close();self.vlog.close();self.mlog.close()


def verify(built,image,output,root,reference=None,*,ntsc=False):
    image=Path(image)
    if image.suffix=='.d64':
        from scripts.build_app import extract_disk
        assert extract_disk(image)==Path(built['prg_path']).read_bytes()
    else:assert image.read_bytes()==Path(built['prg_path']).read_bytes()
    v=Vice(built,image,output,root,ntsc=ntsc)
    try:
        assert v.value('view')==0
        v.command('break ffd5');v.command('break ffc0')
        assert v.value('audio_enabled')==1
        assert v.value('audio_ntsc')==int(ntsc)
        title=v.memory(0x400,1000);v.capture('title')
        v.key('I');assert v.value('view')==1;v.capture('info')
        chars=Path(built['path']).read_bytes();start=built['labels']['info_chars']-built['load']
        decode={value:key for key,value in built['charset_codes'].items()}
        line_count=(built['labels']['info_line_colors']-built['labels']['info_chars'])//29
        lines=[''.join(decode.get(c,'?') for c in chars[start+i*29:start+(i+1)*29]) for i in range(line_count)]
        audio_scroll=max(0,next(i for i,line in enumerate(lines) if 'ORIGINAL SID' in line)-4)
        for _ in range(audio_scroll):v.key(0x11)
        v.capture('info-audio')
        links_scroll=max(audio_scroll,next(i for i,line in enumerate(lines) if 'HTTPS://GITHUB' in line)-4)
        for _ in range(links_scroll-audio_scroll):v.key(0x11)
        v.capture('info-links')
        v.key('Q');assert v.value('view')==0 and v.memory(0x400,1000)==title
        requests=[];matches=[]
        if reference is None:reference=json.loads((Path(output).parent/'py65/games.json').read_text())
        request_index=0
        for match_index,match in enumerate(reference['matches']):
            v.key('1')
            if match_index==0:v.capture('labels')
            for human in match['human_keys']:
                before=v.value('history_length');v.key(human);after=v.value('history_length')
                if after==before+2:
                    expected=reference['requests'][request_index];request_index+=1
                    h=v.history()
                    logits=[int.from_bytes(v.memory(v.labels['logits']+4*i,4),'little',signed=True) for i in range(9)]
                    assert h[:-1]==expected['history'] and h[-1]==expected['selected'] and logits==expected['logits']
                    requests.append(dict(history=h[:-1],selected=h[-1],logits=logits))
                    if len(requests)==1:v.capture('gameplay')
                for invalid in ['0',human,'!']:
                    length=v.value('history_length');v.key(invalid)
                    assert v.value('history_length')==length and v.value('move_result')==0
            assert v.value('terminal')==match['outcome'] and v.history()==match['history']
            v.capture('draw' if match_index==0 else 'model-win')
            matches.append(dict(history=v.history(),outcome=v.value('terminal')))
            v.key('R');assert v.value('history_length')==0
            if match_index==0:v.capture('replayed')
            v.key('Q');v.key('I');v.key('Q');assert v.memory(0x400,1000)==title
        for keys,outcome in [('14253',1),('152347',2),('532846917',3)]:
            v.key('2')
            for key in keys:v.key(key)
            assert v.value('terminal')==outcome
            v.capture('two-human-'+str(outcome))
            v.key('Q')
        v.key('2');v.key('5');v.key('R');assert v.value('history_length')==0
        v.capture('midgame-replay');v.key('Q')
        before=v.acks;v.key('0');assert v.value('terminal')==3 and v.history()==reference['auto_history']
        assert v.acks-before==9
        v.capture('auto-draw');v.key('Q');v.key('I');v.key('Q')
        assert v.value('activity_phase')==0
        from scripts.build_runtime import FOUR_MODEL
        assert v.memory(0x4000,5195)==FOUR_MODEL.read_bytes()
        core=Path(built['path']).parent.joinpath('core/runtime.bin').read_bytes()[:v.labels['code_end']-0x800]
        assert v.memory(0x800,len(core))==core
        app=Path(built['path']).parent.joinpath('app.bin').read_bytes()
        assert v.memory(0x8000,len(app))==app
        assert v.acks==16
        v.key('Q');assert v.value('view')==3;v.capture('quit')
        assert v.value('audio_enabled')==0 and v.memory(0x314,2)==bytes([0x31,0xea])
        result=dict(status='passed',boundary='VICE x64 stock C64 ROM, monitor-injected KERNAL keyboard queue; NOT browser or physical keys',launch_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),prg_sha256=built['prg_sha256'],prg_autostart=image.suffix=='.prg',d64_true_drive_autostart=image.suffix=='.d64',matches=matches,human_model_requests=requests,auto_draw=True,neural_calls=v.acks,full_logits_equal_to_py65=True,code_model_app_immutable=True,stack_final=255,cpu_port=55,irq_vector_restored_on_session_quit=True,sid_driver_enabled_during_games=True,timing='NTSC' if ntsc else 'PAL',no_ingame_LOAD_OPEN=True,screenshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(output).glob('*.png')})
        Path(output,'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:v.close()


if __name__=='__main__':
    import argparse
    from scripts.build_graphical_app import build
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--vice-root',type=Path,default=DEFAULT_VICE_ROOT)
    args=parser.parse_args();built=build()
    print(json.dumps(verify(built,args.image or built['prg_path'],args.output,args.vice_root),indent=2))
