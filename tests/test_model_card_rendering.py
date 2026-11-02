"""Consumer copy and real Markdown rendering, not remote-publication claims."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
import markdown

ROOT=Path(__file__).resolve().parents[1]

class CardHTML(HTMLParser):
    def __init__(self):
        super().__init__();self.hrefs=[];self.headings=[];self.heading=None
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.hrefs.append(dict(attrs).get('href',''))
        if tag in ('h1','h2','h3'):self.heading=''
    def handle_data(self,data):
        if self.heading is not None:self.heading+=data
    def handle_endtag(self,tag):
        if tag in ('h1','h2','h3') and self.heading is not None:
            self.headings.append(self.heading);self.heading=None

def test_model_card_explicit_names_size_and_direct_observation():
    text=(ROOT/'publication/model-card.md').read_text()
    assert 'historical spelling inconsistency' in text
    assert all(name in text for name in ('Falken-9','falcon-9','FALCON-9'))
    assert 'In informal emulator observations, complete AI-vs-AI games lasted' in text
    assert 'Lewis describes' not in text
    assert '5,195 bytes refer only to' in text
    assert 'complete game' in text and '6502 inference runtime' in text and 'working memory' in text
    assert 'assets/screenshots/falken-9-011-gameplay.png' in text
    assert 'application010' not in text and 'falken9-010-' not in text
    assert 'Emulator-tested only' in text
    assert '39 selected indexed figures' in text
    assert 'not the acceptance criterion' in text


def test_publication_copy_has_no_operator_or_upload_prose():
    for name in ('publication/model-card.md', 'docs/C64_GAME.md'):
        text = (ROOT / name).read_text()
        for stale in ('this draft', 'planned public destinations', 'future public slug',
                      'UPLOAD.md', 'COMMIT_MESSAGE.txt', 'distribution/publication/'):
            assert stale not in text
        assert 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1' in text
        assert 'sole cause' not in text

def test_actual_card_markdown_renders_real_headings_bold_and_urls():
    text=(ROOT/'publication/model-card.md').read_text()
    assert re.search(r'\\[\[\]#*]',text) is None
    body=re.sub(r'\A---\n.*?\n---\n','',text,count=1,flags=re.S)
    html=markdown.markdown(body,extensions=['tables','fenced_code'])
    parser=CardHTML();parser.feed(html)
    assert parser.headings[0]=='Falken-9'
    assert 'Downloads' in parser.headings and 'What the model computes' in parser.headings
    assert all('**' not in title and '\\' not in title for title in parser.headings)
    assert '<strong>' in html and '<table>' in html
    assert 'https://github.com/lewismoten/falken-9' in parser.hrefs
    for href in parser.hrefs:
        assert not any(c in href for c in ('\\','[',']',' '))
        url=urlsplit(href)
        if url.netloc=='github.com':
            assert url.scheme=='https' and len([s for s in url.path.split('/') if s])>=2

def test_pages_model_card_preview_hides_hub_yaml(tmp_path):
    from scripts.build_public_pages import render_document
    (tmp_path/'README.md').write_text('---\nlicense: apache-2.0\nlanguage:\n- en\n---\n# Model title\n\n**Readable bold.**\n')
    html,toc,count=render_document(tmp_path,'README.md','overview.html',{'README.md':'overview.html'},{'README.md'})
    assert html.startswith('<h1')
    assert 'license: apache-2.0' not in html
    assert '<strong>Readable bold.</strong>' in html
