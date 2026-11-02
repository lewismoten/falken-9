# Falken-9 model v1.0.0 / Crystal Palace 9

Accepted graphical011 release, committed as ordinary Git blobs for direct
GitHub Pages downloads and external-site transfers. These are unchanged copies
of the validated release—not rebuilt, patched or converted executables.

| File | Bytes | Purpose |
|---|---:|---|
| `model.f9j` | 5,195 | Frozen F9J2 Q11/W16/A32 neural model |
| `falken-9-c64.prg` | 50,507 | Standalone Crystal Palace 9 program |
| `falken-9-c64.d64` | 174,848 | Disk containing that exact PRG |
| `application-validation.json` | 28,008 | Bound native/Py65 validation summary |

Verify this directory with `sha256sum --check SHA256SUMS`.
[`manifest.json`](manifest.json) binds these files to the reviewed
[`application descriptor`](../../publication/application-release.json).
Original numbered builds and provenance paths remain unchanged.

The [Pages launcher](https://lewismoten.github.io/falken-9/) serves these bytes
from its own `downloads/` directory and checks sizes/SHA-256 before transfer:

- **Run PRG** sends the PRG to the external TY64 emulator.
- **Inspect D64** sends the disk to Lewis Moten's storage-d64 inspector.

Hugging Face is a separate distribution, not a Pages build/launch dependency.
See the [game guide](../../docs/C64_GAME.md) for controls and the
[Pages build guide](../../docs/PAGES_PUBLICATION.md) for deployment.

**Emulator-tested only:** physical C64/1541/SID compatibility and performance
are unverified. The 5,195-byte figure is model data, not the full game/RAM size.
Repository [license](../../LICENSE) and [notices](../../NOTICE) apply.
