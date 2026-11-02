# Publication preparation

The project has three deliberately separate public surfaces:

| Surface | Contents | Excluded |
|---|---|---|
| Hugging Face `lewismoten/falken-9` | Frozen F9J2 model, final graphical011 C64 PRG/D64, consumer model card, separate C64 guide and five genuine screenshots, 39-figure indexed-PNG report and narratives, license/notice, provenance, inventory and checksums | Conventional comparison programs, assembly, tests, probes, raw numerical fixtures, art source planes, website code, music, ROMs, operator notes |
| GitHub `lewismoten/falken-9` | Authoritative application/model tooling, assembly, tests, research source/evidence inventory, art source, original music source and preview, documentation, Pages builder/workflow | ROMs, environments, credentials and ignored numbered build outputs |
| GitHub Pages | Model/PRG/D64 downloads, TY64 launch helper, storage-d64 inspector integration, screenshots, embedded/downloadable OGG, HTML game guide and complete HTML research report | Hosted inference, embedded emulator/ROM distribution, private endpoints and operator notes |

The custom `.f9j` packet is the accepted model artifact, not a Transformers
checkpoint or GGUF. Consumer documentation describes its actual loader boundary.
The package does not add a misleading general-purpose inference API.

## Local preparation

From the repository root, after the application worker has emitted verified
`publication/application-release.json` for graphical011:

```sh
.venv/bin/python scripts/prepare_publication.py \
  --output distribution/publication/v3/upload \
  --archive distribution/publication/v3/falken-9-hugging-face.zip

.venv/bin/python scripts/prepare_publication.py \
  --verify distribution/publication/v3/upload
```

Outputs must be new directories/archive names. Historical v1/v2 releases are
immutable. No command here uploads, pushes or deploys anything.

The application descriptor is loaded at **stage and verify runtime**. Its schema
is `falken9-publication-application-v1`, revision `011`, release ID
`falken-9-model-v1.0.0-app011`. It records repository-relative model/PRG/D64
paths, byte counts and SHA-256 digests; five screenshots with their paths,
digests, final-PRG binding, capture method and source artifact; and the paths and
digests of public screenshot provenance and validation JSON. A missing descriptor
is a blocking error, not permission to fall back to application010.

The stager checks the frozen 5,195-byte F9J2 model digest, confirms that the PRG
embeds that packet at `$4000`, extracts the exact PRG from the D64, and verifies
all five screenshot identities against the final executable. Verification
repeats those checks using the staged artifacts and the current descriptor. These
are packaging integrity checks, not a substitute for the application worker's
native emulator acceptance. No physical-hardware acceptance is implied.

## Indexed report presentation

`assets/interpretability/publication-indexed/manifest.json` selects exactly
39 PNGs: 35 with 16-color/4-bit palettes and four with 32-color/8-bit palettes.
Only those selected indexed rasters are copied; candidates, contact sheets,
duplicate original/full-color PNGs and optimization metric dumps stay out.
Both original and dark research PNG links resolve to the selected derivative.
The report's 39 inline images must all use those derivatives, never screenshots.
Screenshots themselves are copied unchanged. Zoomable original/dark SVG
companions and curated narrative Markdown remain available.

The generated public `assets/interpretability/presentation-inventory.json`
records source/indexed sizes and digests, SVG companions and the display-only
boundary without the full optimization manifest's candidate data. The attention
walkthrough records 81 actual Q15 attention values, a square-root display
transformation and a dark-zero to bright-blue-one scale; the original scientific
arrays remain in GitHub. Palette/display changes do not alter measured findings.

`publication/model-card.md` is the Hub model-card template. The canonical
findings remain root `report.md`; the staged report changes link destinations
and removes historical workstation paths, not measured scientific results.
The Pages renderer consumes that same staged report rather than maintaining a
second findings manuscript. Research baseline/reference terminology is historical
scientific evidence; it is not the abandoned conventional comparison application,
which is excluded from the consumer payload.

The website builder and deployment sequencing are documented in
[`docs/PAGES_PUBLICATION.md`](../docs/PAGES_PUBLICATION.md). Music provenance is
in [`assets/audio/README.md`](../assets/audio/README.md); GitHub-side research
reproduction is described in [`docs/RESEARCH_REPRODUCTION.md`](../docs/RESEARCH_REPRODUCTION.md).

## Publication gates

Preparation is not publication. Uploading to the Hub, pushing GitHub changes,
creating a release and enabling/deploying Pages are separate external writes.
After Hub publication, record its immutable commit and use it as the Pages
workflow input. Download all release files from that exact revision and compare
checksums before claiming remote publication complete. No moving-branch fallback
should silently replace a pinned release.

Every distributable file is covered by an explicit inventory and `SHA256SUMS`
(except the checksum file itself). The deterministic ZIP contains exactly that
verified tree, at the archive root, with fixed member timestamps. File privacy,
local Markdown links, unexpected files, unsafe paths and symlinks are checked.
SHA-256 checksums detect changes; they are not authenticity signatures.

The transport ZIP is an upload aid: extract it and upload its **contents** to
the Hub root. Uploading the ZIP alone only stores an archive. Operator directions
and private verification records stay outside the upload payload.

The frozen model remains `model-v1.0.0`. Application011 is accepted only through
its verified descriptor. A documentation, website or recording update is not
permission to rebuild or replace accepted bytes.
