; Original "Patient Calculations", Mercury Quill / Lewis Moten project.
; No imported score/player. Two restrained triangle voices, voice3 SFX.
; Included in separately assembled services ($5500..$5fff), never neural core.
; Stock ROM IRQ entry $ff48 already pushes A/X/Y. No ZP, CPU-port or CIA writes.
; State $5480..$54ef; model ends $544b. No cartridge/RS232 IRQ contract.
audio_enabled = $5480
audio_protected = $5481
audio_pending = $5482
audio_sfx_left = $5483
audio_sfx_priority = $5484
audio_frames = $5485
audio_period = $5486
audio_step = $5487
audio_ntsc = $5488
audio_old_irq = $5489
audio_old_mask = $548b
audio_installed = $548c
audio_ticks = $548d              ; wrapping 16-bit diagnostic only
audio_cooldown = $548f

; Caller SEI, stock ROM/I/O visible. SID/raster owned until session quit.
audio_init:
    ldx #$6f
    lda #0
-
    sta $5480,x
    dex
    bpl -
    sta $d404
    sta $d40b
    sta $d412
    sta $d417
    sta $d418
    lda $0314
    sta audio_old_irq
    lda $0315
    sta audio_old_irq+1
    lda $d01a
    sta audio_old_mask
    lda #<audio_irq
    sta $0314
    lda #>audio_irq
    sta $0315
    lda #250
    sta $d012
    lda $d011
    and #$7f
    sta $d011
    lda #1
    sta $d019
    ora audio_old_mask
    sta $d01a
    lda #1
    sta audio_enabled
    sta audio_installed
    sta audio_frames
    lda #31
    sta audio_step
    lda #30
    sta audio_period
    ; KERNAL PAL flag $02a6: 1 PAL / 0 NTSC, set by stock startup.
    lda $02a6
    bne +
    lda #1
    sta audio_ntsc
    lda #36
    sta audio_period
+
    lda #$58
    sta $d405
    lda #$48
    sta $d406
    lda #$68
    sta $d40c
    lda #$58
    sta $d40d
    lda #$02
    sta $d413
    lda #$24
    sta $d414
    lda #5
    sta $d418
    rts

; Preserve the hook-entry P for the saved KERNAL handler. Raster-only exits
; use the stock saved-register epilogue. CIA1 remains untouched outside work.
audio_irq:
    php
    cld
    lda $d019
    and #1
    beq audio_cia
    lda #1
    sta $d019
    jsr audio_tick
    lda audio_protected
    beq audio_irq_exit
    lda $dc0d                  ; acknowledge, never scan live neural ZP
    jmp audio_irq_exit
audio_cia:
    lda audio_protected
    beq audio_chain
    lda $dc0d
 audio_irq_exit:
    plp
    jmp $ea81                  ; PLA/TAY/PLA/TAX/PLA/RTI in stock ROM
 audio_chain:
    plp
    jmp (audio_old_irq)

; Foreground critical interval: only SID service, not KERNAL, can interrupt.
audio_work_begin:
    lda #1
    sta audio_protected
    cli
    rts
audio_work_end:
    sei
    lda #0
    sta audio_protected
    rts

; Atomic under foreground SEI. 1 think < 2 scroll < 3 nav < 4 X < 5 O.
; One pending event coalesces bursts; active higher priority cannot be preempted.
audio_event:
    cmp audio_pending
    bcc +
    sta audio_pending
+
    rts
audio_mark:
    lda $781a                  ; validate_history already flipped side
    eor #3
    clc
    adc #3
    jmp audio_event

audio_toggle:
    lda audio_enabled
    eor #1
    sta audio_enabled
    bne +
    jmp audio_silence
+
    lda #1
    sta audio_frames
    lda #5
    sta $d418
    rts
audio_silence:
    lda #0
    sta audio_pending
    sta audio_sfx_left
    sta audio_sfx_priority
    sta $d404
    sta $d40b
    sta $d412
    sta $d418
    rts
audio_stop:
    sei
    lda #0
    sta audio_enabled
    jsr audio_silence
    lda audio_installed
    beq +
    lda audio_old_irq
    sta $0314
    lda audio_old_irq+1
    sta $0315
    lda audio_old_mask
    sta $d01a
    lda #1
    sta $d019
    lda #0
    sta audio_installed
+
    rts

; Once per raster frame. Fixed bounded work; never pointers or shared UI state.
audio_tick:
    cld
    inc audio_ticks
    bne +
    inc audio_ticks+1
+
    lda audio_enabled
    bne +
    lda #0
    sta audio_pending
    rts
+
    lda audio_cooldown
    beq +
    dec audio_cooldown
+
    lda audio_sfx_left
    beq audio_pending_check
    dec audio_sfx_left
    bne audio_pending_check
    lda #0
    sta $d412
    sta audio_sfx_priority
 audio_pending_check:
    ldx audio_pending
    beq audio_music
    lda #0
    sta audio_pending
    cpx audio_sfx_priority
    bcc audio_music
    cpx #1
    bne audio_start_effect
    lda audio_cooldown
    bne audio_music
    lda audio_period
    sta audio_cooldown
 audio_start_effect:
    stx audio_sfx_priority
    lda #0
    sta $d412                 ; gate off at least one frame before new note
    lda #2
    sta audio_sfx_left
    ; New frequency/control latched, gate is raised next frame below.
    lda effect_note,x
    tay
    lda audio_ntsc
    beq +
    tya
    clc
    adc #32
    tay
+
    lda note_lo,y
    sta $d40e
    lda note_hi,y
    sta $d40f
    lda effect_ad,x
    sta $d413
    lda effect_sr,x
    sta $d414
    jmp audio_music
 audio_music:
    lda audio_sfx_left
    cmp #1
    bne +
    ldx audio_sfx_priority
    lda effect_control,x
    sta $d412
    lda effect_length,x
    sta audio_sfx_left
    ; priority now marked busy, don't re-trigger the rising edge each frame.
    ora #$80
    sta audio_sfx_left
+
    ; High bit distinguishes gated duration from the one-frame setup phase.
    lda audio_sfx_left
    cmp #$80
    bne +
    lda #0
    sta audio_sfx_left
    sta audio_sfx_priority
    sta $d412
+
    dec audio_frames
    lda audio_frames
    cmp #3
    bne +
    lda #$10
    sta $d404
    sta $d40b
+
    lda audio_frames
    bne audio_tick_done
    lda audio_period
    sta audio_frames
    inc audio_step
    lda audio_step
    and #31
    sta audio_step
    tax
    lda melody,x
    tay
    lda audio_ntsc
    beq +
    tya
    clc
    adc #32
    tay
+
    lda note_lo,y
    sta $d407
    lda note_hi,y
    sta $d408
    ldx audio_step
    lda bass,x
    tay
    lda audio_ntsc
    beq +
    tya
    clc
    adc #32
    tay
+
    lda note_lo,y
    sta $d400
    lda note_hi,y
    sta $d401
    lda #$11
    sta $d404
    sta $d40b
 audio_tick_done:
    rts
; E minor/suspended motion, original 32 measured steps. Note indexes from E2.
melody: .byte 12,19,22,19,17,19,24,19,12,19,22,26,24,19,17,14
        .byte 12,17,19,22,24,22,19,17,10,17,22,19,14,17,19,14
bass:   .byte 0,0,0,0,0,0,0,0,5,5,5,5,5,5,5,5
        .byte 0,0,0,0,0,0,0,0,10,10,10,10,7,7,7,7
effect_note:    .byte 0,7,24,26,12,19
effect_control: .byte 0,$11,$81,$11,$21,$11
effect_length:  .byte 0,2,2,3,6,9
effect_ad:      .byte 0,$02,$01,$02,$03,$13
effect_sr:      .byte 0,$02,$02,$03,$05,$06
    .include "notes.inc"
