; Read-only Q capture under stock 901227-03 keyboard idle contract.
; KERNAL $eb42 leaves PRA=$7f, DDRA=$ff, DDRB=$00. Q connects PA7/PB6.
; No port/latch/DDR/timer/ICR writes or reads of read-to-clear registers.
; PRB reads pulse the CIA PC handshake output for one cycle (6526 behavior);
; no external handshake client is supported. PB6 timer output must be off.
; Reject non-stock column/direction state, including active joystick-2 pins.
; Joystick-1 uses PB0..4, not Q's PB6. Simultaneous key ghosting is not solved.
; Private state follows auto_candidates $54b0..$54b8; init by audio_init.
quit_active = $54b9
quit_pending = $54ba
quit_down = $54bb
quit_blocked = $54bc
quit_sample:
    lda $dc02
    cmp #$ff
    bne quit_sample_done
    lda $dc03
    bne quit_sample_done
    lda $dc00
    cmp #$7f
    bne quit_sample_done
    lda $dc01
    and #$40
    beq quit_sample_down
    lda #0
    sta quit_down
    rts
quit_sample_down:
    lda #1
    sta quit_down
    lda quit_active
    beq quit_sample_done
    lda #$80                   ; sign bit consumed without touching A at checkpoints
    sta quit_pending
quit_sample_done:
    rts

; Foreground SEI only, bounded stock queue compaction preserves unrelated keys.
; A held cancellation Q must not fall through to session-quit at restored title.
; Release is observed by raster sampling, never a wait loop or GETIN heuristic.
quit_release_guard:
    lda quit_blocked
    beq quit_guard_done
    lda $c6
    cmp #11
    bcs quit_guard_done
    ldx #0
    ldy #0
quit_filter_loop:
    cpx $c6
    bcs quit_filter_done
    cpx #10
    bcs quit_guard_done          ; unsupported corrupt queue: do not truncate it
    lda $0277,x
    and #$df
    cmp #$51
    beq quit_filter_next
    lda $0277,x
    sta $0277,y
    iny
quit_filter_next:
    inx
    bne quit_filter_loop
quit_filter_done:
    sty $c6
    lda quit_down
    bne quit_guard_done
    sta quit_blocked
quit_guard_done:
    rts
