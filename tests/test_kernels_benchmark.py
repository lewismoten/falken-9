from test_kernels_binary import harness


def test_benchmark_reports_actual_cycles_with_defined_scope():
    bench = harness()
    report, vectors = bench.run_benchmarks()
    assert report['scope'] == 'isolated dot products, not full inference'
    assert set(report['kernels']) == {'binary','ternary','int8'}
    assert len(vectors) == 150
    for kind, info in report['kernels'].items():
        assert len(info['sha256']) == 64
        assert 0 < info['code_bytes'] <= 256
        assert [row['dimension'] for row in info['dimensions']] == [8,12,16,24,32]
        for row in info['dimensions']:
            assert row['vectors'] == 10
            assert 0 < row['min_cycles'] <= row['mean_cycles'] <= row['worst_cycles']
    for row in vectors:
        assert row['actual'] == row['oracle']
        assert row['unexpected_writes'] == []
