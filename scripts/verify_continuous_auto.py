"""Explicitly composed auto lifecycle gates; NN fixtures are not re-execution."""
from pathlib import Path
import json
from scripts.verify_graphical_app import GraphicalMachine
from scripts.verify_app import AppMachine,fixture_records
from falken9.symmetry import canonicalize

class ComposedMachine(GraphicalMachine):
    def __init__(self,built):
        super().__init__(built);self.fixtures,_=fixture_records();self.requests=[];self.pending=None
    def step(self):
        cpu=self.cpu;mem=cpu.memory;pc=cpu.pc
        if pc==self.labels['graphical_forward']:
            board=tuple(self.get('original_board',i) for i in range(9));canonical,transform=canonicalize(board)
            row=self.fixtures[canonical];logits=row['stages']['logits']
            self.pending=dict(history=self.get('history_length'),board=board,canonical_index=row['canonical_index'],approved=[i for i in range(9) if not board[i] and logits[transform[i]]>=0],previous=self.get('auto_last_opening'))
            for i,v in enumerate(logits):
                for j,b in enumerate(int(v).to_bytes(4,'little',signed=True)):mem[self.labels['logits']+4*i+j]=b
            cpu.p &= ~(cpu.CARRY|cpu.DECIMAL);cpu.pc=(cpu.stPopWord()+1)&65535
            return
        if pc==self.labels['commit_square'] and self.pending is not None:
            record=self.pending;selected=cpu.a
            assert selected in record['approved'] and self.get('original_set',selected)==1
            if record['history'] or not self.get('auto_later'):
                assert selected==next(i for i in (4,1,3,5,7,2,6,8,0) if i in record['approved'])
            elif len(record['approved'])>1 and record['previous'] in record['approved']:
                assert selected!=record['previous']
            record.update(selected=selected,sampled=bool(self.get('auto_sampled')));self.requests.append(record);self.pending=None
        super().step()


def advance_pause(game):
    mem=game.cpu.memory;active=mem.active;mem.active=False
    start=game.get('auto_pause_start')+256*game.get('auto_pause_start',1)
    mem[game.labels['audio_ticks']:game.labels['audio_ticks']+2]=((start+120)&65535).to_bytes(2,'little')
    mem.active=active;game.key(0)


def verify_composed(built,output):
    fixtures,_=fixture_records();empty=fixtures[(0,)*9]['stages']['logits']
    approved=[int(v>=0) for v in empty]
    picker=AppMachine(built);seeds={}
    for name,v in [('mode',0),('auto_later',1),('history_length',0),('terminal',0),('neural_failed',0),('auto_last_opening',255)]:picker.put(name,v,1)
    for i,v in enumerate(approved):picker.put(picker.labels['original_board']+i,0,1);picker.put(picker.labels['original_set']+i,v,1)
    for seed in range(256):
        picker.put('auto_opening_prng',seed,1);assert not picker.call('auto_resolve_opening')['carry'];seeds.setdefault(picker.get('selected_move',1,False),seed)
    assert set(seeds)==set(range(9))
    all_openings=[]
    for opening,seed in sorted(seeds.items()):
        game=ComposedMachine(built);game.until_input();game.key('0',stop_at='neural_begin')
        game.cpu.memory.active=False
        for name,v in [('auto_later',1),('auto_last_opening',255),('auto_opening_prng',seed)]:game.cpu.memory[game.labels[name]]=v
        game.cpu.memory.active=True;game.until_input()
        assert game.get('history',0)==97+opening and game.get('terminal')==3
        assert len(game.requests)==game.get('history_length')==9 and game.get('auto_pausing')==1
        all_openings.append(dict(opening=opening,history=''.join(chr(game.get('history',i)) for i in range(9)),requests=game.requests))
        game.key('Q');assert game.get('view')==0 and game.cpu.sp==255
    game=ComposedMachine(built);game.until_input();game.key('0');histories=[]
    for i in range(40):
        assert game.get('terminal')==3 and game.get('auto_pausing')==1
        histories.append(''.join(chr(game.get('history',j)) for j in range(9)))
        assert game.expected_board_planes_match() and game.immutable_intact()
        if i<39:advance_pause(game)
    assert all(a[0]!=b[0] for a,b in zip(histories,histories[1:]))
    assert len(game.requests)==360
    game.key('Q');assert game.get('view')==0 and game.cpu.sp==255 and game.cpu.memory[1]==0x37
    result=dict(status='passed',scope='executed application/wrapper/sampler/lifecycle using cached frozen NN logits at explicit graphical_forward TEST seam; NOT rerun neural forwards, ROM IRQ timing or physical inputs',prg_sha256=built['prg_sha256'],all_9_openings=all_openings,consecutive_games=40,fixture_requests=360,histories=histories,non_model_marks=0,no_consecutive_opening_repeat=True,stack_final=255)
    Path(output).write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(verify_composed(b,sys.argv[2]),indent=2))
