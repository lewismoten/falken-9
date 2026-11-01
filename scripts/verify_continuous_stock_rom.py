"""Multi-game genuine stock-ROM self-play; every request executes real NN."""
from pathlib import Path
import hashlib
import json
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT
from scripts.verify_app import fixture_records
from falken9.symmetry import canonicalize

class ContinuousVice(Vice):
    def __init__(self,*args,**kwargs):
        self.fixtures,_=fixture_records();self.pending=None;self.trace=[];self.stop_boundary=False
        super().__init__(*args,**kwargs)
    def finish_request(self):
        if self.pending is None:return
        p=self.pending;history=self.history();assert history[:-1]==p['history']
        selected=ord(history[-1])-97
        raw=self.memory(self.labels['logits'],36)
        logits=[int.from_bytes(raw[4*i:4*i+4],'little',signed=True) for i in range(9)]
        assert logits==p.pop('expected_logits')
        assert selected in p['approved'] and self.memory(self.labels['original_set']+selected)[0]==1
        if p['history'] or not p['later']:
            assert selected==next(i for i in (4,1,3,5,7,2,6,8,0) if i in p['approved'])
        elif len(p['approved'])>1 and p['previous'] in p['approved']:assert selected!=p['previous']
        ticks=int.from_bytes(self.memory(self.labels['audio_ticks'],2),'little')
        assert (ticks-p['start_ticks'])&65535>100
        p.update(selected=selected,history_after=history,end_ticks=ticks,actual_full_forward=True)
        self.trace.append(p);self.pending=None
    def resume(self):
        while True:
            self.command('x');pc,regs=self.registers()
            if pc==self.labels['neural_begin']:
                self.finish_request()
                original=tuple(self.memory(self.labels['original_board'],9));canonical,transform=canonicalize(original)
                gold=self.fixtures[canonical];logits=gold['stages']['logits']
                self.pending=dict(history=self.history(),canonical_index=gold['canonical_index'],approved=[i for i in range(9) if not original[i] and logits[transform[i]]>=0],expected_logits=logits,later=bool(self.value('auto_later')),previous=self.value('auto_last_opening'),start_ticks=int.from_bytes(self.memory(self.labels['audio_ticks'],2),'little'))
                self.acks+=1;continue
            if self.stop_boundary and pc==self.labels['auto_turn']:
                self.finish_request();return
            assert pc==self.labels['input_wait'],hex(pc)
            self.finish_request()
            assert regs[3]==255 and regs[5]==0x37
            assert self.memory(0x314,2)==self.labels['audio_irq'].to_bytes(2,'little')
            return


def verify(built,image,output,ntsc=False):
    out=Path(output).resolve();v=ContinuousVice(built,image,out,DEFAULT_VICE_ROOT,ntsc=ntsc)
    games=[];holds=[]
    try:
        v.key('0');assert v.acks==9 and v.value('auto_sampled')==0
        v.command(f"break {v.labels['auto_restart']:04x}");v.command('disable 4')
        v.command(f"break {v.labels['auto_turn']:04x}");v.command('disable 5')
        v.command('break store d011 d011')  #6: any blackout/recompose on automatic replay fails
        for i in range(3):
            assert v.value('terminal')==3 and v.value('auto_pausing')==1
            assert v.value('audio_enabled')==1
            h=v.history();assert len(h)==9
            assert v.acks==(i+1)*9
            v.capture('auto-game-'+str(i+1))
            games.append(dict(history=h,outcome=v.value('terminal'),sampled=bool(v.value('auto_sampled')),requests=v.trace[i*9:(i+1)*9]))
            if i<2:
                start=int.from_bytes(v.memory(v.labels['auto_pause_start'],2),'little')
                v.command('disable 1');v.command('enable 4');v.command('x')
                assert v.registers()[0]==v.labels['auto_restart']
                elapsed=(int.from_bytes(v.memory(v.labels['audio_ticks'],2),'little')-start)&65535
                assert 100<=elapsed<=122
                holds.append(dict(frames=elapsed,timing='NTSC' if ntsc else 'PAL'))
                v.command('disable 4');v.command('enable 1');v.resume()
        assert all(a['history'][0]!=b['history'][0] for a,b in zip(games,games[1:]))
        v.command('disable 6');before=v.acks;v.key('Q');assert v.value('view')==0 and v.acks==before
        # A fresh session returns to genuine deterministic model opening, then
        # Q at the next safe boundary must prevent the second request.
        v.stop_boundary=True;v.command('enable 5');v.command('ignore 5 1');v.key('0')
        assert v.value('history_length')==1 and v.history()=='e' and v.acks==before+1
        v.command('disable 5');v.stop_boundary=False;v.key('Q')
        assert v.value('view')==0 and v.acks==before+1 and v.value('auto_pausing')==0
        result=dict(status='passed',scope='actual standalone PRG or true1541 D64 stock-ROM VICE; monitor queue input; real full inference for every mark, audio IRQ active; NOT physical keys/hardware',prg_sha256=built['prg_sha256'],image_sha256=hashlib.sha256(Path(image).read_bytes()).hexdigest(),games=games,automatic_result_holds=holds,actual_neural_requests=v.acks,q_at_result_pause=True,q_between_turns_no_extra_request=True,automatic_replay_no_d011_writes=True,screenshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.png')})
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result
    finally:v.close()

if __name__=='__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text());r=verify(b,sys.argv[2],sys.argv[3]);print(json.dumps({k:v for k,v in r.items() if k!='games'},indent=2))
