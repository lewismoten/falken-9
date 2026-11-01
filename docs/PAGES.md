# GitHub-only C64 launcher

`pages/` is a compact static launcher, not an emulator, disk parser or hosted model. It is deliberately excluded from the Hugging Face source/upload allowlist. The Hub runnable formats remain the self-contained PRG and D64; authoritative model/source/inspection files are preserved there. Nothing in this change creates a public repository, enables Pages or uploads to the Hub.

## Local build and deployment preparation

With the prepared numbered candidate and an actual final-executable screenshot:

    .venv/bin/python -m scripts.build_pages \
      --candidate artifacts/app/007-graphical \
      --screenshot assets/screenshots/falken9-007-title.png \
      --output build/pages-007
    python3 -m http.server 8847 --bind 127.0.0.1 --directory build/pages-007

Use http://127.0.0.1:8847/ for local testing, not file://. The builder refuses nonempty or candidate-overlapping output and any output inside `distribution/`. It verifies candidate PRG hash and exact extraction from D64, generates same-origin relative downloads and a byte/SHA-256 inventory, and copies one actual screenshot. Generated D64 stays ignored. A minimal upload/rebuild is independent of this optional site.

The existing repository remote remains unchanged. GitHub repository creation, a public release URL and a Pages deployment workflow/activation require separate publication authorization. Once that destination is authorized, the generated static directory is the deployment input; do not deploy the repository root or the Hub upload tree. No private download host, ROM, credential or local machine path is in the generated site. Local integration does not claim a GitHub Actions run or a live Pages deployment.

A downloaded expanded release can also supply the candidate: copy its one PRG/D64 plus `validation/build.json` (as candidate `build.json`) into a new directory; use a shipped actual screenshot. No binary fetch occurs during site construction.

## Authorized protocol attribution

The window transports are minimal adaptations of Lewis Moten's own Sector-256 integration:

- https://github.com/lewismoten/sector-256/blob/main/pages/index.js
- reviewed source SHA-256 a725e8d3daf20851b1197e395659c0f8f14cb648a31601ded0b7b6cbdb8d450b
- Existing receiver: https://lewismoten.github.io/storage-d64/
- receiver external-load.js SHA-256 d980519f004d80112428e2771075bb0340523f8b3123acc68c80d80663607a19

Only the small integration pattern is adapted; no unrelated app or D64 parser is copied. The external inspector is not modified.

## Exact transports and recovery

Run PRG opens the named TY64 window synchronously in the click handler, fetches and verifies the complete PRG (including its two-byte C64 load address), waits three seconds, then posts a Uint8Array to exactly https://ty64.krissz.hu . That source has no readiness acknowledgment. A successful post is not a guaranteed receiver load; retry/manual download is explicitly available. Popup, fetch, integrity and closed-window failures are recoverable.

Inspect Disk installs its message listener before opening a UUID-specific receive document. Readiness requires the opened window source, exact inspector origin, `storage-d64:ready` type and exact receiveRequestId. It ignores mismatches, times out after ten seconds and cleans timer/listener on every path. After readiness and exact binary verification, it posts `{type:'storage-d64:load',sourceName,bytes:Uint8Array}` with an explicit inspector target origin. No outbound wildcard origin is used.

The inspector emits readiness on document load, not hashchange. Repeated inspection closes only the previously owned receiver and opens a fresh document. After launcher reload, an ownership marker and opener check recover that window; the UI warns users to save inspector edits before reopening. A foreign owned window is rejected. Artifact/inventory fetches have ten-second aborts; inventory failure exposes a reload retry. Expected hashes bind the generated release, not an independent authenticity signature against a compromised site.

## Executed evidence and limits

Node tests use mocked windows for exact bytes, load address, target origins, wrong source/origin/type/request ID, popup/timeout/network/integrity/closed-window errors, cleanup and retry/reload behavior. They are protocol unit proof, not native emulator acceptance.

The real loopback page was exercised against live TY64 and live storage-d64 using the final numbered PRG/D64. Receiver-side byte digests match the final files; TY64 rendered the native title and a human/model reply. The live inspector displayed its sourceName/directory, and its own native parser extracted the exact PRG. Retry and launcher-reload receiver recovery were exercised. Receiver-native screenshots and events are retained privately. The current inspector displays zero blocks for this entry despite a valid 198-sector chain and c1541 count; that external UI discrepancy is disclosed rather than patched here.

The user's c64online target is a separate format-specific test, not the TY64 transport receiver. Its completed and interrupted paths are listed in [application acceptance](APP_GRAPHICAL_007.md). Browser host focus/transport failures and physical keyboard/hardware acceptance are not silently promoted to passes.
