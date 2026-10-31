from test_kernels_binary import harness


def test_kernel_return_status_stack_and_scratch_contract():
    bench = harness()
    for kind in ['binary','ternary','int8']:
        image = bench.assemble(kind)
        packed = {'binary':b'\x01','ternary':b'\x01','int8':b'\x01'}[kind]
        result = bench.execute(image,[-128],packed,32 if kind == 'int8' else 16)
        assert result['decimal'] == 0
        assert result['stack_pointer'] == 0xff
        assert result['value'] == -128
        assert result['unexpected_writes'] == []
