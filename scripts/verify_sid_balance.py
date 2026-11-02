"""Native VICE finite event windows, not a listening-acceptance oracle.

Monitor-injected event requests exercise the real IRQ/SID service. No host
synthesis, gain normalization, or replacement SID renderer is used.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import wave
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT


def capture(built, output, *, music=False, ntsc=False, events=(3,4,5,3,3,4,1,5,2), root=DEFAULT_VICE_ROOT):
    out=Path(output).resolve()
    v=Vice(built,built['prg_path'],out,root,ntsc=ntsc,audio_output='wav')
    phases=[]
    def clock():
        return int(next(s for s in v.command('r').splitlines() if s.startswith('.;')).split()[-1])
    def put(name,value):v.command(f"> {v.labels[name]:04x} {value:02x}")
    def advance(frames):
        v.command('ignore 4 '+format(frames-1,'x'));v.command('x')
        assert v.registers()[0]==v.labels['audio_tick']
    try:
        v.activity_captured=True
        v.command('warp off')
        v.command('disable 1');v.command('disable 2')
        v.command(f"break {v.labels['audio_tick']:04x}")
        v.command('x')
        v.command('trace store d40e d414')
        v.command(f"trace exec {v.labels['audio_event']:04x} {v.labels['audio_event']:04x}")
        if not music:
            v.command('> d404 00');v.command('> d40b 00')
        # Same initial release/preroll in every render.
        put('audio_frames',200 if not music else 1)
        advance(60 if ntsc else 50)
        for event in events:
            if not music:put('audio_frames',200)
            put('audio_pending',event)
            begin=clock()
            advance(30 if ntsc else 25)
            phases.append(dict(event=event,clock=begin,end_clock=clock(),gate=v.memory(0xd412)[0],priority=v.value('audio_sfx_priority')))
            assert v.memory(0xd412)[0]&1==0
        end=clock()
    finally:v.close()
    wav=out/'sid.wav'
    with wave.open(str(wav)) as w:
        params=w.getparams();samples=array.array('h',w.readframes(w.getnframes()))
    cpu_hz=1022727 if ntsc else 985248
    windows=[]
    for i,p in enumerate(phases):
        # Anchor to recording end; include one mixer-buffer margin on both sides.
        stop=params.nframes-round((end-p['end_clock'])/cpu_hz*params.framerate)
        start=stop-round((p['end_clock']-p['clock'])/cpu_hz*params.framerate)
        start=max(0,start);stop=min(params.nframes,stop)
        pcm=samples[start*params.nchannels:stop*params.nchannels]
        dest=out/f"{i:02d}-event-{p['event']}.wav"
        with wave.open(str(dest),'wb') as w:
            w.setparams(params);w.writeframes(pcm.tobytes())
        windows.append(dict(**p,path=str(dest),start_sample=start,end_sample=stop,rms=math.sqrt(sum(x*x for x in pcm)/max(1,len(pcm))),peak=max(map(abs,pcm),default=0),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    result=dict(scope='Actual VICE MOS8580 PCM; event-window end anchored to CPU clock/recording end; buffer offset may affect window edges; not listening approval',prg_sha256=built['prg_sha256'],music=music,timing='NTSC' if ntsc else 'PAL',vice_command=v.command_line,wav_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),sample_rate=params.framerate,channels=params.nchannels,frames=params.nframes,peak=max(map(abs,samples)),clipped_samples=sum(abs(x)>=32767 for x in samples),windows=windows)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('built');p.add_argument('output');p.add_argument('--music',action='store_true');p.add_argument('--ntsc',action='store_true')
    a=p.parse_args();print(json.dumps(capture(json.loads(Path(a.built).read_text()),a.output,music=a.music,ntsc=a.ntsc),indent=2))
