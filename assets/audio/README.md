# Patient Calculations — original game music

[Download / play the Ogg/Vorbis preview](patient-calculations.ogg).

**Original score credit:** Mercury Quill / Lewis Moten project, as recorded in
`src/app/sid_audio.asm`. This is the project's own two-voice SID score, not a
copied film/game melody or imported third-party SID tune. Existing first-party
Apache-2.0 and NOTICE terms apply; artwork exceptions are unchanged.

## What this recording is

A fresh native **VICE x64 3.9 / reSID MOS8580 emulator** WAV capture of the exact
accepted **010** game executable, idling on its PAL title screen. No keys or
SFX were injected. Monitor traces recorded zero calls to the game's audio-event
routine and zero writes to voice three's control register during 2,100 raster
ticks. The title, pending-event state, effect state and silent voice-three gate
were also checked. This is **not a physical SID recording**, a host-synthesized
approximation, a recording of release 007's effects, or a claim of listening or
physical-hardware approval.

The excerpt uses source WAV seconds **[1,39)** with a 50 ms fade-in and 1-second
fade-out. There is no gain normalization or replacement audio. The WAV mixer
buffer boundary is not claimed sample-aligned with monitor timestamps; the
preview is not advertised as a seamless loop or a sample-exact score start.

## Verified download

- Container / codec: Ogg / Vorbis (`libvorbis` quality 5).
- Duration: **38.000 seconds**; **48,000 Hz, mono**.
- File: **330,979 bytes**.
- SHA-256: `a0ce1a0d94cda8e2599a393683d51e381835c28eb88e03f486e5ec9b4e8a3461`.
- Full signed-16-bit decode: 1,824,000 samples, 1,773,020 nonzero;
  peak 2,283, RMS 379.053, **zero clipped samples**.

These are numeric decode checks, not subjective listening acceptance. The music
is intentionally quiet; the conversion preserves the game's captured level.
[provenance.json](provenance.json) records the exact executable/source/capture
hashes, encoding settings, source and decoded-output metrics, and scope limits.
It contains no machine-specific absolute paths, credentials or private endpoints.

## Reproduce locally (no upload)

From the repository root, with the existing native VICE/stock-ROM setup and
FFmpeg available:

```sh
# Captures the frozen PRG; does not rebuild or change the game/model.
python -m scripts.prepare_music_preview build/info010/build.json \
  build/music-preview-010 --capture-build

# Encode the captured WAV. Re-running this from the retained WAV with the same
# FFmpeg/libvorbis toolchain produces the same OGG bytes.
python -m scripts.prepare_music_preview build/music-preview-010/sid.wav \
  assets/audio/patient-calculations.ogg --start 1 --duration 38

.venv/bin/python -m pytest tests/test_music_preview.py -q
```

A new emulator run can have different mixer/start boundaries and WAV bytes;
byte-identical recapture is **not** promised. A fresh capture/conversion requires
updating and reviewing provenance rather than treating its hashes as unchanged.
The conversion command prints measured source/output metadata; it does not
silently rewrite the reviewed provenance file.

The raw WAV and full native monitor/VICE logs are retained in the ignored local
`build/music-preview-010/` evidence directory, not duplicated in tracked assets
or public upload trees. The repeat-encoding test uses that real WAV when present
and explicitly skips that check in a clean checkout without private evidence;
the published OGG's full decode/hash test runs independently.
