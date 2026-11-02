"""Build a curated, subpath-safe static site from a pinned consumer package.

No training, assembly, screenshots or model execution happen here. The public
package is the only source for model/game/research files. Audio is a separate
GitHub artifact. Python-Markdown is the real Markdown renderer.
"""
from pathlib import Path, PurePosixPath
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote, quote
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import markdown

ROOT = Path(__file__).resolve().parents[1]
GITHUB = 'https://github.com/lewismoten/falken-9/blob/main/'
FROZEN = {
    'model.f9j': dict(bytes=5195, sha256='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'),
    'c64/falken-9-c64.prg': dict(bytes=50546, sha256='c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a'),
    'c64/falken-9-c64.d64': dict(bytes=174848, sha256='2570b642780ea6dd2e64c1b915e4bf3143fd8d86e1f9e2224f483f53d9bdb21d'),
}
REQUIRED = {'README.md', 'report.md', 'c64/README.md', 'LICENSE', 'NOTICE', *FROZEN}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Invalid package path')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or str(path) != name or ':' in name:
        raise ValueError(f'Unsafe package path: {name}')
    return name


def manifest_records(manifest):
    if not isinstance(manifest, dict) or manifest.get('schema') != 'falken9-consumer-release-v1':
        raise ValueError('Expected falken9-consumer-release-v1 manifest')
    files = manifest.get('files')
    if isinstance(files, dict):
        files = [dict(record, path=name) for name, record in files.items()]
    if not isinstance(files, list) or not files:
        raise ValueError('Manifest files must be nonempty records')
    records = {}
    for record in files:
        if not isinstance(record, dict):
            raise ValueError('Invalid file record')
        name = safe_name(record.get('path'))
        size = record.get('bytes', record.get('size_bytes', record.get('size')))
        digest = record.get('sha256')
        if name in records or type(size) is not int or size < 0 or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError(f'Invalid/duplicate manifest record: {name}')
        records[name] = dict(path=name, bytes=size, sha256=digest)
    return records


APPLICATION_DESCRIPTOR = ROOT / 'publication/application-release.json'
APPLICATION_RELEASE_ID = 'falken-9-model-v1.0.0-app011'
SCREENSHOT_KINDS = ('title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session')


def screenshot_records(shots):
    """Screenshot provenance needs hashes; byte counts may live in files only."""
    if isinstance(shots, dict):
        shots = list(shots.values())
    if not isinstance(shots, list) or not all(isinstance(shot, dict) for shot in shots):
        raise ValueError('Expected screenshot provenance records')
    records = manifest_records({'schema': 'falken9-consumer-release-v1',
                                'files': [dict(shot, bytes=shot.get('bytes', 0)) for shot in shots]})
    for shot in shots:
        if 'bytes' not in shot:
            records[shot['path']].pop('bytes')
    return records


def application_release():
    """Load only the independently trusted checkout descriptor, never HF input."""
    path = APPLICATION_DESCRIPTOR
    if path.is_symlink():
        raise ValueError('Symlink application descriptor')
    descriptor = json.loads(path.read_text())
    if (descriptor.get('schema') != 'falken9-publication-application-v1' or
            descriptor.get('revision') != '011' or descriptor.get('release_id') != APPLICATION_RELEASE_ID):
        raise ValueError('Invalid trusted application descriptor')
    artifacts = descriptor.get('artifacts', descriptor)
    pins = {}
    for kind, destination in [('model', 'model.f9j'), ('prg', 'c64/falken-9-c64.prg'), ('d64', 'c64/falken-9-c64.d64')]:
        record = artifacts[kind]
        # Source paths can differ from the consumer destination; never copy them.
        safe_name(record['path'])
        checked = manifest_records({'schema': 'falken9-consumer-release-v1', 'files': [record]})
        pins[destination] = next(iter(checked.values()))
    if any(pins['model.f9j'][key] != value for key, value in FROZEN['model.f9j'].items()):
        raise ValueError('Application descriptor changes the frozen model')
    shots = descriptor['screenshots']
    shots = list(shots.values()) if isinstance(shots, dict) else shots
    records = screenshot_records(shots)
    expected = {f'assets/screenshots/falken-9-011-{kind}.png' for kind in SCREENSHOT_KINDS}
    if records.keys() != expected:
        raise ValueError('Application descriptor requires all five 011 screenshots')
    for shot in shots:
        if shot.get('prg_sha256') != pins['c64/falken-9-c64.prg']['sha256'] or not shot.get('method') or not shot.get('source_artifact'):
            raise ValueError('Screenshot lacks executable-bound provenance')
    for key in ('screenshot_provenance', 'validation'):
        record = descriptor[key]
        safe_name(record['path'])
        if not re.fullmatch('[0-9a-f]{64}', record.get('sha256', '')):
            raise ValueError('Invalid application evidence digest')
    pins.update(records)
    return descriptor, pins


def release_pins(manifest):
    release_id = manifest.get('release_id')
    if release_id == APPLICATION_RELEASE_ID:
        descriptor, pins = application_release()
        declared = screenshot_records(manifest.get('screenshots'))
        trusted = screenshot_records(descriptor['screenshots'])
        if declared.keys() != trusted.keys() or any(
                declared[name]['sha256'] != trusted[name]['sha256'] for name in trusted):
            raise ValueError('Package screenshot metadata differs from trusted application')
        return pins
    if release_id != 'falken-9-model-v1.0.0-app010':
        raise ValueError('Unsupported public application release')
    return FROZEN


def validate_package(package):
    package = Path(package).resolve()
    try:
        manifest_path = package / 'manifest.json'
        if manifest_path.is_symlink():
            raise ValueError('Symlink manifest')
        manifest = json.loads(manifest_path.read_text())
        records = manifest_records(manifest)
        if not REQUIRED <= records.keys():
            raise ValueError(f'Missing required files: {sorted(REQUIRED - records.keys())}')
        for name, record in records.items():
            path = package / name
            if path.is_symlink() or not path.resolve().is_relative_to(package) or not path.is_file():
                raise ValueError(f'Missing or unsafe file: {name}')
            data = path.read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise ValueError(f'Package size/SHA-256 mismatch: {name}')
        for name, pin in release_pins(manifest).items():
            if name not in records or any(records[name][key] != pin[key] for key in ('bytes', 'sha256') if key in pin):
                raise ValueError(f'Frozen release mismatch: {name}')
        sums = {}
        sums_path = package / 'SHA256SUMS'
        if sums_path.is_symlink():
            raise ValueError('Symlink checksum file')
        for line in sums_path.read_text().splitlines():
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
            if not match:
                raise ValueError('Invalid SHA256SUMS line')
            digest, name = match.groups()
            safe_name(name)
            if name in sums:
                raise ValueError('Duplicate checksum path')
            sums[name] = digest
        expected = {name: record['sha256'] for name, record in records.items() if name != 'SHA256SUMS'}
        expected['manifest.json'] = sha(manifest_path.read_bytes())
        if sums != expected:
            raise ValueError('SHA256SUMS does not match manifest and manifest digest')
        return records
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError(f'Invalid public package: {error}') from error


def curated(name):
    path = PurePosixPath(name)
    if any('candidate' in part.lower() for part in path.parts):
        return False
    return (name in REQUIRED or name in {'assets/interpretability/presentation-inventory.json', 'provenance/application-screenshot-provenance.json', 'provenance/application-validation.json', 'model.json', 'assets/interpretability/model-inspection/provenance.json', 'assets/interpretability/publication-dark/presentation.json', 'assets/interpretability/publication-indexed/presentation.json', 'assets/screenshots/application010-additional-provenance.json', 'assets/screenshots/application011-provenance.json'} or
            (name.startswith('assets/screenshots/') and path.suffix.lower() == '.png' and ('010' in path.name or path.name in {f'falken-9-011-{kind}.png' for kind in SCREENSHOT_KINDS})) or
            (name.startswith(('assets/interpretability/', 'docs/research/')) and path.suffix.lower() in {'.png', '.svg'}) or
            (name.startswith('docs/research/') and path.suffix.lower() == '.md'))


class RewriteHTML(HTMLParser):
    def __init__(self, rewrite):
        super().__init__(convert_charrefs=False)
        self.rewrite, self.parts = rewrite, []
        self.images = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'iframe', 'object', 'embed', 'base'}:
            raise ValueError(f'Unsafe Markdown HTML: {tag}')
        values = []
        for key, value in attrs:
            table_alignment = key == 'style' and tag in {'td', 'th'} and value in {'text-align: left;', 'text-align: right;', 'text-align: center;'}
            if key.startswith('on') or key == 'srcset' or (key == 'style' and not table_alignment):
                raise ValueError(f'Unsafe Markdown attribute: {key}')
            if key in {'href', 'src'} and value:
                value = self.rewrite(value, tag == 'img')
            values.append(' ' + key + ('' if value is None else '="' + escape(value, quote=True) + '"'))
        if tag == 'img':
            self.images += 1
            values.append(' loading="lazy" decoding="async"')
        self.parts.append('<' + tag + ''.join(values) + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')


def relative(target, source):
    return Path(os.path.relpath(target, PurePosixPath(source).parent)).as_posix()


def render_document(package, source, destination, destinations, copied):
    renderer = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'], extension_configs={'toc': {'permalink': True}})
    text = (package / source).read_text()
    # Hub model-card metadata is not prose. Leave ordinary thematic rules and
    # incomplete/non-leading blocks untouched; only remove a complete header
    # carrying recognizable model-card fields.
    frontmatter = re.match(r'\A---[ \t]*\n(.*?)^---[ \t]*(?:\n|\Z)', text, re.S | re.M)
    if frontmatter and re.search(r'^(?:license|language|tags):', frontmatter.group(1), re.M):
        text = text[frontmatter.end():]
    rendered = renderer.convert(text)

    def rewrite(url, image=False):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme not in {'https', 'http', 'mailto'} or image:
                raise ValueError(f'Unsafe/external resource URL: {url}')
            return url
        if not parsed.path:
            return url
        if parsed.path.startswith('/') or '\\' in parsed.path:
            raise ValueError(f'Root-absolute or unsafe URL: {url}')
        target = os.path.normpath(str(PurePosixPath(source).parent / unquote(parsed.path))).replace(os.sep, '/')
        safe_name(target)
        if image and (target not in copied or not (package / target).is_file()):
            raise ValueError(f'Missing local image: {source}: {target}')
        if target in FROZEN:
            path = relative('downloads/' + PurePosixPath(target).name, destination)
        elif target in destinations:
            path = relative(destinations[target], destination)
        elif target in copied or target in {'manifest.json', 'SHA256SUMS'}:
            path = relative(target, destination)
        elif target == 'docs/C64_GAME.md':
            path = relative('game.html', destination)
        else:
            return GITHUB + quote(target, safe='/') + ('#' + parsed.fragment if parsed.fragment else '')
        return quote(path, safe='/') + ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')

    parser = RewriteHTML(rewrite)
    parser.feed(rendered)
    return ''.join(parser.parts), getattr(renderer, 'toc'), parser.images


def shell(title, content, page='index.html', toc='', script=False):
    prefix = relative('index.html', page).removesuffix('index.html')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Falken-9: a resident neural tic-tac-toe model for the Commodore 64. Play, inspect, and read the research.">
<title>{escape(title)} — Falken-9</title><link rel="stylesheet" href="{prefix}publication.css"></head>
<body><a class="skip" href="#content">Skip to content</a>
<header class="masthead"><a class="wordmark" href="{prefix}index.html">FALKEN–9 <span>C64 / NEURAL GAME</span></a>
<nav aria-label="Primary"><a href="{prefix}index.html#play">Play & download</a><a href="{prefix}report.html">Research</a><a href="{prefix}game.html">Game guide</a><a href="{prefix}index.html#music">Listen</a></nav></header>
<div class="{'reading-layout' if toc else 'site-layout'}">{'<aside class="toc" aria-label="On this page"><details open><summary>On this page</summary>' + toc + '</details></aside>' if toc else ''}
<main id="content" class="{'prose' if toc else 'landing'}">{content}</main></div>
<footer><p>Frozen model. Actual C64 gameplay. Research with explicit limits.</p><a href="{prefix}LICENSE">License</a> · <a href="{prefix}NOTICE">Notices</a> · <a href="{GITHUB}">Source on GitHub</a></footer>
{'<script type="module" src="' + prefix + 'index.mjs"></script>' if script else ''}</body></html>'''


def audit_site(output):
    output = Path(output)
    ids = {}
    documents = {}
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls, self.ids = [], set()
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if attrs.get('id'):
                self.ids.add(attrs['id'])
            for key in ('src', 'href'):
                if attrs.get(key):
                    self.urls.append((attrs[key], tag))
    for file in output.rglob('*.html'):
        parser = Links()
        parser.feed(file.read_text())
        documents[file.resolve()] = parser.urls
        ids[file.resolve()] = parser.ids
    for file, urls in documents.items():
        for url, tag in urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme not in {'https', 'http', 'mailto'} or tag in {'img', 'script', 'link', 'source'}:
                    raise ValueError(f'Unsafe external resource: {url}')
                continue
            if parsed.path.startswith('/'):
                raise ValueError(f'Project-subpath unsafe URL: {url}')
            target = (file.parent / unquote(parsed.path)).resolve() if parsed.path else file
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise ValueError(f'Broken/escaping local URL: {file}: {url}')
            if parsed.fragment and target in ids and unquote(parsed.fragment) not in ids[target]:
                raise ValueError(f'Broken local anchor: {file}: {url}')


def build_pages(package, output, music, music_provenance):
    package, output, music, music_provenance = map(lambda p: Path(p).resolve(), (package, output, music, music_provenance))
    for source in (package, ROOT / 'pages', music, music_provenance):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('Output must be disjoint from all inputs')
    if output.is_relative_to(ROOT / 'distribution'):
        raise ValueError('Pages output must not enter the public package')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output must be fresh or empty')
    records = validate_package(package)
    package_manifest = json.loads((package / 'manifest.json').read_text())
    expected_figures = package_manifest['report']['inline_figures']
    if type(expected_figures) is not int or expected_figures < 37:
        raise ValueError('Missing or incomplete report figure declaration')
    data = music.read_bytes()
    provenance = json.loads(music_provenance.read_text())
    if not data.startswith(b'OggS') or not isinstance(provenance, dict):
        raise ValueError('Expected Ogg audio and provenance object')
    audio_output = provenance.get('output', provenance)
    if not isinstance(audio_output, dict) or audio_output.get('sha256') != sha(data) or audio_output.get('bytes') != len(data):
        raise ValueError('Music provenance digest/size mismatch')
    copied = {name for name in records if curated(name)}
    current = package_manifest['release_id'] == APPLICATION_RELEASE_ID
    revision = '011' if current else '010'
    prefix = 'falken-9-011-' if current else 'falken9-010-'
    order = {prefix + kind + '.png': index for index, kind in enumerate(SCREENSHOT_KINDS)}
    if current and expected_figures != 39:
        raise ValueError('Application 011 requires all 39 report figures')
    selected_screenshots = screenshot_records(package_manifest['screenshots']).keys() if current else copied
    screenshots = sorted((name for name in selected_screenshots if name.startswith('assets/screenshots/') and name.endswith('.png')), key=lambda name:(order.get(Path(name).name,99),name))
    gameplay = 'assets/screenshots/' + prefix + 'gameplay.png'
    if gameplay not in screenshots:
        raise ValueError(f'Actual application {revision} gameplay capture required')
    hero = 'assets/screenshots/' + prefix + 'title.png'
    if hero not in screenshots:
        hero = gameplay
    for name in screenshots:
        if not (package / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError(f'Invalid screenshot PNG: {name}')
    destinations = {name: str(PurePosixPath(name).with_suffix('.html')) for name in copied if name.endswith('.md')}
    destinations.update({'README.md': 'overview.html', 'c64/README.md': 'game.html', 'report.md': 'report.html'})
    # Validate and render before creating output. Never modify the package.
    documents = {}
    for name, destination in destinations.items():
        body, toc, images = render_document(package, name, destination, destinations, copied)
        if name == 'report.md' and images != expected_figures:
            raise ValueError(f'Expected all {expected_figures} illustrated report figures; found {images}')
        if current and name == 'c64/README.md' and any(
                f'src="{shot}"' not in body for shot in screenshots):
            raise ValueError('Application 011 game guide must display all five selected screenshots')
        page_title = {'README.md': 'Project overview', 'c64/README.md': 'C64 game guide', 'report.md': 'Model research report'}.get(name, Path(name).stem.replace('_', ' '))
        documents[destination] = shell(page_title, body, destination, toc)
    manifest: dict = dict(schema='falken9-public-pages-v1', release_id=package_manifest['release_id'], public_publication=False)
    downloads = []
    for kind, name in [('model', 'model.f9j'), ('prg', 'c64/falken-9-c64.prg'), ('d64', 'c64/falken-9-c64.d64')]:
        record = dict(records[name], path='downloads/' + Path(name).name)
        manifest[kind] = record
        downloads.append(f'<tr><th scope="row"><a id="{kind}" href="{record["path"]}" download>{escape(Path(name).name)}</a></th><td>{record["bytes"]:,} bytes</td><td><code>{record["sha256"]}</code></td></tr>')
    gallery = ''.join(f'<figure><a href="{name}"><img src="{name}" alt="Actual C64 capture: {escape(Path(name).stem.replace(prefix, "").replace("-", " "))}" loading="lazy" width="768" height="544"></a><figcaption>{escape(Path(name).stem.replace(prefix, "").replace("-", " "))}</figcaption></figure>' for name in screenshots)
    music_record = dict(path='assets/audio/patient-calculations.ogg', bytes=len(data), sha256=sha(data), provenance='assets/audio/provenance.json')
    music_record['application_scope'] = 'Authentic accepted application010 recording; not a new application011 recording.'
    manifest['music'] = music_record
    title = escape(str(provenance.get('title', 'Patient Calculations')))
    audio_credit = escape(str(provenance.get('credit', 'Original project composition.')))
    audio_boundary = escape(str(provenance.get('recording_boundary', 'See audio provenance for the recording boundary.')))
    audio_details = ' · '.join(escape(str(audio_output[key])) + suffix for key, suffix in [('duration_seconds', ' seconds'), ('sample_rate', ' Hz'), ('channels', ' channel(s)')] if key in audio_output)
    home = f'''<section class="intro"><div><p class="eyebrow">A SMALL MODEL. A REAL MACHINE.</p><h1>Crystal Palace 9.<br>Powered by Falken-9.</h1>
<p class="dek">Crystal Palace 9 keeps its original artwork and adds sound, animated activity and a resident, 5,195-byte Falken-9 model. Every AI move runs the network; the frozen weights do not learn as you play.</p>
<p><a class="text-action" href="#play">Play or inspect the release ↓</a></p><p class="quiet">Not a lookup table. Not the original Crystal-9 weights compressed again.</p></div>
<figure class="hero-screen"><a href="{hero}"><img src="{hero}" width="768" height="544" alt="Actual Crystal Palace 9 screen, captured in stock-ROM VICE"></a><figcaption>Crystal Palace 9 · Falken-9 model · actual stock-ROM VICE capture</figcaption></figure></section>
<section id="play" class="split"><div><p class="eyebrow">01 / RUN THE GAME</p><h2>Your next move.</h2><p>Launch the PRG in TY64, or send the disk to Lewis Moten’s storage-d64 inspector. Both open another tab; no emulator is embedded here. Self-play is a short curiosity to watch, with sound and visible activity during thinking. General timing impressions are described in the game guide.</p><div class="actions"><button id="run" disabled>Play in TY64 ↗</button><button id="inspect" disabled>Inspect the D64 ↗</button></div><p id="status" role="status" aria-live="polite">Loading the verified release inventory…</p><button id="retry" hidden>Reload launcher</button></div><div><h3>Before you start</h3><p>Allow popups. Transmitted bytes are checked against the same-origin inventory’s length and SHA-256. The disk inspector also requires a source-, origin- and request-matched readiness handshake.</p><p>TY64 provides no ready acknowledgment: if the initial transfer is too early, retry or load the downloaded PRG manually.</p><p><a href="game.html">Read controls, self-play and game details →</a></p></div></section>
<section id="downloads"><p class="eyebrow">02 / KEEP A COPY</p><h2>The exact release files.</h2><p>Model packet, executable program and disk image. Download links work without JavaScript.</p><div class="table-scroll"><table class="downloads"><thead><tr><th>File</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>{''.join(downloads)}</tbody></table></div><p class="quiet"><a href="manifest.json">Package manifest</a> · <a href="SHA256SUMS">Package checksums</a> · <a href="release.json">Site inventory</a></p></section>
<section class="research-lead"><p class="eyebrow">03 / FOLLOW THE EVIDENCE</p><h2>What does the network actually do?</h2><p>Distributed, position-sensitive computation—not evidence for a dedicated “fork neuron.” The complete illustrated report separates observations, interventions, guarantees and surviving counterexamples.</p><a class="text-action" href="report.html">Read the complete illustrated report →</a><p><a href="overview.html">Project overview and model lineage</a></p></section>
<section id="screenshots"><p class="eyebrow">04 / ON SCREEN</p><h2>The running game.</h2><div class="gallery">{gallery}</div></section>
<section id="music" class="split"><div><p class="eyebrow">05 / LISTEN</p><h2>{title}</h2><p>{audio_credit}</p><details><summary>Recording and emulator boundary</summary><p class="quiet">{audio_boundary}</p><p class="quiet">Authentic accepted application010 recording, retained unchanged; not a new application011 recording.</p></details></div><div><p class="quiet">{audio_details}</p><audio controls preload="metadata"><source src="{music_record['path']}" type="audio/ogg">Your browser cannot play Ogg audio; download the track below.</audio><p><a href="{music_record['path']}" download>Download the Ogg track</a> · <a href="assets/audio/provenance.json">Audio provenance</a></p><p class="quiet">{len(data):,} bytes · SHA-256 <code>{sha(data)}</code></p></div></section>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.pages-', dir=output.parent))
    try:
        for name in copied:
            if name in FROZEN:
                target = staging / 'downloads' / Path(name).name
            else:
                target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package / name, target)
        for name in ('manifest.json', 'SHA256SUMS'):
            shutil.copyfile(package / name, staging / name)
        for destination, html in documents.items():
            target = staging / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html)
        for name in ('index.mjs', 'launcher.mjs', 'publication.css'):
            shutil.copyfile(ROOT / 'pages' / name, staging / name)
        audio_dir = staging / 'assets/audio'
        audio_dir.mkdir(parents=True, exist_ok=True)
        (audio_dir / 'patient-calculations.ogg').write_bytes(data)
        (audio_dir / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        (staging / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (staging / 'index.html').write_text(shell('Play, inspect, understand', home, script=True))
        (staging / '.nojekyll').touch()
        audit_site(staging)
        if output.exists():
            output.rmdir()
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--music', type=Path, required=True)
    parser.add_argument('--music-provenance', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_pages(args.package, args.output, args.music, args.music_provenance)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Build rejected: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
