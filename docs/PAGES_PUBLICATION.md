# Public consumer site: build from the committed release

The publication site is built by `scripts/build_public_pages.py`, not the legacy
`scripts/build_pages.py`. The old `pages/index.html`, `style.css`, `index.mjs`,
`launcher.mjs` and launcher tests remain compatible. The new surface is editorial:
actual application 011 imagery, useful downloads, illustrated research, a readable
HTML game guide, and the separately recorded accepted application010 music preview.
Frozen application010 consumer packages remain supported without changing their
recorded metadata or bytes. Nothing is published
by running either Python script locally.

## Dependency and local build

Python 3.12+ and the pinned renderer in `requirements-pages.txt` are sufficient.
Node 22 runs the existing browser-transport unit tests. No JavaScript package
install, CDN, web font, emulator, assembler, markdown approximation, or HF token
is needed.

```sh
python3 -m venv .venv-pages
.venv-pages/bin/python -m pip install -r requirements-pages.txt
.venv-pages/bin/python scripts/prepare_publication.py \
  --output build/git-public-package
.venv-pages/bin/python scripts/build_public_pages.py \
  --package build/git-public-package \
  --output build/pages-publication \
  --music assets/audio/patient-calculations.ogg \
  --music-provenance assets/audio/provenance.json
PUBLIC_PAGES_PACKAGE=build/git-public-package \
  .venv-pages/bin/python -m unittest discover -s tests -p test_public_pages.py -v
node --test tests/pages-launcher.test.mjs
```

Output must be absent or empty, and disjoint from all inputs. Rebuild into a fresh
name, or deliberately remove only the previous generated output. Builds stage in
a temporary sibling directory, audit the complete site, and atomically rename on
success; failed builds do not leave a plausible partial publication.

The source package is never modified. Validation checks its
`falken9-consumer-release-v1` manifest, every listed size/SHA-256,
`SHA256SUMS` (including the manifest itself), and independently trusted model/PRG/D64
hashes. For `falken-9-model-v1.0.0-app011`, the source checkout must contain
`publication/application-release.json`, produced only after final validation.
This local `falken9-publication-application-v1` descriptor authorizes revision
`011`: its model, PRG, D64 and all five executable-bound screenshots must match the
consumer package. Screenshot selection comes from the verified package metadata;
the descriptor is never obtained from HF or accepted from the package. Commit
this reviewed descriptor alongside the Pages sources before dispatching CI.
Source artifact paths in the descriptor are provenance, not Pages copy targets.
Its original artifact paths remain provenance. A fresh checkout resolves the
model, PRG, D64 and validation summary to the byte-identical committed mirrors
under `releases/falken-9-v1.0.0/`, checking the same descriptor digests. Only the
accepted release D64 has a Git-ignore exception; historical proof disks remain
ignored. Pages therefore needs neither Hub access nor ignored local outputs.
The unchanged 5,195-byte model retains its independent frozen digest. Application010
uses the existing legacy frozen pins and requires no new descriptor. Unsupported
release IDs fail closed. The builder rejects duplicate records, malformed inventories, path escapes,
symlinks, missing files, incorrect checksums, missing local figures, invalid local
URLs and anchors, and any illustrated report other than all 39 embedded figures.
The preview Ogg must match the digest and length in its separate provenance
(`output` record). It is not obtained from HF.

### Site contents and URL behavior

- `index.html`: gameplay image, safe launch buttons, exact byte/hash download
  table, all five actual screenshots, report/guide links, audio controls with
  `preload="metadata"`, downloadable Ogg, credit and recording boundary.
- `report.html`: complete staged `report.md`, all 39 figures linked to their SVGs,
  real Markdown tables, heading anchors and sidebar table of contents.
- `game.html`: complete consumer `c64/README.md` guide, rendered to HTML.
- `overview.html` and `docs/research/**/*.html`: rendered consumer Markdown.
- Original relative PNG/SVG paths stay intact. Kept Markdown remains available
  alongside its HTML version. Markdown-to-Markdown navigation targets HTML.
- `downloads/model.f9j`, `downloads/falken-9-c64.prg` and
  `downloads/falken-9-c64.d64` are byte-identical copies of the verified inputs.
- `release.json` is the site's own actual-path digest inventory. `manifest.json`
  and `SHA256SUMS` are preserved **package** records: their original package paths
  are not a checksum command for the rearranged Pages tree. No build output is
  evidence that publication occurred; `public_publication` remains false.
- `.nojekyll`, license and notices are included. Training/evidence JSON, scripts,
  probes, assembly, tests, artwork source files, and raw audio captures are not.
  Model/inspection provenance, the compact manifest-selected
  `assets/interpretability/publication-indexed/presentation.json`, and curated
  screenshot provenance are permitted; raw candidate data are not. Legacy010
  presentation provenance remains supported. The unchanged Ogg is the authentic
  38-second accepted application010 capture, not a new application011 recording.

All site-local URLs are document-relative, including nested research pages, so
`https://OWNER.github.io/REPO/` works without root-absolute paths. Excluded code
and evidence links go to `https://github.com/lewismoten/falken-9/blob/main/…`;
this source-navigation choice is not used to select the binary release.

### Launch protocol safety

`pages/launcher.mjs` is unchanged. Both popup opens occur in the user gesture
before asynchronous work. PRG/D64 transports fetch only allowed same-origin
`downloads/` paths; length and SHA-256 must match before posting bytes. Destination
origins are explicit, never `*`. The storage-d64 receiver must match its origin,
window source, message type and fresh request ID. Timeouts and failures clean up,
report recovery, and leave manual downloads available. Reload/retry refreshes only
an owned inspector popup. TY64 has no ready acknowledgment: its existing delayed
transfer is explicitly best effort, not an invented handshake.

## Publication sequencing

1. Review and commit the source, `publication/application-release.json`, the
   accepted release under `releases/falken-9-v1.0.0/`, all report/screenshot
   assets, renderer requirements, workflow and recorded Ogg/provenance.
2. Select **GitHub Actions** in repository Settings → Pages. Review any
   `github-pages` environment protection for the approved branch.
3. Manually dispatch `.github/workflows/pages.yml` on the approved Git commit.
   There is no required Hub revision, token or binary download. The build stages
   and verifies the committed release, runs publication/launcher tests, renders
   the site and uploads only `build/pages-publication`.
4. The dependent deployment job publishes that artifact with `pages: write`
   and `id-token: write`. The build has read-only permissions and checkout
   credentials are not retained.
5. Verify the project-subpath URL, all 39 report figures, guide, downloads and
   audio. **Run PRG** sends the verified same-origin PRG to TY64;
   **Inspect D64** sends the verified same-origin disk to storage-d64. These
   are distinct external destinations, not embedded emulator/parser copies.

Hugging Face remains a separate consumer distribution. The optional
`scripts/fetch_public_release.py` can still audit an explicitly supplied full
40-hex Hub revision; the Pages deployment does not call it. Neither local builds
nor generated manifests constitute evidence of a successful remote deployment.

## Verification and boundaries

Tests exercise real Markdown rendering, aligned tables, anchors, SVG links,
all-figure enforcement, output isolation, corruption/path/symlink rejection,
curation, real-package integration and immutable-fetch failures. Synthetic
fixtures are labeled as fixtures; their hashes override pins **only in tests**.
There is no CLI option to disable the frozen release pins. The real integration
test runs automatically when the local package exists; CI sets
`PUBLIC_PAGES_PACKAGE` after Git staging, so a missing package is a failure, not a
silent fixture-only success.

For local visual checks, serve only the generated output (or its immediate build
parent) on loopback and review it under a non-root subpath. Check desktop and
mobile horizontal overflow, all 39 loaded report images, 39 SVG image links,
local download digests in browser Web Crypto, and console/page errors. Audio
controls/metadata layout can be inspected without claiming listening approval;
verify the Ogg with ffprobe/full decode separately. A local browser environment
that leaves HTML media in `HAVE_NOTHING` is not proof of a broken or successful
public player; explicitly record playback as unconfirmed until tested in the
actual deployed browser. No physical SID recording claim is made.

Official implementation references:

- [GitHub custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Python-Markdown tables](https://python-markdown.github.io/extensions/tables/)
- [Python-Markdown heading anchors / TOC](https://python-markdown.github.io/extensions/toc/)
