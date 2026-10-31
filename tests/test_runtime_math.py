"""Execute real NMOS 6502 arithmetic, independent Python-int oracle."""
import importlib.util
import math
import random
from pathlib import Path


def runtime():
    assert importlib.util.find_spec('scripts.build_runtime'), 'target build is missing'
    from scripts.build_runtime import build
    from scripts.verify_runtime import Machine
    return Machine(build())


def test_mac40_rounding_overflow_and_preservation():
    m = runtime()
    rng = random.Random(1459)
    cases = [(0, 0, 0), (2147483647, 1, 0), (-8388607, -32768, 0),
             (8388607, 32767, (1 << 39)-1), (-8388607, 32767, -(1 << 39))]
    cases += [(rng.randrange(-200000, 200001), rng.randrange(-32768, 32768), rng.randrange(-1<<34, 1<<34)) for _ in range(80)]
    for a, w, acc in cases:
        m.put('operand', a, 4); m.put('weight', w, 2); m.put('acc', acc, 5)
        result = m.call('mac40')
        valid = abs(a) <= 8388607 and -(1<<39) <= acc+a*w < (1<<39)
        assert result['carry'] == int(not valid), (a,w,acc)
        if valid: assert m.get('acc',5) == acc+a*w
        assert m.get('operand',4) == a
        assert m.get('weight',2) == w
        assert not result['decimal']
    m.put('operand',8388608,4); m.put('weight',1,2)
    assert m.call('mac40')['carry'] == 1
    for a in [-(1<<39), -(1<<34)-3,-65537,-5,-3,-1,0,1,3,5,(1<<39)-1]:
        for shift in [0,1,3,11,15,31,39]:
            m.put('acc',a,5); m.put('shift',shift,1)
            assert not m.call('scale40')['carry']
            expected = (abs(a)+(0 if shift==0 else 1<<(shift-1))) >> shift
            assert m.get('acc',5) == (-expected if a<0 else expected)


def test_variable_signed_division_and_unsigned40_floor_sqrt():
    m = runtime()
    assert 'divide40' in m.labels, 'variable division is missing'
    rng = random.Random(389)
    for n,d in [(0,1),(-1,2),(1,2),(-(1<<39),1),((1<<39)-1,4294967295)] + [(rng.randrange(-1<<38,1<<38),rng.randrange(1,1<<32)) for _ in range(80)]:
        m.put('acc',n,5); m.put('denominator',d,5)
        result=m.call('divide40')
        assert result['carry']==0
        assert m.get('acc',5)==(1 if n>=0 else -1)*((abs(n)+d//2)//d), (n,d)
        assert m.get('denominator',5,False)==d
    m.put('denominator',0,5)
    assert m.call('divide40')['carry']==1
    for n in [0,1,2,3,4,8,9,10,(1<<40)-1]+[rng.randrange(1<<40) for _ in range(80)]:
        m.put('acc',n,5)
        assert m.call('sqrt40')['carry']==0
        assert m.get('root',5,False)==math.isqrt(n), n


def test_floor_division_and_exact_exp_interpolation():
    m=runtime()
    assert 'floor40' in m.labels, 'floor division missing'
    from falken9.canonical_integer_export import load
    from scripts.build_runtime import MODEL
    table=load(MODEL)['tables']['exp']
    rng=random.Random(111)
    for n,d in [(0,3),(5,2),(1073741824,294912)]+[(rng.randrange(1<<38),rng.randrange(1,1<<32)) for _ in range(30)]:
        m.put('acc',n,5);m.put('denominator',d,5)
        assert not m.call('floor40')['carry']
        assert m.get('acc',5)==n//d
    for gap in [0,1,31,32,63,64,65,32767,32768,32769,2147483647]+[rng.randrange(32768) for _ in range(150)]:
        m.put('operand',gap,4)
        assert not m.call('exp_interpolate')['carry']
        i,r=divmod(min(gap,32768),64)
        expected=(table[i]*(64-r)+table[min(i+1,512)]*r+32)//64
        assert m.get('acc',5)==expected,gap
