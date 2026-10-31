"""Audit evidence integrity, with no claim of integrated game availability."""
from pathlib import Path
import hashlib
import json
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ram_audit_evidence_and_provisional_arena_accounting():
    audit_path = ROOT/'artifacts/kernels/ram-audit.json'
    if not audit_path.is_file():
        pytest.skip('optional read-only CP64 audit snapshot is not present')
    report = json.loads(audit_path.read_text())
    assert report['proven_free_bytes_in_existing_complete_game'] == 0
    for source in report['evidence']:
        evidence = ROOT/source['evidence']
        assert evidence.stat().st_size == source['bytes']
        assert hashlib.sha256(evidence.read_bytes()).hexdigest() == source['sha256']
    maps = report['symbols']
    shell = maps['build/release-018.lbl']
    bundle = maps['build/ai_opening_bundle.lbl']
    assert shell['AI_OPENING_RESULT'] == bundle['model_opening_result']
    assert report['images'][1]['end_exclusive'] == bundle['tensor_group_code_end']
    proposed = report['prototype_ledger']
    for i,left in enumerate(proposed):
        assert left['bytes'] == left['end_exclusive']-left['start']
        for right in proposed[i+1:]:
            assert left['end_exclusive'] <= right['start'] or right['end_exclusive'] <= left['start']
    for arena in report['candidate_arenas']:
        assert arena['classification'] == 'provisional'
        assert arena['bytes'] == arena['end_exclusive']-arena['start']
