# Graphical application 005

## What changed

Delivered004 user feedback is authoritative regression evidence even though its
previous tests passed. The nine reported laps sum to 86.98 seconds (reported
87-second game); this is USER-REPORTED004, not our controlled timing. Platform
and physical hardware are unspecified. No speedup or new wall-time claim follows
from this UI correction.

Executed004 traces reproduced the cause: a title arrow called full title entry,
clearing DEN for 330,674 CPU cycles, and a normal move called full board decoding,
clearing DEN for 819,244 cycles. Those are NMOS Py65 CPU-cycle intervals, not
VIC/ROM/IEC/wall-time measurements. Saved reports are under the private operations
005/failing004 directory, with original004 captures preserved separately.

005 patches selector cells in place and caches nine rendered cell occupancies.
Ordinary human/model moves patch only changed marks/labels and compact status.
They do not clear DEN or decode complete planes. Initial view entry and replay
still disable display until full composition finishes. This is not a claim that
all transitions are instantaneous, raster-synchronized, or free of all tearing.

Title footer: INFO at row22/col2, QUIT at row23/col2; initial letter white1,
remaining letters gray12. Exact requested lower-right badge: FALCON-9 then 1.0,
both dark blue6. Frozen model identity, tags, artifact slugs and Git remotes retain
their original spelling. Immutable imported PNG/JSON art is unchanged.

INFO retains the original archive frame and 29x18 scrolling viewport, white body,
yellow headings, red emphasis, original scrollbar and gray/white footer. Both
requested repository destinations are readable across wrapped lines and labeled
not yet published. No public upload is authorized or performed.

The rejected prose controls/result banners are gone. The original compact turn
cell at $0643/$3218 shows X/O, terminal winner, D draw, ? invalid or ! error.
All nine dim row-major numeric labels remain, are replaced by original X/O mark
patches, and return on replay. Commands are described in INFO.

## Honest computation feedback

The meter uses the original split geometry: screen $063e..$064a, excluding
$0643, paired bitmap $31f0..$3257 excluding $3218..$321f. It writes all eight
scanlines, preserves the turn glyph, and uses red2 for X / blue6 for O.

32 successfully completed semantic compute boundaries advance calibrated work
credits. src/app/progress-calibration.json retains measured CPU-cycle deltas for
one deterministic canonical board at each nonterminal ply0..8. The bar is a
nominal completed-work display, NOT a time-remaining estimate or exact per-input
cycle percentage. All627 final presentation forwards execute with the meter
active and retain every original intermediate, route and logit.

Precommit fill is capped at46 of48 native columns. Independent review found that
47 plus the right outline LOOKED full, even before commit; an executed bitmap
regression now distinguishes precommit and full. Completion48 follows a legal
mark's visible-plane write, then resets before input/next turn. Errors, title,
replay and new turns clear activity/progress. No timer or drawing IRQ is used.

Seven actual console button attributes at row19/columns7,12,13,20,26,27,32 animate
independently of inputs, routing, gameplay randomness and meter credits.18 extra
safe attention-row callbacks break up a long activity gap. Their synchronous
cadence still varies with work; the lights are not a percentage or clock.
Callbacks preserve A/X/Y, flags and all ZP, and do not touch tensors/IRQ vectors.
State lies after the KERNAL ZP save ($7880..$78df), not inside it.

## Verification boundary

Fresh005 evidence: all627 numerical stages/routes/logits,4520 composed wrappers,
complete human/model draw+loss, two-human X/O wins+draw, nine-forward auto draw,
invalid/replay/title/INFO cycles. Exact PRG and true1541 D64 separately passed
stock-ROM VICE gates with unchanged IRQ/port/core/model/app and final stack255.
175 tests passed,2 historical optional ROM tests skipped,1 frozen002 evidence-
rewriting test deselected,677 subtests passed. Final005 ROM gates replace neither
those skipped historical tests nor physical-machine acceptance.

Browser PRG and D64 separately autostarted on the requested c64online target and
received trusted browser keyDown/keyUp events (not physical keys).51 saved native
board crops exactly match source art plus declared labels/marks. Both complete
human/model matches and replay; D64 also completes two-human win+draw. PRG auto
draw is captured. D64 browser connections were lost during auto attempts, so its
browser auto completion remains UNCONFIRMED; the exact D64 completed auto under
stock-ROM/true1541 VICE. No uncaptured outcome is inferred. PRG browser two-human
draw was not separately captured. Physical C64/1541 compatibility is unverified.

## Short user test

Load falken9-005-graphical.d64 with Auto Start. Arrow down/up should move the
selector without a blackout. Check left INFO/QUIT palette and dark-blue badge.
I, then down18 times shows both wrapped repository links; Q returns.
1, then5,2,4,9,7 (wait for each response) gives OXO/XXO/XOX and D.
R replays; Q returns.1, then1,2,4 gives XXO/XO./O.. and O winner.
2, then1,4,2,5,3 gives X winner.0 runs both neural sides. During inference expect
an outlined role-colored meter and dispersed button activity, with no banners.
No input/cancellation during protected synchronous computation is promised.
