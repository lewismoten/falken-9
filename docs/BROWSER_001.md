# Resident 001: c64online browser acceptance

Test date: October 31, 2026. Target: `https://c64online.com/c64-online-emulator/`, anonymous fresh Chromium session, displayed emulator V1.0.4.8/5283. No account, network publication, game changes, RAM/keyboard-queue injection, forced PC, or internal inference invocation was used.

## Frozen artifacts

| Format | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| PRG | `artifacts/app/001-resident/falken9-001-resident.prg` | 33162 | `faa07bd4b9aa1c40894098407046d29a3310b52ab5dcdf0cc47ba6daf98f3b47` |
| D64 | `artifacts/app/001-resident/falken9-001-resident.d64` | 174848 | `b26580db7ed064360f3fb3ffdf15105645b9f242239e72e57137a447f80925a2` |

Both exact local files were selected through the real page `#c64fd` file input using CDP `DOM.setFileInputFiles`. The browser and artifact filesystem were shared; no fabricated transport was necessary. Local SHA-256 was checked before each format. The D64's selected browser `File` was also hashed using Web Crypto (`d64-browser-upload.json`). PRG selection reported the exact filename and 33162 bytes; its source hash was checked locally, not independently inside Web Crypto.

All evidence below is under `artifacts/app/001-resident/browser/`. `manifest.json` binds evidence hashes, format, artifact SHA, and actual/attempted input sequences. Full-page screenshots show the host page; `*-canvas.png` are direct lossless captures of the actual emulator canvas, not reconstructed boards. `visual-review-contact-sheet.png` is a labeled montage of those unmodified canvas captures.

## Result boundary

| Gate | PRG | D64 |
| --- | --- | --- |
| Upload exact frozen artifact | Pass | Pass |
| Auto Start launch, no manually typed RUN/SYS/LOAD | Pass | Pass |
| Human/model response through browser key events | Complete matches | Opening A → model E only |
| Complete draw | Pass | Unconfirmed |
| Complete O win | Pass | Unconfirmed |
| Occupied-cell recovery | Pass | Unconfirmed |
| Terminal input lock and R replay | Pass after draw and O win | Unconfirmed: host ad iframe intercepted later events |

The PRG interaction acceptance passes for the tested sequences. D64 launch passes, but D64 full keyboard acceptance remains **unconfirmed**, not a game failure or a complete-match pass. Neither format proves physical C64 hardware behavior.

## Launch instructions actually exercised

1. Open the exact target page and keep its browser tab active/visible.
2. Leave **Auto Start** checked (default).
3. Select the numbered PRG or D64 through the site's File Browser/upload input.
4. Wait for the board. No manual BASIC command was sent for either format.

The first PRG attempt initially showed a garbled power-up screen while `document.visibilityState` was `hidden`. Clicking its canvas was insufficient. Activating the actual tab using CDP `Page.bringToFront` made it `visible`; the already uploaded PRG then reached the game. Thus `01-prg-upload-failure.png` is an initially stalled launch observation, not the final launch verdict. `03-prg-autostart.png` and its canvas capture show the successful empty-board launch.

D64 was loaded from a fresh page with Auto Start checked. `21-d64-upload-state.png` visibly shows the emulator-generated `LOAD"*",8,1`, `SEARCHING FOR *`, and `LOADING`; `22-d64-after-wait.png` shows the empty game board. There were zero observed page keyboard events between upload and that board. This verifies disk mount/load/autostart, not merely mounting a disk or manually compensating with RUN. The site's default fast-load checkbox remained enabled; no physical-drive or browser timing claim is made.

## PRG keyboard and visual evidence

Input was delivered as CDP `Input.dispatchKeyEvent` keyDown/keyUp pairs with ordinary letter keys and `KeyA`–`KeyR` codes, about 150 ms between down and up. This is browser keyboard-event delivery through the emulator's existing handler, **not a physical USB keyboard test**. The page captured every PRG down/up with `isTrusted: true` and `repeat: false`; see `prg-key-events.json`. No page JS state was used as a substitute for visible board inspection.

Observed PRG key-down sequence, including rejection and terminal tests:

`E E B D I G A R A B D I R`

### Draw, invalid input, terminal lock, replay

- `E` → X at E, model O at C (`04-prg-E.png`).
- Second `E` → unchanged marks and **INVALID / OCCUPIED - TRY A-I** (`05-prg-occupied-E-canvas.png`).
- `B` → X at B, O at H (`06-prg-B-canvas.png`): input recovery succeeded.
- `D` → X at D, O at F (`07-prg-D-canvas.png`).
- `I` → X at I, O at A (`08-prg-I-canvas.png`).
- `G` → X at G and **DRAW - R TO REPLAY** (`09-prg-draw-canvas.png`).

Accepted chronological marks: `ecbhdfiag`. Final board, inspected visually:

```text
O X O
X X O
X O X
```

Every cell is occupied, X has five marks, O four, and neither side has a winning row, column, or diagonal. The displayed draw agrees with the board rules.

- Terminal `A` leaves the board and DRAW text unchanged (`10-prg-draw-terminal-A-canvas.png`); its canvas PNG is byte-identical to the prior draw capture.
- `R` clears all marks, restores A–I labels, and displays **YOUR TURN - A TO I** (`11-prg-replay-canvas.png`).

### O win, terminal lock, replay

From that replayed empty board:

- `A` → X at A, O at E (`12-prg-A-canvas.png`).
- `B` → X at B, O at C (`13-prg-B-canvas.png`).
- `D` → X at D, O at G and **O WINS - R TO REPLAY** (`14-prg-O-win-canvas.png`).

Accepted chronological marks: `aebcdg`. Final board:

```text
X X O
X O F
O H I
```

F/H/I are remaining gray address labels, not marks. O occupies C–E–G, a complete diagonal; X has no winning line. The visible result agrees with the rules.

- Terminal `I` leaves the board/result unchanged (`15-prg-win-terminal-I-canvas.png`), byte-identical to the O-win canvas capture.
- `R` again restores an empty labeled board and human turn (`16-prg-win-replay-canvas.png`).

The screenshots visibly distinguish light-red X, blue O, and gray empty-cell labels on black. Immediate-X/busy timing was not independently accepted from these captures; waits were observation intervals, not measured neural response times.

## D64 interaction limitation and bounded retries

After the verified D64 autostart, the first A key-down reached the page and the actual canvas progressed to X at A and O at E. A host advertising interstitial then took focus before the key-up. `29-d64-after-ad-close.png` and its canvas show that legal opening response. The page event log contains only the initial trusted A key-down; subsequent attempted keys were directed to the ad iframe, not the emulator page.

The attempted first-run schedule was `A A B D I R`, followed by a compensating A key-up and attempted `A B D I R`; further focus attempts and a B probe, then a canvas click with another attempted `A B D I R`, still did not restore top-page keyboard delivery. Closing the ad visually, calling the existing input receiver's DOM focus method, and clicking the visible canvas were bounded unsuccessful recovery attempts: the top document's `activeElement` remained an iframe, and the board stayed at A/E. These are **not** accepted board inputs. Filenames `23`–`39` describe intended probes, not successful game states; in particular names containing `O-win`, `terminal`, `replay`, or `immediate-X-busy` in that range must not be interpreted as passed gates. The contact sheet explicitly shows that `39-d64-replay-focused-canvas.png` still contains A/E, not a replayed empty board.

A final clean-page D64 reload avoided the initial canvas click. `40-d64-retry-autostart.png` again shows the empty board, but the first A key-down again opened a host overlay, this time a Google survey (`41-d64-retry-A.png`). No survey answers were supplied. `d64-retry-key-events.json` again contains only A key-down. This retry did not establish keyboard acceptance. No further retry or D64 rebuild was attempted.

## Host errors, provenance, and exclusions

Both uploads raised the site's actual uncaught error:

```text
Uncaught ReferenceError: ajd is not defined
https://c64online.com/wp-content/kszk/revc64v2/vanillarevol.js?ver=16:28
```

Retained in `initial-errors.json`, `prg-errors.json`, `d64-errors.json`, and `d64-retry-errors.json`. Read-only inspection of the public upload handler showed `Module.loadFile` is called before the failing joystick setup, consistent with both formats launching despite the error. No host-script patch was applied. Error capture was installed before upload; it is not a complete historical DevTools-console transcript.

The run did not alter emulator RAM, CPU, model, ROM, speed configuration, or game artifacts to obtain a pass. It did not invoke internal model functions or inject expected marks. No wall-time performance, unthrottled/warp status, physical 1541 timing, full D64 gameplay, or physical-hardware acceptance is claimed. Source and frozen PRG/D64 bytes remain unchanged.
