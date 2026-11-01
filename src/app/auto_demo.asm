; Continuous self-play is presentation orchestration, NOT learning.
; Every opening runs the real model. Later empty-board requests randomize
; only the actual inverse-mapped approved set, not BCE score magnitudes.
auto_pausing = $54a0
auto_pause_start = $54a1
auto_started = $54a3
auto_later = $54a4
auto_sampled = $54a5
auto_last_opening = $54a6
auto_opening_prng = $54a7
auto_elapsed = $54a8
auto_count = $54aa
auto_candidate_count = $54ab
auto_limit = $54ac
auto_attempts = $54ad
auto_candidates = $54b0

auto_session_reset:
    lda #0
    sta auto_pausing
    sta auto_started
    sta auto_later
    sta auto_sampled
    lda #$ff
    sta auto_last_opening
    lda #$a7
    sta auto_opening_prng
    rts

; Called ONLY after successful policy_request/restore_set in the app.
; Guards additionally reject scope leaks and contradictory empty-board state.
; Absolute private scratch only; C=1 means error, never a fallback square.
auto_resolve_opening:
    cld
    lda $7853                  ; mode
    bne auto_sampler_skip
    lda auto_later
    beq auto_sampler_skip
    lda $7809                  ; history_length
    bne auto_sampler_skip
    lda $7819                  ; terminal
    ora $7851                  ; neural_failed
    bne auto_sampler_bad
    lda #0
    sta auto_count
    sta auto_candidate_count
    ldx #0
auto_count_loop:
    lda $7810,x
    bne auto_sampler_bad
    lda $7840,x                ; actual original_set, never stored logits
    beq +
    cmp #1
    bne auto_sampler_bad
    inc auto_count
+
    inx
    cpx #9
    bne auto_count_loop
    lda auto_count
    beq auto_sampler_bad
    ldx #0
auto_collect_loop:
    lda $7840,x
    beq auto_collect_next
    cpx auto_last_opening
    bne auto_collect
    lda auto_count
    cmp #1
    bne auto_collect_next       ; no-repeat only when another approved option exists
auto_collect:
    txa
    ldy auto_candidate_count
    sta auto_candidates,y
    inc auto_candidate_count
auto_collect_next:
    inx
    cpx #9
    bne auto_collect_loop
    ldx auto_candidate_count
    cpx #1
    beq auto_single
    lda auto_limits,x
    sta auto_limit
    lda #9
    sta auto_attempts
auto_random_byte:
    lda auto_opening_prng
    bne +
    lda #$b7                   ; poisoned zero cannot lock the LFSR
+
    lsr a
    bcc +
    eor #$b8
+
    sta auto_opening_prng
    sec
    sbc #1                     ; maximal LFSR 1..255 -> 0..254
    cmp auto_limit
    bcc auto_reduce
    dec auto_attempts
    bne auto_random_byte
    jmp auto_sampler_bad       ; explicit finite guard, no manufactured move
auto_reduce:
    cmp auto_candidate_count
    bcc auto_pick
    sbc auto_candidate_count
    jmp auto_reduce
auto_single:
    lda #0
auto_pick:
    tax
    lda auto_candidates,x
    sta $7849                  ; selected_move
    clc
    adc #1
    sta $784d                  ; public move_result, 1..9
    lda #1
    sta auto_sampled
auto_sampler_skip:
    clc
    rts
auto_sampler_bad:
    lda #0
    sta $784d
    lda #$ff
    sta $7849
    sec
    rts
; Largest multiple of N <=255. Count geometry, not model-policy data.
auto_limits: .byte 0,255,254,255,252,255,252,252,248,252

auto_pause_begin:
    lda audio_ticks
    sta auto_pause_start
    lda audio_ticks+1
    sta auto_pause_start+1
    lda #1
    sta auto_pausing
    rts
; Foreground SEI makes the two-byte sample atomic. Frame service continues
; even when muted. Approx2sec: 100 PAL /120 NTSC, not host wall-clock timing.
auto_pause_due:
    lda auto_pausing
    beq auto_not_due
    sec
    lda audio_ticks
    sbc auto_pause_start
    sta auto_elapsed
    lda audio_ticks+1
    sbc auto_pause_start+1
    bne auto_due
    ldx #100
    lda audio_ntsc
    beq +
    ldx #120
+
    stx auto_elapsed+1
    lda auto_elapsed
    cmp auto_elapsed+1
    bcs auto_due
auto_not_due:
    clc
    rts
auto_due:
    sec
    rts
