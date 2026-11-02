"""Explicit square-coordinate transforms; not a learned model layer."""


def _make_transform(rotations, reflected):
    result = []
    for index in range(9):
        row, column = divmod(index, 3)
        if reflected:
            column = 2 - column
        for _ in range(rotations):
            row, column = column, 2 - row
        result.append(row * 3 + column)
    return tuple(result)


# Each permutation maps a source-square index to its destination-square index.
TRANSFORMS = tuple(_make_transform(rotations, reflected)
                   for reflected in (False, True) for rotations in range(4))


def _validate(transform):
    if len(transform) != 9 or sorted(transform) != list(range(9)):
        raise ValueError('expected a permutation of the nine squares')


def transform_board(board, transform):
    _validate(transform)
    if len(board) != 9:
        raise ValueError('expected nine board cells')
    result = [None] * 9
    for source, destination in enumerate(transform):
        result[destination] = board[source]
    return tuple(result)


def inverse(transform):
    _validate(transform)
    result = [0] * 9
    for source, destination in enumerate(transform):
        result[destination] = source
    return tuple(result)


def transform_move(square, transform):
    _validate(transform)
    if not isinstance(square, str) or len(square) != 1 or square not in 'abcdefghi':
        raise ValueError('expected a single square a through i')
    return chr(ord('a') + transform[ord(square) - ord('a')])


def canonicalize(board):
    """Return a canonical board and its original-to-canonical permutation."""
    candidates = [(transform_board(board, transform), index)
                  for index, transform in enumerate(TRANSFORMS)]
    canonical, index = min(candidates)
    return canonical, TRANSFORMS[index]


def restore_moves(canonical_moves, transform):
    """Inverse-map a predicted move set, then apply ORIGINAL-coordinate ties.

    This helper cannot repair an incomplete or incorrect predicted optimal set.
    It does not compute optimality and must not be fed oracle data in inference.
    """
    undo = inverse(transform)
    restored = {transform_move(move, undo) for move in canonical_moves}
    return [move for move in 'ebdfhcgia' if move in restored]
