"""Numeric validation of the real downloadable game-music transport."""
import array
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_tool():
    path = ROOT / 'scripts/prepare_music_preview.py'
    assert path.exists(), 'repeatable music conversion tool is missing'
    spec = importlib.util.spec_from_file_location('music_preview', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pcm_metrics_detect_silence_and_clipping():
    tool = load_tool()
    stats = tool.pcm_metrics(array.array('h', [0, 100, -100, 32767, -32768]).tobytes())
    assert stats['samples'] == 5
    assert stats['nonzero_samples'] == 4
    assert stats['clipped_samples'] == 2
    assert stats['peak'] == 32768
    assert stats['rms'] > 0
    assert tool.pcm_metrics(bytes(20))['rms'] == 0


def test_download_has_real_vorbis_audio_and_public_provenance():
    import json
    tool = load_tool()
    folder = ROOT / 'assets/audio'
    assert (folder / 'patient-calculations.ogg').exists()
    metadata = json.loads((folder / 'provenance.json').read_text())
    actual = tool.inspect_audio(folder / 'patient-calculations.ogg')
    assert actual == {k: v for k, v in metadata['output'].items() if k != 'path'}
    assert actual['codec'] == 'vorbis' and actual['container'] == 'ogg'
    assert actual['duration_seconds'] == 38.0
    assert actual['sample_rate'] == 48000 and actual['channels'] == 1
    assert actual['pcm_s16le']['nonzero_samples'] > 1_000_000
    assert actual['pcm_s16le']['clipped_samples'] == 0
    assert metadata['capture']['prg_sha256'] == tool.ACCEPTED_PRG_SHA256
    assert metadata['capture']['injected_keys'] == 0
    assert metadata['capture']['injected_events'] == 0
    text = (folder / 'provenance.json').read_text()
    assert '/home/' not in text and '127.0.0.1' not in text


def test_repeat_conversion_matches_published_bytes(tmp_path):
    import json
    import pytest
    source = ROOT / 'build/music-preview-010/sid.wav'
    if not source.exists():
        pytest.skip('private capture not retained in this checkout; use --capture-build')
    tool = load_tool()
    metadata = json.loads((ROOT / 'assets/audio/provenance.json').read_text())
    assert tool.sha256(source) == metadata['source']['sha256']
    result = tool.convert(source, tmp_path / 'repeat.ogg', start=1.0, duration=38.0)
    assert result['output'] == {k: v for k, v in metadata['output'].items() if k != 'path'}
