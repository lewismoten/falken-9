---
license: apache-2.0
language:
- en
tags:
- commodore-64
- tic-tac-toe
- mixture-of-experts
- custom-integer-runtime
- retrocomputing
- interpretability
---
# Falken-9

**A resident neural tic-tac-toe model designed for the Commodore 64.**
It powers **Crystal Palace 9**—the existing game and artwork, now with sound and
the Falken-9 model. The 5,195-byte model deployment packet retains attention, learned routing and two selected experts
per move. Every AI mark executes the network; there is no minimax or board-to-move
lookup hidden in the game.

**Emulator-tested only.** Physical C64, 1541 and SID compatibility and performance
are unverified. This is a custom integer runtime artifact, **not a Transformers
checkpoint, GGUF, Ollama model or hosted inference endpoint**.

![Crystal Palace 9 gameplay in native VICE, graphical011](assets/screenshots/falken-9-011-gameplay.png)

*Actual graphical011 emulator output, not a mockup. Crystal Palace 9 is the game;
Falken-9 is its model. Earlier `falcon-9` / FALCON-9 labels were a
historical spelling inconsistency, not a different model. The model name and repository slug are
Falken-9 and `falken-9`.*

## Downloads

| File | Purpose |
|---|---|
| [model.f9j](model.f9j) | Frozen F9J2 Q11/W16/A32 deployment packet; 5,195 bytes |
| [C64 PRG](c64/falken-9-c64.prg) | Standalone game with resident model, graphics, original SID music and effects |
| [C64 D64](c64/falken-9-c64.d64) | Disk image containing that same standalone game |

- **[Game guide and screenshots](c64/README.md)** — controls, loading, opening
  variety, audio, limitations and acceptance boundaries.
- **[Illustrated research report](report.md)** — exhaustive findings through
  study016, 39 selected indexed figures including the original weight and connection views,
  worked arithmetic, controls and counterexamples.
- **[GitHub source and probes](https://github.com/lewismoten/falken-9)** — assembly,
  training/verification tools, test scripts, research probes and authoritative art.
- **[Project website](https://lewismoten.github.io/falken-9/)** — browser launch
  helpers, disk inspection, downloads, game screenshots, music preview and HTML report.
- [Model description](model.json) · [Release manifest](manifest.json) ·
  [SHA-256 checksums](SHA256SUMS)

No code or probe archive is required merely to run the supplied PRG/D64. The
separate model packet is for the custom Falken-9 runtime described in the source
repository. Downloading it does not make it compatible with a general LLM loader.

The 5,195 bytes refer only to the model deployment packet; the complete game,
6502 inference runtime, graphics/audio and working memory require additional space.

## What the model computes

Nine board-square tokens encode occupancy, absolute position and side to move.
The width-8 integer network performs normalization, full-board attention,
projection/residual, flattened readout, learned routing, two of four expert MLPs
(hidden width 4), a merge and the final nine-score head.

A nonnegative score indicates membership in the complete optimal-move set;
score magnitude is not calibrated confidence or a categorical preference. Fixed
code validates history, canonicalizes the board, runs inference, restores the
**whole** approved set to original coordinates, masks occupied squares and
applies the declared tie priority. Offline minimax supplies training/audit labels,
never gameplay moves.

The frozen packet is `model-v1.0.0`, SHA-256:
`fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.

All 627 canonical boards pass the established assembled numerical checks. The
4,520-raw-board wrapper result is a composed verification, not 4,520 separately
executed native games. Recent interpretability, opponent and robustness studies
are host analyses with separately stated evidence boundaries.

## Why this model exists

Across Palace-9, Crystal-9 and Falken-9, the engineering question is:

> Can a learned attention-and-expert network execute on a C64, play correctly,
> and be small enough to investigate exhaustively?

Beating a specialized tic-tac-toe solver on speed is not the acceptance criterion.
The experiment concerns real learned computation on a constrained machine,
verified gameplay and a model small enough for systematic investigation.

The progression was [Palace-9](https://huggingface.co/lewismoten/palace-9)
(standard local-LLM/GGUF tooling), [Crystal-9](https://huggingface.co/lewismoten/crystal-9)
(a leaner custom model), and [Crystal Palace / CP64](https://github.com/lewismoten/crystal-palace)
(the original Crystal-9 model executing on a C64 with disk paging). Falken-9
instead trains for C64 arithmetic, live RAM and work per turn from the start.
These are distinct models, not interchangeable formats or successive exports of
the same weights. Users seeking GGUF/llama.cpp/Ollama should see Palace-9.

The complete model stays resident, with no per-turn model-data disk loads.
It powers **Crystal Palace 9**, retaining the game's artwork while adding sound
and a faster neural execution path.
In informal emulator observations, complete AI-vs-AI games lasted just over a minute,
with roughly ten-second thinking intervals and
visible activity: a quick curiosity to watch rather than a prolonged wait.
An earlier model-backed version took roughly 20 minutes. These are user-observed
emulator impressions across releases, not a controlled benchmark or a
physical-hardware speed claim.

### Decoded weights and tensor workflow

[![Original decoded model weights and their computation connections](assets/interpretability/publication-indexed/model-inspection/tensor-workflow.png)](assets/interpretability/model-inspection/tensor-workflow.svg)

*The original weight-map image, preserved byte-for-byte. Each cell represents
one decoded scalar parameter, not a bit or byte. Colors normalize per tensor;
all four expert banks are displayed, while only two selected experts execute
per inference. Static weights are not board-dependent activations.*

## What the research establishes

[![Measured same-connection support reverses across candidate squares](assets/interpretability/publication-indexed/study-004/square-paths.png)](report.md)

The network has context-dependent causal effects, but no isolated “fork expert”
or complete symbolic strategy circuit has been established. The report separates
learned computation from wrapper-provided symmetry, stored weights from dynamic
activity, full approved sets from selected ties, and individual from joint
parameter robustness. It also documents self-play's limited coverage, the
fixed-seed sampler's **nonuniform** opening frequencies, and exact outcomes
against a specifically defined random legal opponent. Self-play is not learning.

## Inspiration, credits and license

Inspired by *WarGames* (1983), Falken-9 is named for Dr. Stephen Falken, the
fictional researcher who developed Joshua, the AI on the WOPR war-simulation
computer. This project plays tic-tac-toe only; its war-room setting is fictional.
“Patient Calculations” is an original SID score, not a film melody.

Project by Lewis Moten, with Mercury Quill / Hermes Agent assistance.
First-party material is Apache-2.0 to the extent the contributors hold the
relevant rights; applicable artwork provenance and limitations are in
[NOTICE](NOTICE) and [LICENSE](LICENSE). No Commodore ROM, emulator, assembler,
third-party soundtrack or installed software environment is redistributed here.
