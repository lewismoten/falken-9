#!/home/ai/falken-9/.venv/bin/python
"""Read-only frozen application010 isolated assembled-subroutine parity.
Run with the project's py65 interpreter. Writes JSON only under scratch.
No assembly, release edits, ROM/I/O/game execution, or empirical fairness claim.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ART = Path('/home/ai/falken-9/artifacts/app/010-graphical')
STUDY = Path('/home/ai/falken9-playpath-study-015')
SCRATCH = Path('/home/ai/.hermes/cache/scratch')
EXPECTED = {'prg':'c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a', 'd64':'2570b642780ea6dd2e64c1b915e4bf3143fd8d86e1f9e2224f483f53d9bdb21d'}
BOUND = 4096

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main(out):
    assert out.resolve().is_relative_to(SCRATCH.resolve())
    paths = {'prg':ART/'falken9-010-graphical.prg', 'd64':ART/'falken9-010-graphical.d64', 'listing':ART/'app.lst', 'source':Path('/home/ai/falken-9/src/app/auto_demo.asm'), 'census':STUDY/'results015/sampler-state-census015.json', 'orbit':STUDY/'results015/opening-transitions015.json', 'independent_audit':STUDY/'study015_audit.py'}
    before = {k:sha(p) for k,p in paths.items()}
    assert all(before[k]==v for k,v in EXPECTED.items())
    listing=paths['listing'].read_text()
    syms={name:int(addr,16) for name,addr in re.findall(r'\b([A-Za-z_]\w*)\s*=\s*\$([0-9a-fA-F]+)',listing)}
    names=['auto_session_reset','auto_resolve_opening','auto_random_byte','auto_limits','auto_pausing','auto_started','auto_later','auto_sampled','auto_last_opening','auto_opening_prng','auto_count','auto_candidate_count','auto_attempts','auto_candidates','auto_limit','mode','history_length','original_board','terminal','neural_failed','original_set','selected_move','move_result']
    s={k:syms[k] for k in names}
    raw=paths['prg'].read_bytes(); load=int.from_bytes(raw[:2],'little'); end=load+len(raw)-2
    assert end<=65536 and load>0x300
    base=[0xA5]*65536; base[load:end]=raw[2:]
    # Native JSR/RTS plus actual BCS consumes return carry; JMP preserves flags.
    # Success/failure PCs are disjoint BRK sentinels, never executed.
    success,failure=0x20b,0x20e
    class Memory(list):
        def __setitem__(self,k,v):
            if self.audit:
                assert isinstance(k,int) and k in self.allowed, ('unexpected write',hex(k))
                self.writes.append((k,v))
            super().__setitem__(k,v)
    mem=Memory(base); mem.audit=False; mem.writes=[]
    cpu=MPU(memory=mem); dis=Disassembler(cpu)
    disassembly=[]; pc=s['auto_session_reset']
    while pc<s['auto_limits']:
        n,txt=dis.instruction_at(pc)
        disassembly.append({'pc':f'{pc:04x}','bytes':bytes(mem[pc:pc+n]).hex(),'instruction':txt}); pc+=n
    assert pc==s['auto_limits']
    assert mem[s['auto_resolve_opening']]==0xd8 # CLD
    assert mem[s['auto_limits']:s['auto_limits']+10]==[0,255,254,255,252,255,252,252,248,252]
    stats={'calls':0,'max_instructions':0,'max_emulated_cycles':0,'total_instructions':0,'unexpected_writes':0}
    reset_allowed={s[k] for k in ['auto_pausing','auto_started','auto_later','auto_sampled','auto_last_opening','auto_opening_prng']}
    resolver_allowed=set(range(s['auto_count'],s['auto_attempts']+1))|set(range(s['auto_candidates'],s['auto_candidates']+9))|{s['auto_opening_prng'],s['auto_sampled'],s['selected_move'],s['move_result']}
    def call(entry,carry=1,decimal=1):
        mem.audit=False
        mem[0x200:0x211]=[0x20,entry&255,entry>>8,0xb0,3,0x4c,success&255,success>>8,0x4c,failure&255,failure>>8,0,0xea,0xea,0,0xea,0xea]
        cpu.pc=0x200;cpu.sp=0xf3;cpu.a=0x69;cpu.x=0x96;cpu.y=0x3c;cpu.p=0x24|(carry&1)|(8 if decimal else 0)
        stack_before=mem[0x100:0x200]; cycles=cpu.processorCycles
        mem.allowed=(reset_allowed if entry==s['auto_session_reset'] else resolver_allowed)|{0x1f3,0x1f2}
        mem.writes=[];mem.audit=True;attempts=0
        for count in range(1,BOUND+1):
            assert cpu.pc in {0x200,0x203,0x205,0x208} or s['auto_session_reset']<=cpu.pc<s['auto_limits'], ('escaped PC',hex(cpu.pc))
            if cpu.pc==s['auto_random_byte']: attempts+=1
            cpu.step()
            if cpu.pc in (success,failure):break
        else:raise AssertionError('instruction watchdog exhausted')
        mem.audit=False
        c=cpu.p&1
        assert cpu.sp==0xf3 and (cpu.pc==failure)==bool(c)
        assert mem[0x1f2:0x1f4]==[2,2] # JSR pushes $0202, RTS resumes $0203
        assert all(mem[0x100+i]==v for i,v in enumerate(stack_before) if i not in (0xf2,0xf3))
        assert mem[s['auto_session_reset']:s['auto_limits']+10]==base[s['auto_session_reset']:s['auto_limits']+10]
        used=cpu.processorCycles-cycles
        stats['calls']+=1;stats['max_instructions']=max(stats['max_instructions'],count);stats['max_emulated_cycles']=max(stats['max_emulated_cycles'],used);stats['total_instructions']+=count
        if entry==s['auto_resolve_opening']:assert not(cpu.p&8)
        return dict(carry=c,attempts=attempts,instructions=count,cycles=used,pc=cpu.pc)
    def setup(previous=4,seed=167,approved=None):
        mem.audit=False
        for k in ['mode','history_length','terminal','neural_failed']:mem[s[k]]=0
        mem[s['original_board']:s['original_board']+9]=[0]*9
        mem[s['original_set']:s['original_set']+9]=[1]*9 if approved is None else approved
        for k in ['auto_later','auto_sampled','auto_last_opening','auto_opening_prng','selected_move','move_result','auto_attempts']:
            mem[s[k]]={'auto_later':1,'auto_sampled':0,'auto_last_opening':previous,'auto_opening_prng':seed,'selected_move':0x6d,'move_result':0x7e,'auto_attempts':0x92}[k]
    resets=[]
    for carry in [0,1]:
        for decimal in [0,1]:
            for addr in reset_allowed:mem[addr]=0x63
            r=call(s['auto_session_reset'],carry,decimal)
            assert [mem[s[k]] for k in ['auto_pausing','auto_started','auto_later','auto_sampled','auto_last_opening','auto_opening_prng']]==[0,0,0,0,255,167]
            assert r['carry']==carry and bool(cpu.p&8)==bool(decimal)
            resets.append(r)
    # Actual reset -> first-game skip -> later-game resolver sequence.
    setup(seed=17);call(s['auto_session_reset']); mem[s['selected_move']]=4;mem[s['move_result']]=5
    r=call(s['auto_resolve_opening']); assert not r['carry'] and r['attempts']==0 and mem[s['selected_move']]==4 and mem[s['auto_opening_prng']]==167
    census=json.loads(paths['census'].read_text());assert len(census)==2295
    assert {(r['previous'],r['prng_before']) for r in census}=={(p,b) for p in range(9) for b in range(1,256)}
    records=[];attempt_hist=collections.Counter()
    for idx,expected in enumerate(census):
        setup(expected['previous'],expected['prng_before']);r=call(s['auto_resolve_opening'],idx%2,1)
        observed=dict(previous=expected['previous'],prng_before=expected['prng_before'],opening=mem[s['selected_move']],prng_after=mem[s['auto_opening_prng']],attempts=r['attempts'])
        assert observed==expected,(observed,expected)
        assert r['carry']==0 and mem[s['move_result']]==observed['opening']+1 and mem[s['auto_sampled']]==1
        assert mem[s['auto_attempts']]==10-r['attempts'] and observed['opening']!=observed['previous']
        assert mem[s['auto_last_opening']]==expected['previous']
        attempt_hist[r['attempts']]+=1;records.append(observed)
    guards=[]
    def guard(name,changes,skip):
        setup()
        for a,v in changes:mem[a]=v
        snapshot=mem[:];r=call(s['auto_resolve_opening'])
        assert r['attempts']==0 and mem[s['auto_opening_prng']]==167 and mem[s['auto_sampled']]==0
        if skip:
            assert r['carry']==0 and all(mem[a]==snapshot[a] for a in resolver_allowed)
        else:
            assert r['carry']==1 and mem[s['selected_move']]==255 and mem[s['move_result']]==0
        guards.append(dict(name=name,skip=skip,**r))
    for key in ['mode','history_length']:
        for v in range(1,256):guard(f'{key}:{v}',[(s[key],v)],True)
    guard('first-game',[(s['auto_later'],0)],True)
    for key in ['terminal','neural_failed']:
        for v in range(1,256):guard(f'{key}:{v}',[(s[key],v)],False)
    for i in range(9):
        for v in [1,2,255]:guard(f'occupied:{i}:{v}',[(s['original_board']+i,v)],False)
        for v in [2,255]:guard(f'malformed-set:{i}:{v}',[(s['original_set']+i,v)],False)
    guard('empty-approved',[(s['original_set']+i,0) for i in range(9)],False)
    singles=[]
    for cell in range(9):
        for previous in [cell,255]:
            setup(previous,167,[int(i==cell) for i in range(9)]);r=call(s['auto_resolve_opening'])
            assert not r['carry'] and r['attempts']==0 and mem[s['selected_move']]==cell and mem[s['move_result']]==cell+1 and mem[s['auto_opening_prng']]==167
            singles.append(dict(cell=cell,previous=previous,**r))
    # Independently compute zero recovery for the actual $B7 substitute.
    setup(seed=0);r=call(s['auto_resolve_opening']);replacement=(0xb7>>1)^0xb8
    assert not r['carry'] and r['attempts']==1 and mem[s['auto_opening_prng']]==replacement
    candidates=[i for i in range(9) if i!=4];assert mem[s['selected_move']]==candidates[(replacement-1)%8]
    zero=dict(prng_before=0,substitute=183,prng_after=mem[s['auto_opening_prng']],opening=mem[s['selected_move']],**r)
    # Continuous CPU state between events; emulate only caller's observed
    # stx auto_last_opening store, not a game/model/terminal/replay execution.
    setup();call(s['auto_session_reset']);mem[s['auto_last_opening']]=4;mem[s['auto_later']]=1
    pairs={};orbit=[]
    while (mem[s['auto_last_opening']],mem[s['auto_opening_prng']]) not in pairs:
        assert len(orbit)<2296
        last,seed=mem[s['auto_last_opening']],mem[s['auto_opening_prng']];pairs[last,seed]=len(orbit)
        r=call(s['auto_resolve_opening']);assert not r['carry']
        move=mem[s['selected_move']]
        orbit.append(dict(previous=last,prng_before=seed,opening=move,prng_after=mem[s['auto_opening_prng']],attempts=r['attempts']))
        mem[s['auto_last_opening']]=move
    transient=pairs[mem[s['auto_last_opening']],mem[s['auto_opening_prng']]]
    cycle=orbit[transient:];counts={str(k):v for k,v in sorted(collections.Counter(r['opening'] for r in cycle).items())}
    expected_orbit=json.loads(paths['orbit'].read_text())['fixed_seed_host_emulation']
    assert orbit==expected_orbit['records'] and transient==expected_orbit['transient_length']==1 and len(cycle)==expected_orbit['cycle_length']==248 and counts==expected_orbit['cycle_counts']
    # All writes in every call were address-audited; fixtures and synthetic
    # trampoline writes occur with audit disabled outside measured calls.
    after={k:sha(p) for k,p in paths.items()};assert before==after
    result=dict(passed=True,scope='Isolated genuine assembled subroutines in py65 flat RAM; NOT full native game replay, ROM/I/O/hardware acceptance, empirical fairness, or wall-time measurement.',input_files={k:dict(path=str(p),sha256=before[k],sha256_after=after[k]) for k,p in paths.items()},harness=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__))),load_address=load,load_address_hex=f'${load:04x}',payload_end_exclusive=end,addresses={k:f'${v:04x}' for k,v in s.items()},native_caller=dict(jsr_pc='$0200',bcs_pc='$0203',success_sentinel='$020b',failure_sentinel='$020e',sentinels_never_executed=True,stack_pointer_before_after='$f3',instruction_bound_per_call=BOUND,carry_consumed_before_any_flag_clobber=True),reset_tests=resets,census=dict(count=len(records),mismatches=0,attempt_histogram=dict(sorted(attempt_hist.items())),records=records),guards=dict(count=len(guards),records=guards),singletons=singles,zero_seed_recovery=zero,fixed_seed_orbit=dict(seed=167,first_deterministic_opening_assumed_from_study015=4,transient_length=transient,cycle_length=len(cycle),cycle_counts=counts,cycle_transition_support=len({(r['previous'],r['opening']) for r in cycle}),including_transient_support=len({(r['previous'],r['opening']) for r in orbit}),records=orbit,caller_last_opening_store='Applied by harness between resolver events; no game execution claimed'),execution=stats,read_only_preservation=True,disassembly=disassembly)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(passed=True,output=str(out),output_sha256=sha(out),census_count=len(records),guard_count=len(guards),attempt_histogram=dict(attempt_hist),transient_length=transient,cycle_length=len(cycle),cycle_counts=counts,execution=stats),sort_keys=True))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=SCRATCH/'study015_machine_sampler_verified.json');args=ap.parse_args();main(args.output)
