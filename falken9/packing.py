"""Dense row packing. Lowest-index lane occupies least-significant bits."""
CODEBOOKS = {'binary': (-1, 1), 'ternary': (0, 1, -1)}


def pack(weights, kind: str) -> bytes:
    book = CODEBOOKS[kind]
    bits = 1 if kind == 'binary' else 2
    weights = list(weights)
    result = bytearray((len(weights) * bits + 7) // 8)
    for i, weight in enumerate(weights):
        if weight not in book:
            raise ValueError('weight outside codebook')
        result[i * bits // 8] |= book.index(weight) << (i * bits % 8)
    return bytes(result)


def unpack(data: bytes, count: int, kind: str) -> list[int]:
    book = CODEBOOKS[kind]
    bits = 1 if kind == 'binary' else 2
    if count < 0 or len(data) != (count * bits + 7) // 8:
        raise ValueError('incorrect packed length')
    if count * bits % 8 and data[-1] >> (count * bits % 8):
        raise ValueError('nonzero padding')
    result = []
    for i in range(count):
        code = (data[i * bits // 8] >> (i * bits % 8)) & ((1 << bits) - 1)
        if code >= len(book):
            raise ValueError('reserved code')
        result.append(book[code])
    return result
