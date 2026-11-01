# Original SID audio: Patient Calculations

The score and event data in `src/app/sid_audio.asm` were composed for this project. No film/game melody or third-party SID tune is copied or redistributed. Existing first-party Apache-2.0/NOTICE terms apply to the contribution, with existing artwork exceptions unchanged.

Two quiet triangle voices provide a slow minor/suspended melody and sustained bass pulse. Voice three is reserved for bounded SFX: a changed title selection, an actual INFO scroll, a decorative thinking checkpoint, and distinct X/O mark timbres after visible successful placement. They convey activity, not strategy. Pending events have explicit priority; the driver releases gates and drops stale events during mute. Invalid/no-op actions do not manufacture successful-mark effects. Session quit silences all voices and restores the saved interrupt configuration. M is optional mute/unmute, not a startup prompt.

## Interrupt and memory contract

This is a narrow stock-ROM/no-cartridge contract, not a generic IRQ framework. VIC raster line 250 owns the SID service. CIA timers are not reassigned, reloaded or reconfigured. Initialization saves the VIC IRQ mask and KERNAL IRQ vector; shutdown restores those. The raster compare is owned for this session, not saved/restored: the tested stock startup has no preexisting raster-IRQ client. This is not support for arbitrary prior raster handlers. The saved vector remains the normal KERNAL owner outside protected work.

The stock KERNAL hardware IRQ entry at $ff48 has already saved A/X/Y before entering the installed $0314 vector. The service is ZP-free, CLD-protected, absolute-state-only, and preserves its entry registers; RTI restores the interrupted flags. Protected compute suppresses the KERNAL keyboard/clock scanner and acknowledges pending CIA status so that live neural ZP cannot be corrupted. Outside compute, the original KERNAL route is retained. No graphics/UI pointers, input scans, CIA timers, CPU port or model memory are mutated by the SID service. NMI ownership is not changed.

UI banking uses $36 and normal banking $37, both retaining KERNAL and I/O visibility. The application brackets synchronous compute and view composition with the protected flag and restores its saved neural/KERNAL ZP/port contract. The immutable core is not patched to add calls or interrupts. Audio code and original score live with separately relocated orchestration at $5500..$5bc4; shared private service state occupies the reserved $5480..$54ff interval, with distinct audio, activity and opening-sampler allocations. The frozen model ends before this interval. See assembled labels rather than treating that range as unallocated headroom.

PAL/NTSC are detected through the standard startup flag; separate generated frequency words and 30/36-frame note divisions keep the intended slow tempo. The result hold uses 100/120 audio-service ticks even when muted. The tests cover both timing tables; native VICE runs cover PAL and NTSC. Arbitrary ROM replacements, IRQ extensions and physical hardware remain unverified.

## Evidence scope and cost

The final executable passes all 627 numerical stage/route/logit cases without asynchronous interrupts. A separate adversarial suite executes stock-ROM IRQ entry/exit at 11,875 interleavings over 24 representative boards and both port values. Maximum observed complete protected service cost is 321 CPU cycles; it is a measured bound over these cases, not every imaginable machine extension. The assembled SID module/score/frequency tables occupy 820 bytes; the complete relocated service region uses 1,733 bytes, with 128 bytes reserved for all service state. Per-frame overhead is added work, not a claimed inference speedup. State, code/table ranges, stack low-water and write audits are retained in candidate evidence.

Actual x64/MOS8580 WAV output, not a host imitation, spans idle music, title/INFO SFX, a complete human/model response and distinct mark sounds. Both PAL and NTSC PCM are non-silent with zero samples at the clipping extrema. Native trace records include hundreds of SID-service calls inside the full forward, changing score registers and the actual event/mark-frequency writes. These are numeric PCM/register checks, not a claim that a person heard or approved the composition. Private captures and full monitor traces are deliberately excluded from public upload trees.

Native stock-ROM lifecycle and three-game continuous-auto tests run with the audio IRQ enabled. The 4,520-wrapper and long composed-auto tests use cached numerical fixtures and do not establish exhaustive interrupt timing. The work-based meter calibration was rerun against this executable; its existing fill table remained equal. Raster-service cadence and variable callback-light cadence are different quantities.

## Primary references

- Commodore 64 Programmer's Reference Guide: VIC raster/IRQ, SID frequency, ADSR/gate and CIA interrupt-control descriptions. Original manual mirror: https://www.zimmers.net/anonftp/pub/cbm/manuals/c64/c64-programmers-reference-guide.txt
- VICE primary sound/monitor implementation and manual: https://github.com/VICE-Team/svn-mirror/tree/main/vice/src and https://vice-emu.sourceforge.io/vice_6.html

These references inform the design; actual stock-ROM execution and final-binary traces establish the tested contract. ROM bytes are not redistributed.
