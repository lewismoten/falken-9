# Playable graphical release and Hugging Face preparation

## Authorized destination and scope

Prepare a tested, playable graphical Commodore 64 game and a reproducible upload
package for the exact requested Hugging Face repository ID
**`lewismoten/falcon-9`**. The existing project/model name **Falken-9**, title
identifier `falken-9` / `v1.0`, model packet, and `model-v1.0.0` tag are preserved.
The repository spelling is intentional in this plan; do not silently rename
identifiers or republish existing model bytes under a changed model version.
Prepare the Hub upload locally; do not claim or perform public Hub publication
before the user has tested the finished disk and authorized that step.

The user is away and authorized continued work without routine intervention.
Advance passing stages, retain failures, and report the exact final test disk
and download once the complete handoff is ready.

## Frozen foundation

- Accepted 5,195-byte E4/K2 Q11/W16/A32 model:
  `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.
- Accepted core image:
  `838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961`.
- `model-v1.0.0` points to `81252dc1137bf418159c19104d71317ba3063691`.
- Numeric application 002 is implemented, stock-ROM tested and user-accepted.
  Preserve its PRG/D64 and original 001 bytes. No further training is required.
- Existing numerical evidence covers 627 canonical neural forwards and a
  composed exhaustive 4,520-board wrapper proof, not 4,520 new neural forwards.

## Stage 1 — Graphical playable application

Reuse the original, provenance-preserved game art through copied indexed PNG
sources and a reproducible asset compiler. Keep the independent Crystal-9/CP64
release untouched. Derive the complete RAM/VIC/loader map before integration;
source filenames or RAM gaps alone do not establish safe residency.

Required presentation and interaction:

- Native title/game/INFO views and complete human-versus-model play.
- Row-major 1–9 squares; external result 0 invalid/no result; unchanged internal
  occupancy, chronological letter history, symmetry and tie semantics.
- Immediate accepted-human-move feedback before expensive inference.
- Terminal result, invalid/occupied-input recovery, replay and return to title.
- Static dark-blue `falken-9` / `v1.0` identification in the title's lower-right,
  aligned with Info/Quit and visually distinct from actionable shortcuts.
- Decorative inference activity lights below the field, separate from model
  state/randomness. Safe bounded real-work updates only, never fake progress.
- All visible selectable modes must work. Prefer complete human/model,
  two-human and model/model modes; otherwise make an unavailable mode plainly
  unselectable rather than exposing a broken route.
- INFO should explain this exact model/application, controls and emulator-only
  acceptance, not retain misleading original-model or performance claims.

Prefer retaining the frozen neural core unchanged. If presentation callbacks
require a different orchestration or code path, explicitly identify and prove
that path's complete numerical equivalence; an old proof cannot validate changed
neural execution. Do not trade genuine inference for a lookup policy.

Use TDD, actual assembled execution, packaged-D64 extraction, stock-ROM VICE
lifecycle tests and real framebuffer captures. Exercise title → INFO → title →
full game → terminal/replay/title continuously, including repeated requests,
stack/register/ZP ownership and code/model immutability. Attempt the target
browser separately and distinguish PRG/D64 launch and interaction acceptance.
Never treat missing browser evidence as physical-hardware acceptance.

Freeze a new numbered artifact only after its gates pass; 003 is the next
available number at the start of this plan. New executable bytes after freezing
require another unused number. Commit verified source and evidence in small
steps and push through the existing authorized Git remote.

## Stage 2 — Reproducible Hugging Face upload package

Foreground the runnable C64 game, model purpose and a real final-game screenshot
in the model card. Include the compact model, exact integer ONNX/Netron assets,
decoded tensor workflow, provenance, applicable Apache-2.0 license/notices,
concise validation reports and a minimal expanded source tree. No ROMs,
credentials/private endpoints, installed environments, raw traces, unused
research experiments, duplicate source archives or fabricated screenshots.

Use descriptive public disk/ZIP names; bind them byte-for-byte to the frozen
numbered development disk. Preserve the exact model tag and model SHA. Explain
that this is a custom integer runtime, not GGUF, Transformers or hosted inference.
Keep current dataset pin, numeric UI versus internal representation and expert
count/top-k details explicit. The package should not depend on a sibling checkout
or an ignored development-only checkpoint to reproduce the shipped disk.

Exercise a clean build from the staged minimal source tree and from the
extracted transport ZIP. Compare the rebuilt D64, embedded model and packaged
assets byte-for-byte. Verify every shipped checksum, local model-card link,
archive path, privacy exclusion and runtime claim. Keep upload directions and
suggested commit text outside the upload root and its ZIP. No remote Hub write
is required or authorized by this preparation plan.

## Final user handoff

After independent review and exact-artifact verification, provide the new
numbered D64's working private download, its identity and minimal test sequence,
expected results, and remaining browser/physical-hardware limits. Deliver the
upload-ready expanded package and transport ZIP with a concise readiness report.
Do not ask the user to test an unchanged 002 disk as if it were the new graphical
release, and do not call the Hub repository published based on local staging.
