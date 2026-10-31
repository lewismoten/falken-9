from test_kernels_binary import harness
import random


def test_int8_machine_code_full_signed_domain_and_int32_accumulation():
    bench = harness()
    image = bench.assemble('int8')
    # Every signed activation/weight combination, batched into 32-lane dots.
    # Distinct signed products cannot cancel within a same-sign weight row.
    for w in range(-128,128):
        for base in range(-128,128,32):
            xs = list(range(base,base+32))
            ws = [w]*32
            result = bench.execute(image,xs,bytes(v & 255 for v in ws),32)
            assert result['value'] == sum(x*w for x,w in zip(xs,ws))
            assert result['carry'] == 0
            assert result['unexpected_writes'] == []
    rng = random.Random(27)
    for n in [0,1,8,12,16,24,32]:
        for _ in range(8):
            xs = [rng.randrange(-128,128) for _ in range(n)]
            ws = [rng.randrange(-128,128) for _ in range(n)]
            assert bench.execute(image,xs,bytes(w&255 for w in ws),32)['value'] == sum(x*w for x,w in zip(xs,ws))
    assert bench.execute(image,[-128]*32,b'\x80'*32,32)['value'] == 524288
