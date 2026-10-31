"""Falken-9 scalar contract: exact integers, ties away from zero."""


def accumulator_bound(dimension: int, activation_bits: int, weight_magnitude: int) -> int:
    """Symmetric absolute bound, including the asymmetric signed minimum."""
    if dimension < 0 or activation_bits < 2 or weight_magnitude < 0:
        raise ValueError('invalid bound inputs')
    return dimension * (1 << (activation_bits - 1)) * weight_magnitude


def encode_signed(value: int, bits: int) -> bytes:
    if bits not in (8, 16, 32):
        raise ValueError('unsupported width')
    return value.to_bytes(bits // 8, 'little', signed=True)


def dot(activations, weights, activation_bits: int = 8, accumulator_bits: int = 16) -> int:
    activations, weights = list(activations), list(weights)
    if len(activations) != len(weights):
        raise ValueError('dimension mismatch')
    lo, hi = -(1 << (activation_bits - 1)), (1 << (activation_bits - 1)) - 1
    if any(x < lo or x > hi for x in activations):
        raise ValueError('activation outside signed range')
    result = sum(x * w for x, w in zip(activations, weights))
    encode_signed(result, accumulator_bits)  # No silent wrap or saturation.
    return result


def round_shift(value: int, shift: int) -> int:
    """Divide by 2**shift, round nearest; exact half ties away from zero."""
    if shift < 0:
        raise ValueError('shift must be nonnegative')
    if shift == 0:
        return value
    magnitude = (abs(value) + (1 << (shift - 1))) >> shift
    return -magnitude if value < 0 else magnitude


def requantize(value: int, shift: int, bits: int = 8) -> int:
    """Round first, then clamp to a signed two's-complement destination."""
    if bits < 2:
        raise ValueError('bits must be at least two')
    return max(-(1 << (bits - 1)), min((1 << (bits - 1)) - 1,
                                    round_shift(value, shift)))
