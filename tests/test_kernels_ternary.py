from test_kernels_binary import harness
import itertools
import random


def test_ternary_machine_code_decodes_all_codes_and_rejects_reserved():
    bench = harness()
    image = bench.assemble('ternary')
    rng = random.Random(11)
    vectors = []
    for n in [0,1,3,4,8,12,16,24,32]:
        for _ in range(12):
            vectors.append(([rng.randrange(-128,128) for _ in range(n)],
                            [rng.choice([-1,0,1]) for _ in range(n)]))
        for x in [-128,127,0]:
            for w in [-1,0,1]: vectors.append(([x]*n,[w]*n))
    for ws in itertools.product([-1,0,1], repeat=4):
        vectors.append(([-128,127,-1,1],ws))
    for xs,ws in vectors:
        packed = bytearray((len(ws)+3)//4)
        for i,w in enumerate(ws):
            packed[i//4] |= {0:0,1:1,-1:2}[w] << (2*(i%4))
        result = bench.execute(image,xs,packed)
        assert result['value'] == sum(x*w for x,w in zip(xs,ws))
        assert result['carry'] == 0
        assert result['unexpected_writes'] == []
    assert bench.execute(image,[1],b'\x03')['carry'] == 1
