"""Consumer-guide reading order and bounded Markdown metadata handling."""
from pathlib import Path

from scripts.build_public_pages import render_document

ROOT = Path(__file__).resolve().parents[1]


def test_game_guide_puts_running_and_controls_before_background():
    text = (ROOT / 'docs/C64_GAME.md').read_text()
    markers = [
        'falken-9-011-title.png',
        'falken-9-011-gameplay.png',
        '## Download and run',
        '## Controls and quitting',
        'falken-9-011-quit-session.png',
        '## How Falken-9 differs from the earlier CP64 implementation',
        '## Revision history and verification boundaries',
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert 'application011-provenance.json' in text
    assert 'falken9-010-' not in text
    assert '**FALKEN-9** badge' in text
    assert 'FALKEN-9 / INFO' not in text
    assert 'terminal result in human/model or two-human mode' in text
    assert 'Emulator-tested only' in text
    assert 'historical spelling inconsistency' in text


def test_renderer_preserves_thematic_rules_and_incomplete_metadata(tmp_path):
    documents = [
        '---\n\nA normal opening thematic rule.\n\n---\n\n# Body\n',
        '---\nlicense: apache-2.0\n# No closing delimiter\n',
        '# Body\n\n---\nlicense: apache-2.0\n---\n',
        '---\nlicense: apache-2.0\n---\n# Body\n\n---\n\nRetained thematic rule.\n',
    ]
    for text in documents:
        (tmp_path / 'README.md').write_text(text)
        html, _, _ = render_document(tmp_path, 'README.md', 'overview.html', {}, set())
        assert '<hr>' in html
        if text != documents[-1]:
            assert ('license: apache-2.0' in html) == ('license: apache-2.0' in text)
        else:
            assert 'license: apache-2.0' not in html
