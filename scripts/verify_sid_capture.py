"""Capture actual final-binary VICE SID PCM plus native register/event traces."""
from pathlib import Path
import array
import hashlib
import json
import math
import re
import wave
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT


def summarize_trace(path,built,phases,ntsc):
    records=[];pending=None
    for line in Path(path).read_text().splitlines():
        trace=re.match(r'^#\d+ \(Trace\s+(exec|store) ([0-9a-f]+)\)',line)
        if trace:pending=(trace[1],int(trace[2],16));continue
        if pending and line.startswith('.C:'):
            register=re.search(r'A:([0-9A-Fa-f]{2}).*\s(\d+)$',line)
            if register:records.append(dict(kind=pending[0],address=pending[1],a=int(register[1],16),clock=int(register[2])))
            pending=None
    labels=built['labels'];ticks=[r['clock'] for r in records if r['kind']=='exec' and r['address']==labels['audio_tick']]
    begin=next(p['cpu_clock'] for p in phases if p['name']=='before-human-X-and-full-inference')
    end=next(p['cpu_clock'] for p in phases if p['name']=='after-full-inference-and-model-O')
    live=[clock for clock in ticks if begin<=clock<=end]
    gaps=[b-a for a,b in zip(live,live[1:])]
    assert len(live)>100 and max(gaps)<(19000 if ntsc else 22000)
    events=[r for r in records if r['kind']=='exec' and r['address']==labels['audio_event']]
    assert {1,2,3,4,5} <= {r['a'] for r in events}
    pending_mark=None;low=0;marks=[]
    for r in records:
        if r['kind']=='exec' and r['address']==labels['audio_event'] and r['a'] in (4,5):pending_mark=r['a']
        if r['kind']=='store' and r['address']==0xd40e:low=r['a']
        if r['kind']=='store' and r['address']==0xd40f and pending_mark:
            marks.append(dict(mark='X' if pending_mark==4 else 'O',sid_frequency_word=low+256*r['a'],clock=r['clock']));pending_mark=None
    assert {r['mark'] for r in marks}=={'X','O'} and len({r['sid_frequency_word'] for r in marks})>=2
    result=dict(scope='native VICE trace exec/store records, CPU stopwatch clocks; no synthesized register responses',tick_count=len(ticks),inference_tick_count=len(live),inference_tick_gap_cycles_min=min(gaps),inference_tick_gap_cycles_max=max(gaps),event_ids=sorted({r['a'] for r in events}),mark_frequency_writes=marks,records=records)
    return result


def capture(built,output,root,ntsc=False):
    out=Path(output).resolve();v=Vice(built,built['prg_path'],out,root,ntsc=ntsc,audio_output='wav')
    phases=[]
    def snapshot(name):
        r=v.command('r');line=next(line for line in r.splitlines() if line.startswith('.;'))
        phases.append(dict(name=name,cpu_clock=int(line.split()[-1]),audio_ticks=int.from_bytes(v.memory(v.labels['audio_ticks'],2),'little'),history=v.history()))
    def idle(frames):
        v.command('disable 1');v.command('enable 4');v.command('ignore 4 '+format(frames,'x'));v.command('x')
        assert v.registers()[0]==v.labels['audio_tick']
        v.command('disable 4');v.command('enable 1');v.resume()
    try:
        v.activity_captured=True
        v.command('warp off');assert 'off' in v.command('warp')
        v.command(f"break {v.labels['audio_tick']:04x}");v.command('disable 4')
        v.command(f"trace exec {v.labels['audio_tick']:04x} {v.labels['audio_tick']:04x}")
        v.command('trace store d400 d418')
        v.command(f"trace exec {v.labels['audio_event']:04x} {v.labels['audio_event']:04x}")
        snapshot('idle-music-start');idle(100 if not ntsc else 120);snapshot('idle-music-end')
        v.key(0x11);idle(12);snapshot('navigation-sfx')
        v.key('I');v.key(0x11);idle(12);snapshot('scroll-sfx');v.key('Q')
        v.key('1');snapshot('before-human-X-and-full-inference')
        v.key('5');snapshot('after-full-inference-and-model-O')
        assert v.history()=='ec' and v.acks==1 and v.value('audio_enabled')==1
        idle(25);snapshot('model-O-sfx-released')
        assert v.memory(0xd412)[0]&1==0
        v.key('Q')
        # A second queue byte inserted before the title release guard runs is
        # intentionally stale-cancel input, not a physically fresh Q press.
        # Give the real released matrix/raster and foreground guard an epoch;
        # the following injected byte tests shutdown, not hardware identity.
        idle(2)
        assert v.value('quit_down')==0 and v.value('quit_blocked')==0
        v.key('Q');assert v.value('audio_enabled')==0
        assert all(v.memory(a)[0]==0 for a in (0xd404,0xd40b,0xd412,0xd418))
    finally:v.close()
    path=out/'sid.wav'
    with wave.open(str(path)) as w:
        params=w.getparams();samples=array.array('h',w.readframes(w.getnframes()))
    assert params.sampwidth==2 and params.nchannels in (1,2)
    peak=max(map(abs,samples));clipped=sum(abs(v)>=32767 for v in samples)
    assert 0<peak<32767 and clipped==0 and len(samples)>params.framerate*5
    trace=summarize_trace(out/'monitor.log',built,phases,ntsc)
    (out/'register-trace.json').write_text(json.dumps(trace,indent=2)+'\n')
    result=dict(status='passed',scope='actual VICE x64 MOS8580 SID PCM recording, stock ROM; numeric waveform validation only, NOT listened/physical audio acceptance',prg_sha256=built['prg_sha256'],timing='NTSC' if ntsc else 'PAL',wav=dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),channels=params.nchannels,sample_rate=params.framerate,frames=params.nframes,seconds=params.nframes/params.framerate,peak=peak,rms=math.sqrt(sum(v*v for v in samples)/len(samples)),clipped_samples=clipped,nonzero_samples=sum(v!=0 for v in samples)),phases=phases,trace={k:v for k,v in trace.items() if k!='records'},monitor_trace_sha256=hashlib.sha256((out/'monitor.log').read_bytes()).hexdigest(),vice_command=v.command_line)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(capture(b,sys.argv[2],DEFAULT_VICE_ROOT),indent=2))
