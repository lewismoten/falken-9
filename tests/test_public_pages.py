"""Publication Pages tests; synthetic fixtures never represent release evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def real_package():
    if os.environ.get('PUBLIC_PAGES_PACKAGE'):
        return ROOT / os.environ['PUBLIC_PAGES_PACKAGE']
    revised = ROOT / 'distribution/publication/v2/upload'
    return revised if revised.exists() else ROOT / 'distribution/publication/v1/upload'


def load_builder():
    path = ROOT / 'scripts/build_public_pages.py'
    if not path.exists():
        raise AssertionError('publication builder is not implemented')
    spec = importlib.util.spec_from_file_location('public_pages', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicPagesTests(unittest.TestCase):
    def fixture(self, root):
        package = root / 'package'
        package.mkdir()
        contents = {
            'README.md': '# Overview\n[Report](report.md) · [Model](model.f9j)',
            'report.md': '# Research\n\n## A finding\n\n| A | B |\n|:---|---:|\n| 1 | 2 |\n\n' + '\n\n'.join(f'[![Figure {i}](docs/research/study/figure{i}.png)](docs/research/study/figure{i}.svg)' for i in range(37)),
            'c64/README.md': '# Game guide\n\n## Play\n\n[Research](../report.md)\n\n![Game](../assets/screenshots/falken9-010-gameplay.png)',
            'LICENSE': 'Fixture license', 'NOTICE': 'Fixture notice',
            'model.f9j': b'fixture model', 'c64/falken-9-c64.prg': b'fixture PRG',
            'c64/falken-9-c64.d64': b'fixture D64',
            'assets/screenshots/falken9-010-gameplay.png': b'\x89PNG\r\n\x1a\nfixture',
            'docs/research/study/REPORT.md': '# Study\n[Source](../../../scripts/probe.py)',
            'scripts/probe.py': 'not copied',
        }
        for i in range(37):
            contents[f'docs/research/study/figure{i}.png'] = b'\x89PNG\r\n\x1a\nfixture'
            contents[f'docs/research/study/figure{i}.svg'] = '<svg xmlns="http://www.w3.org/2000/svg"/>'
        records = []
        for name, content in contents.items():
            path = package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode() if isinstance(content, str) else content
            path.write_bytes(data)
            records.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        (package / 'manifest.json').write_text(json.dumps(dict(schema='falken9-consumer-release-v1', release_id='falken-9-model-v1.0.0-app010', report={'inline_figures':37}, files=records)))
        (package / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in records) + hashlib.sha256((package / 'manifest.json').read_bytes()).hexdigest() + '  manifest.json\n')
        music = root / 'music.ogg'
        music.write_bytes(b'OggSfixture audio')
        provenance = root / 'provenance.json'
        provenance.write_text(json.dumps(dict(title='Patient Calculations', sha256=hashlib.sha256(music.read_bytes()).hexdigest(), bytes=music.stat().st_size)))
        frozen = {r['path']: dict(sha256=r['sha256'], bytes=r['bytes']) for r in records if r['path'].endswith(('.f9j', '.prg', '.d64'))}
        return package, music, provenance, frozen

    def test_validated_build_renders_tables_all_figures_audio_and_relative_links(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, music, provenance, frozen = self.fixture(root)
            with patch.object(builder, 'FROZEN', frozen):
                builder.build_pages(package, root / 'output', music, provenance)
            output = root / 'output'
            report = (output / 'report.html').read_text()
            self.assertIn('<table>', report)
            self.assertIn('id="a-finding"', report)
            self.assertEqual(report.count('<img '), 37)
            self.assertIn('figure36.svg', report)
            home = (output / 'index.html').read_text()
            self.assertIn('preload="metadata"', home)
            self.assertIn('<audio controls', home)
            self.assertIn('Patient Calculations', home)
            self.assertIn('game.html', home)
            self.assertTrue((output / '.nojekyll').exists())
            self.assertFalse((output / 'scripts').exists())
            self.assertIn('github.com/lewismoten/falken-9/blob/main/scripts/probe.py', (output / 'docs/research/study/REPORT.html').read_text())
            for name, record in frozen.items():
                target = output / 'downloads' / Path(name).name
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), record['sha256'])
            builder.audit_site(output)

    def final011_fixture(self, root):
        package, music, provenance, frozen = self.fixture(root)
        for kind in ('title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session'):
            path = package / f'assets/screenshots/falken-9-011-{kind}.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\nfixture ' + kind.encode())
        (package / 'assets/screenshots/falken9-010-gameplay.png').unlink()
        (package / 'c64/README.md').write_text('# Game guide\n' + '\n'.join(
            f'![{kind}](../assets/screenshots/falken-9-011-{kind}.png)' for kind in ('title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session')))
        figures = package / 'assets/interpretability/publication-indexed'
        figures.mkdir(parents=True)
        for i in range(39):
            (figures / f'figure{i}.png').write_bytes(b'\x89PNG\r\n\x1a\nindexed fixture')
        (figures / 'presentation.json').write_text('{}')
        (package / 'report.md').write_text('# Report\n' + '\n'.join(
            f'![Figure {i}](assets/interpretability/publication-indexed/figure{i}.png)' for i in range(39)))
        descriptor = dict(schema='falken9-publication-application-v1', revision='011',
                          release_id='falken-9-model-v1.0.0-app011')
        def record(path):
            data = (package / path).read_bytes()
            return dict(path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        descriptor.update({kind: record(path) for kind, path in [('model', 'model.f9j'), ('prg', 'c64/falken-9-c64.prg'), ('d64', 'c64/falken-9-c64.d64')]})
        descriptor['screenshots'] = [dict(record(f'assets/screenshots/falken-9-011-{kind}.png'),
            prg_sha256=frozen['c64/falken-9-c64.prg']['sha256'], method='Synthetic fixture only', source_artifact='fixture.prg')
            for kind in ('title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session')]
        descriptor['screenshot_provenance'] = dict(path='assets/screenshots/application011-provenance.json', sha256='1' * 64)
        descriptor['validation'] = dict(path='results/fixture-validation.json', sha256='2' * 64)
        trusted = root / 'application-release.json'
        trusted.write_text(json.dumps(descriptor))
        self.refresh_fixture(package, 39, descriptor['release_id'])
        return package, music, provenance, frozen, trusted

    def refresh_fixture(self, package, figures, release_id):
        records = []
        for path in sorted(package.rglob('*')):
            if path.is_file() and path.name not in ('manifest.json', 'SHA256SUMS'):
                data = path.read_bytes()
                records.append(dict(path=path.relative_to(package).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        manifest = package / 'manifest.json'
        manifest.write_text(json.dumps(dict(schema='falken9-consumer-release-v1', release_id=release_id, report={'inline_figures': figures}, files=records, screenshots=[r for r in records if r['path'].startswith('assets/screenshots/') and r['path'].endswith('.png')])))
        (package / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in records) + hashlib.sha256(manifest.read_bytes()).hexdigest() + '  manifest.json\n')

    def test_final011_uses_local_trust_and_copies_all_current_screenshots(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, music, provenance, frozen, trusted = self.final011_fixture(root)
            with patch.object(builder, 'FROZEN', frozen), patch.object(builder, 'APPLICATION_DESCRIPTOR', trusted):
                inventory = builder.build_pages(package, root / 'site', music, provenance)
            self.assertEqual(inventory['release_id'], 'falken-9-model-v1.0.0-app011')
            self.assertEqual((root / 'site/report.html').read_text().count('<img '), 39)
            self.assertEqual((root / 'site/game.html').read_text().count('<img '), 5)
            self.assertIn('falken-9-011-title.png', (root / 'site/index.html').read_text())
            self.assertIn('not a new application011 recording', (root / 'site/index.html').read_text())
            self.assertTrue((root / 'site/assets/interpretability/publication-indexed/presentation.json').is_file())
            self.assertFalse((root / 'site/application-release.json').exists())
            builder.audit_site(root / 'site')

    def test_final011_cannot_self_authorize_or_change_pinned_evidence(self):
        builder = load_builder()
        for fault in ('absent', 'model', 'prg', 'screenshot', 'shot_prg', 'revision', 'unknown_release'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package, _, _, frozen, trusted = self.final011_fixture(root)
                descriptor = json.loads(trusted.read_text())
                if fault == 'absent':
                    # A descriptor supplied by the downloaded package is not trusted.
                    (package / 'application-release.json').write_bytes(trusted.read_bytes())
                    trusted.unlink()
                elif fault in ('model', 'prg'):
                    descriptor[fault]['sha256'] = '0' * 64
                elif fault == 'screenshot':
                    descriptor['screenshots'][0]['sha256'] = '0' * 64
                elif fault == 'shot_prg':
                    descriptor['screenshots'][0]['prg_sha256'] = '0' * 64
                elif fault == 'revision':
                    descriptor['revision'] = '010'
                if fault != 'absent': trusted.write_text(json.dumps(descriptor))
                if fault == 'unknown_release':
                    self.refresh_fixture(package, 39, 'untrusted-app012')
                with patch.object(builder, 'FROZEN', frozen), patch.object(builder, 'APPLICATION_DESCRIPTOR', trusted), self.assertRaises(ValueError):
                    builder.validate_package(package)

    def test_final011_screenshot_metadata_without_redundant_byte_counts(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _, _, frozen, trusted = self.final011_fixture(root)
            descriptor = json.loads(trusted.read_text())
            for shot in descriptor['screenshots']:
                shot.pop('bytes')
            trusted.write_text(json.dumps(descriptor))
            with patch.object(builder, 'FROZEN', frozen), patch.object(builder, 'APPLICATION_DESCRIPTOR', trusted):
                builder.validate_package(package)

    def test_final011_rejects_missing_or_false_package_screenshot_metadata(self):
        builder = load_builder()
        for fault in ('missing', 'path', 'digest'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package, _, _, frozen, trusted = self.final011_fixture(root)
                manifest_path = package / 'manifest.json'
                manifest = json.loads(manifest_path.read_text())
                if fault == 'missing': manifest.pop('screenshots')
                if fault == 'path': manifest['screenshots'][0]['path'] = 'assets/screenshots/falken9-010-title.png'
                if fault == 'digest': manifest['screenshots'][0]['sha256'] = '0' * 64
                manifest_path.write_text(json.dumps(manifest))
                sums = package / 'SHA256SUMS'
                sums.write_text(sums.read_text().rsplit('\n', 2)[0] + '\n' + hashlib.sha256(manifest_path.read_bytes()).hexdigest() + '  manifest.json\n')
                with patch.object(builder, 'FROZEN', frozen), patch.object(builder, 'APPLICATION_DESCRIPTOR', trusted), self.assertRaises(ValueError):
                    builder.validate_package(package)

    def test_fetch_final011_uses_same_local_descriptor_gate(self):
        spec = importlib.util.spec_from_file_location('fetch_public_release', ROOT / 'scripts/fetch_public_release.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _, _, frozen, trusted = self.final011_fixture(root)
            prefix = 'https://huggingface.co/lewismoten/falken-9/resolve/' + 'a' * 40 + '/'
            def download(url):
                self.assertTrue(url.startswith(prefix))
                return (package / url.removeprefix(prefix)).read_bytes()
            with patch.object(module.builder, 'FROZEN', frozen), patch.object(module.builder, 'APPLICATION_DESCRIPTOR', trusted):
                result = module.fetch_release('a' * 40, root / 'download', download=download)
            self.assertEqual(result['repository'], 'lewismoten/falken-9')
            self.assertEqual((root / 'download/c64/falken-9-c64.prg').read_bytes(), (package / 'c64/falken-9-c64.prg').read_bytes())
            trusted.unlink()
            with patch.object(module.builder, 'FROZEN', frozen), patch.object(module.builder, 'APPLICATION_DESCRIPTOR', trusted), self.assertRaises(ValueError):
                module.fetch_release('a' * 40, root / 'untrusted', download=download)
            self.assertFalse((root / 'untrusted').exists())

    def test_final011_game_guide_must_display_all_five_selected_screenshots(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, music, provenance, frozen, trusted = self.final011_fixture(root)
            (package / 'c64/README.md').write_text('# Guide without screenshot embeds')
            self.refresh_fixture(package, 39, 'falken-9-model-v1.0.0-app011')
            with patch.object(builder, 'FROZEN', frozen), patch.object(builder, 'APPLICATION_DESCRIPTOR', trusted), self.assertRaisesRegex(ValueError, 'five.*screenshots'):
                builder.build_pages(package, root / 'site', music, provenance)
            self.assertFalse((root / 'site').exists())

    def test_curated_assets_exclude_candidates_and_raw_numerical_data(self):
        builder = load_builder()
        for name in ('assets/interpretability/candidates/test.png', 'assets/interpretability/publication-indexed/candidate-01.png', 'assets/interpretability/publication-indexed/raw.json'):
            self.assertFalse(builder.curated(name), name)
        self.assertTrue(builder.curated('assets/interpretability/publication-indexed/presentation.json'))

    def test_wrong_manifest_schema_is_rejected(self):
        builder = load_builder()
        with self.assertRaises(ValueError):
            builder.manifest_records({'schema': 'not-this-release', 'files': [{'path': 'x', 'bytes': 0, 'sha256': '0' * 64}]})

    def test_corrupt_manifest_hash_checksums_paths_symlinks_and_pins(self):
        builder = load_builder()
        for fault in ('hash', 'bytes', 'pin', 'path', 'duplicate', 'symlink', 'sums', 'missing', 'manifest'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package, music, provenance, frozen = self.fixture(root)
                path = package / 'manifest.json'
                manifest = json.loads(path.read_text())
                if fault == 'hash':
                    (package / 'model.f9j').write_bytes(b'wrong')
                elif fault == 'bytes':
                    manifest['files'][0]['bytes'] += 1
                elif fault == 'pin':
                    frozen['model.f9j']['sha256'] = '0' * 64
                elif fault == 'path':
                    manifest['files'][0]['path'] = '../escape'
                elif fault == 'duplicate':
                    manifest['files'].append(manifest['files'][0])
                elif fault == 'symlink':
                    original = package / 'model.f9j'
                    copy = root / 'model'
                    copy.write_bytes(original.read_bytes())
                    original.unlink()
                    original.symlink_to(copy)
                elif fault == 'sums':
                    (package / 'SHA256SUMS').write_text('bad checksum')
                elif fault == 'missing':
                    (package / 'LICENSE').unlink()
                elif fault == 'manifest':
                    path.write_text('{')
                if fault not in {'manifest'}:
                    path.write_text(json.dumps(manifest))
                with patch.object(builder, 'FROZEN', frozen), self.assertRaises(ValueError):
                    builder.validate_package(package)
                self.assertFalse((root / 'output').exists())

    def test_missing_images_bad_urls_figure_count_audio_and_output_safety(self):
        builder = load_builder()
        for fault in ('image', 'url', 'figure', 'audio', 'audio_digest', 'occupied', 'overlap', 'music_overlap'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package, music, provenance, frozen = self.fixture(root)
                report = package / 'report.md'
                if fault == 'image':
                    report.write_text(report.read_text().replace('figure0.png', 'missing.png'))
                elif fault == 'url':
                    report.write_text(report.read_text() + '\n[Bad](/root.html)')
                elif fault == 'figure':
                    report.write_text(report.read_text().replace('![Figure 0]', '[Figure 0]'))
                elif fault == 'audio':
                    music.write_bytes(b'not an ogg')
                elif fault == 'audio_digest':
                    provenance.write_text(json.dumps({'output': {'sha256': '0' * 64, 'bytes': music.stat().st_size}}))
                # Keep the manifest honest so failures exercise rendering, not SHA validation.
                manifest = json.loads((package / 'manifest.json').read_text())
                for record in manifest['files']:
                    payload = (package / record['path']).read_bytes()
                    record.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
                (package / 'manifest.json').write_text(json.dumps(manifest))
                (package / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in manifest['files']) + hashlib.sha256((package / 'manifest.json').read_bytes()).hexdigest() + '  manifest.json\n')
                output = root / 'output'
                if fault == 'occupied':
                    output.mkdir()
                    (output / 'keep').touch()
                elif fault == 'overlap':
                    output = package / 'output'
                elif fault == 'music_overlap':
                    output = music
                with patch.object(builder, 'FROZEN', frozen), self.assertRaises(ValueError):
                    builder.build_pages(package, output, music, provenance)

    def test_site_audit_rejects_root_absolute_missing_and_escaping_links(self):
        builder = load_builder()
        for url in ('/asset.png', '../escape.png', 'missing.png', 'javascript:alert(1)', '#absent'):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'index.html').write_text(f'<a href="{url}">x</a>')
                with self.assertRaises(ValueError):
                    builder.audit_site(root)

    def test_fetch_requires_immutable_revision_and_verifies_downloads(self):
        spec = importlib.util.spec_from_file_location('fetch_public_release', ROOT / 'scripts/fetch_public_release.py')
        self.assertTrue((ROOT / 'scripts/fetch_public_release.py').is_file(), 'public immutable fetcher is not implemented')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for revision in ('main', '', 'a' * 39, 'g' * 40, 'a' * 40 + '/bad'):
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                module.fetch_release(revision, Path(directory) / 'download')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _, _, frozen = self.fixture(root)
            urls = []
            def download(url):
                urls.append(url)
                relative = url.split('/resolve/' + 'a' * 40 + '/', 1)[1]
                return (package / relative).read_bytes()
            with patch.object(module.builder, 'FROZEN', frozen):
                module.fetch_release('a' * 40, root / 'download', download=download)
            self.assertTrue(urls)
            self.assertTrue(all('huggingface.co/lewismoten/falken-9/resolve/' + 'a' * 40 + '/' in url for url in urls))
            self.assertEqual((root / 'download/model.f9j').read_bytes(), b'fixture model')
            with patch.object(module.builder, 'FROZEN', frozen), self.assertRaises(ValueError):
                module.fetch_release('a' * 40, root / 'corrupt', download=lambda url: b'broken' if url.endswith('model.f9j') else download(url))
            self.assertFalse((root / 'corrupt').exists())

    def test_real_consumer_package_and_committed_audio_integration(self):
        package = real_package()
        if not package.exists():
            if os.environ.get('PUBLIC_PAGES_PACKAGE'):
                self.fail('Explicit real package input is missing')
            self.skipTest('No local release package; workflow fetches it before testing')
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            inventory = builder.build_pages(package, output, ROOT / 'assets/audio/patient-calculations.ogg', ROOT / 'assets/audio/provenance.json')
            report = (output / 'report.html').read_text()
            declared = json.loads((package / 'manifest.json').read_text())
            self.assertEqual(report.count('<img '), declared['report']['inline_figures'])
            self.assertIn('<table>', report)
            self.assertEqual(inventory['model']['bytes'], 5195)
            self.assertEqual(inventory['prg']['bytes'], declared['artifacts']['prg']['bytes'])
            self.assertEqual(inventory['d64']['bytes'], 174848)
            self.assertEqual(inventory['music']['sha256'], 'a0ce1a0d94cda8e2599a393683d51e381835c28eb88e03f486e5ec9b4e8a3461')
            self.assertEqual(len(list((output / 'assets/screenshots').glob('*.png'))), len(declared['screenshots']))
            self.assertFalse(any(path.suffix in {'.py', '.asm', '.wav'} for path in output.rglob('*')))
            expected_json = {'model.json', 'manifest.json', 'release.json', 'assets/audio/provenance.json'}
            for name in ('assets/interpretability/presentation-inventory.json', 'provenance/application-screenshot-provenance.json', 'provenance/application-validation.json', 'assets/interpretability/model-inspection/provenance.json', 'assets/interpretability/publication-dark/presentation.json', 'assets/screenshots/application010-additional-provenance.json', 'assets/interpretability/publication-indexed/presentation.json', 'assets/screenshots/application011-provenance.json'):
                if (package / name).is_file(): expected_json.add(name)
            self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*.json')}, expected_json)
            builder.audit_site(output)

    def test_real_overview_metadata_links_remain_site_local(self):
        from html.parser import HTMLParser
        package = real_package()
        if not package.exists():
            if os.environ.get('PUBLIC_PAGES_PACKAGE'):
                self.fail('Explicit real package input is missing')
            self.skipTest('No local release package')
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = set()
            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.hrefs.add(dict(attrs).get('href'))
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            builder.build_pages(package, output, ROOT / 'assets/audio/patient-calculations.ogg', ROOT / 'assets/audio/provenance.json')
            self.assertEqual((output / 'model.json').read_bytes(), (package / 'model.json').read_bytes())
            links = Links()
            links.feed((output / 'overview.html').read_text())
            self.assertTrue({'model.json', 'manifest.json', 'SHA256SUMS'} <= links.hrefs)

    def test_workflow_is_manual_and_only_uploads_curated_build(self):
        workflow = (ROOT / '.github/workflows/pages.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('hf_revision:', workflow)
        self.assertIn('scripts/prepare_publication.py', workflow)
        self.assertIn('build/git-public-package', workflow)
        self.assertNotIn('scripts/fetch_public_release.py', workflow)
        self.assertNotIn('  push:', workflow)
        self.assertNotIn('default: main', workflow)
        self.assertIn('path: build/pages-publication', workflow)
        self.assertIn('needs: build', workflow)
        self.assertIn('permissions: {}', workflow)
        self.assertIn('pages: write', workflow)
        self.assertIn('id-token: write', workflow)
        self.assertIn('persist-credentials: false', workflow)

    def test_missing_manifest_is_rejected_without_output(self):
        builder = load_builder()
        self.assertIsNotNone(builder, 'publication builder is not implemented')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package'
            package.mkdir()
            with self.assertRaises(ValueError):
                builder.validate_package(package)
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
