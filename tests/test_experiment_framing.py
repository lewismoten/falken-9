"""Keep the common engineering question explicit without inventing new gates."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
QUESTION = ('Can a learned attention-and-expert network execute on a C64, play correctly, '
            'and be small enough to investigate exhaustively?')

def test_common_question_in_overview_card_and_report():
    for name in ('README.md', 'publication/model-card.md', 'report.md'):
        text = (ROOT / name).read_text()
        prose = ' '.join(text.replace('> ', '').split())
        assert QUESTION in prose, name
        assert all(model in prose for model in ('Palace-9', 'Crystal-9', 'Falken-9')), name
        assert 'specialized' in prose and 'speed' in prose, name

def test_report_exhaustiveness_is_scoped_and_figure_inventory_retained():
    text = (ROOT / 'report.md').read_text()
    assert 'declared finite board domains' in text
    assert 'complete interpretation of every internal mechanism' in text
    assert len(re.findall(r'!\[[^\]]*\]\([^\s)]+\.png\)', text)) == 39
