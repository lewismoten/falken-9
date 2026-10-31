import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from scripts import benchmark_kernels


class ToolchainTests(unittest.TestCase):
    def test_kernel_assembler_uses_project_local_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / 'build/tools/64tass/usr/bin/64tass'
            local.parent.mkdir(parents=True)
            local.write_text('fixture executable path only')
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(benchmark_kernels, 'ROOT', root), mock.patch.object(benchmark_kernels.shutil, 'which', return_value=None):
                try:
                    selected = benchmark_kernels.assembler()
                except RuntimeError:
                    self.fail('project-local assembler bootstrap is not recognized')
                self.assertEqual(selected, str(local))

    def test_explicit_assembler_selection_has_priority(self):
        with mock.patch.dict(os.environ, {'TASS64': '/explicit/assembler'}):
            self.assertEqual(benchmark_kernels.assembler(), '/explicit/assembler')


if __name__ == '__main__':
    unittest.main()
