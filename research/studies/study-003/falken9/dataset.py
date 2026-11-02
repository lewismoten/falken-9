"""Pinned dataset tooling and an independent audit-only minimax oracle.

Never import the minimax oracle in deployed neural inference.
"""
from functools import lru_cache

DATASET_REPOSITORY = 'lewismoten/tic-tac-toe'
DATASET_REVISION = '6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7'
MANIFEST_SHA256 = '0258d03ac9a2fd5bbf590736f9758d982d5f179e7415a4ca771418b22b1f2777'
TIE_ORDER = 'ebdfhcgia'
_ORACLE_LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
                 (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))


def _winner(board):
    for line in _ORACLE_LINES:
        values = {board[index] for index in line}
        if len(values) == 1 and 0 not in values:
            return values.pop()
    return 0


@lru_cache(maxsize=None)
def _negamax(board, player):
    winner = _winner(board)
    if winner:
        return 1 if winner == player else -1
    if 0 not in board:
        return 0
    return max(-_negamax(board[:i] + (player,) + board[i + 1:], 3 - player)
               for i, value in enumerate(board) if value == 0)


@lru_cache(maxsize=None)
def _oracle_cached(board):
    if len(board) != 9 or any(value not in (0, 1, 2) for value in board):
        raise ValueError('expected nine board states')
    nx, no = board.count(1), board.count(2)
    if nx not in (no, no + 1) or _winner(board) or 0 not in board:
        raise ValueError('expected a nonterminal alternating-play board')
    player = 1 if nx == no else 2
    options = []
    for square in TIE_ORDER:
        i = ord(square) - ord('a')
        if not board[i]:
            value = -_negamax(board[:i] + (player,) + board[i + 1:], 3 - player)
            options.append((square, value))
    best = max(value for _, value in options)
    return tuple(square for square, value in options if value == best)


def oracle_moves(board):
    """Audit-only all-optimal target in published tie order; not an inference path."""
    return list(_oracle_cached(tuple(board)))


def verify_jsonl(path, record):
    """Stream and bind a JSONL artifact to its declared digest and row count."""
    import hashlib
    import json
    digest = hashlib.sha256()
    rows = 0
    with path.open('rb') as source:
        for line in source:
            digest.update(line)
            json.loads(line)
            rows += 1
    result = {'sha256': digest.hexdigest(), 'rows': rows, 'bytes': path.stat().st_size}
    if result['sha256'] != record['sha256'] or rows != record['rows']:
        raise ValueError(f'dataset digest/count mismatch: {path.name}')
    return result


def audit_history_rows(rows):
    """Exhaustively validate chronology, boards, all targets and redundancy."""
    from collections import Counter
    from .policy import board_from_history
    histories = set()
    labels_by_board = {}
    lengths = Counter()
    for row in rows:
        history = row['history']
        if history in histories:
            raise ValueError(f'duplicate history: {history!r}')
        histories.add(history)
        board = board_from_history(history)
        cells = ''.join('.XO'[value] for value in board)
        text = '/'.join(cells[i:i + 3] for i in (0, 3, 6))
        if row['board'] != text or row['next_player'] != ('O' if len(history) % 2 else 'X'):
            raise ValueError(f'board/player mismatch: {history!r}')
        if 'board_text' in row:
            expected = '\n'.join(' '.join(cells[i:i + 3]) for i in (0, 3, 6))
            if row['board_text'] != expected:
                raise ValueError(f'board_text mismatch: {history!r}')
        optimal = oracle_moves(board)
        if row['optimal_move'] != optimal[0] or row['optimal_moves'] != optimal:
            raise ValueError(f'independent minimax target mismatch: {history!r}')
        labels = (row['optimal_move'], tuple(row['optimal_moves']))
        if board in labels_by_board and labels_by_board[board] != labels:
            raise ValueError(f'chronology-dependent board labels: {history!r}')
        labels_by_board[board] = labels
        lengths[len(history)] += 1
    return {
        'histories': len(histories),
        'unique_nonterminal_boards': len(labels_by_board),
        'history_length_counts': dict(sorted(lengths.items())),
        'independent_minimax_mismatches': 0,
        'board_label_conflicts': 0,
        'tie_order': TIE_ORDER,
        'board_only_supervision_is_consistent': True,
        'scope': 'dataset semantics only; no trained neural model accepted',
    }


def prepare_dataset(root, download=True):
    """Fetch missing files at the fixed revision, verifying rather than replacing."""
    import hashlib
    import json
    import shutil
    import urllib.request
    root.mkdir(parents=True, exist_ok=True)

    def obtain(remote, local):
        path = root / local
        if not path.exists():
            if not download:
                raise FileNotFoundError(path)
            url = f'https://huggingface.co/datasets/{DATASET_REPOSITORY}/resolve/{DATASET_REVISION}/{remote}'
            partial = path.with_suffix(path.suffix + '.partial')
            with urllib.request.urlopen(url, timeout=90) as response, partial.open('wb') as target:
                shutil.copyfileobj(response, target)
            partial.replace(path)
        return path

    manifest_path = obtain('data/manifest.json', 'manifest.json')
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise ValueError('dataset does not match pinned manifest')
    manifest = json.loads(manifest_path.read_text())
    verified = {}
    for name, record in manifest['files'].items():
        if '/' in name or '\\' in name or name.startswith('.'):
            raise ValueError('unsafe dataset filename')
        verified[name] = verify_jsonl(obtain('data/' + name, name), record)
    ancillary = {
        'LICENSE': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
        'README.md': '58fd3c8afe0a779df1bbac50ee32b833f495011a4766377caed5234aa84f5159',
        'generate_dataset.py': '4646f008f6bc181e361506b022632ee00b2909a743f34f21d2a1a49faa3af028',
    }
    for name, digest in ancillary.items():
        if hashlib.sha256(obtain(name, name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'upstream source/license mismatch: {name}')
    return {'repository': DATASET_REPOSITORY, 'revision': DATASET_REVISION,
            'manifest_sha256': MANIFEST_SHA256, 'verified_files': verified,
            'ancillary_sha256': ancillary, 'license': 'Apache-2.0'}
