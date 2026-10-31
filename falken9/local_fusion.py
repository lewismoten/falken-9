"""Weight-derived per-token constant folding, never a board/move policy table.

Q/K/V after first LayerNorm depend only on (side, square, occupancy), not the
other eight squares. Attention, later normalization, routing and experts remain
input-dependent neural computation. This host compiler experiment does not
claim target RAM residency or measured 6502 speed.
"""
import torch
from falken9.canonical_integer import CanonicalIntegerPolicy


def compile_local_qkv(candidate):
    """Use only integer parameters/arithmetic to enumerate 54 local features."""
    reference = CanonicalIntegerPolicy(candidate)
    table = torch.empty((2, 9, 3, 3, candidate['width']), dtype=torch.int64)
    parameters = candidate['tensors']
    for side in range(2):
        for square in range(9):
            for occupancy in range(3):
                x = (parameters['occupancy.weight']['codes'][occupancy]
                     + parameters['position']['codes'][square]
                     + parameters['side.weight']['codes'][side]).reshape(1, -1)
                x = reference.sat(x, 'embedding')
                z = reference.norm(x, 'norm1')
                for index, name in enumerate(('query', 'key', 'value')):
                    table[side, square, occupancy, index] = reference.linear(z, name + '.weight')[0]
    return table


class LocalNormPolicy(CanonicalIntegerPolicy):
    """Fold only first per-token normalization; keep all Q/K/V projections."""
    def __init__(self, candidate):
        super().__init__(candidate)
        reference = CanonicalIntegerPolicy(candidate)
        self.local_norm = torch.empty((2, 9, 3, self.d), dtype=torch.int64)
        for side in range(2):
            for square in range(9):
                for occupancy in range(3):
                    x = (self.t['occupancy.weight']['codes'][occupancy]
                         + self.t['position']['codes'][square]
                         + self.t['side.weight']['codes'][side]).reshape(1, -1)
                    self.local_norm[side, square, occupancy] = reference.norm(reference.sat(x, 'embedding'), 'norm1')[0]
        self._prepared_norm = None

    def norm(self, x, prefix):
        if prefix == 'norm1' and self._prepared_norm is not None:
            return self._prepared_norm
        return super().norm(x, prefix)

    def __call__(self, boards, return_routes=False):
        if boards.dtype != torch.int64 or boards.ndim != 2 or boards.shape[1] != 9 or bool(((boards < 0) | (boards > 2)).any()):
            raise ValueError('boards must be INT64 Bx9 occupancy')
        side = (boards != 0).sum(-1) % 2
        self._prepared_norm = self.local_norm[side[:, None], torch.arange(9)[None, :], boards]
        try:
            return super().__call__(boards, return_routes)
        finally:
            self._prepared_norm = None


class LocalFusionPolicy(CanonicalIntegerPolicy):
    """Exact local fusion of the fixed F9J2 forward; original model unchanged."""
    def __init__(self, candidate, local_qkv=None):
        super().__init__(candidate)
        self.local_qkv = compile_local_qkv(candidate) if local_qkv is None else local_qkv
        if self.local_qkv.dtype != torch.int64 or tuple(self.local_qkv.shape) != (2, 9, 3, 3, self.d):
            raise ValueError('invalid local QKV table shape/dtype')
        self._prepared_qkv = None

    def norm(self, x, prefix):
        if prefix == 'norm1' and self._prepared_qkv is not None:
            # This value is consumed only by the three bypassed projections.
            return x
        return super().norm(x, prefix)

    def linear(self, x, name, bias=None, expert=None):
        index = {'query.weight': 0, 'key.weight': 1, 'value.weight': 2}.get(name)
        if index is not None and self._prepared_qkv is not None:
            return self._prepared_qkv[:, :, index, :]
        return super().linear(x, name, bias, expert)

    def __call__(self, boards, return_routes=False):
        if boards.dtype != torch.int64 or boards.ndim != 2 or boards.shape[1] != 9 or bool(((boards < 0) | (boards > 2)).any()):
            raise ValueError('boards must be INT64 Bx9 occupancy')
        side = (boards != 0).sum(-1) % 2
        self._prepared_qkv = self.local_qkv[side[:, None], torch.arange(9)[None, :], boards]
        try:
            return super().__call__(boards, return_routes)
        finally:
            self._prepared_qkv = None
