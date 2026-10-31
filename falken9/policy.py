"""Input and output protocol; no game policy is stored or computed here."""

SQUARES = 'abcdefghi'
TIE_ORDER = 'ebdfhcgia'
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
         (2, 5, 8), (0, 4, 8), (2, 4, 6))


def _terminal(board):
    return all(board) or any(board[a] and board[a] == board[b] == board[c]
                             for a, b, c in LINES)


def board_from_history(history):
    """Validate a nonterminal chronological history; X=1, O=2, empty=0.

    Reject terminal histories as well as attempts to continue them. This is a
    protocol validator, not a next-move strategy or neural fallback.
    """
    if not isinstance(history, str) or len(history) > 8:
        raise ValueError('expected a nonterminal history of at most eight moves')
    board = [0] * 9
    for turn, square in enumerate(history):
        if square not in SQUARES or _terminal(board):
            raise ValueError('invalid square or continuation after terminal play')
        index = SQUARES.index(square)
        if board[index]:
            raise ValueError('repeated square')
        board[index] = 1 + turn % 2
    if _terminal(board):
        raise ValueError('terminal board has no next move')
    return tuple(board)


def select_move(scores, history):
    """Choose greatest legal score, resolving equality in published tie order."""
    from math import isfinite
    board = board_from_history(history)
    if len(scores) != 9 or not all(isfinite(float(score)) for score in scores):
        raise ValueError('expected nine finite scores in square order a through i')
    legal = (SQUARES.index(square) for square in TIE_ORDER
             if not board[SQUARES.index(square)])
    winner = max(legal, key=lambda index: scores[index])
    return SQUARES[winner]
