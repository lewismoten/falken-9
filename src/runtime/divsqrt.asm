; Generic signed40/unsigned32 nearest division; denominator preserved.
; Carry set on zero/out-of-contract (>32 bit) denominator.
denominator = $40
root = $45
remainder = $4a
trial = $50

round_mode = $55

divide40:
    lda #1
    sta round_mode
    jmp div_common
floor40:
    lda #0
    sta round_mode
div_common:
    cld
    lda denominator+4
    beq div_width_ok
    sec
    rts
div_width_ok:
    lda denominator
    ora denominator+1
    ora denominator+2
    ora denominator+3
    bne div_nonzero
    sec
    rts
div_nonzero:
    lda acc+4
    sta sign
    bpl div_abs
    jsr negate_acc
div_abs:
    lda round_mode
    beq div_prepare
    .for i := 0, i < 5, i += 1
        lda denominator+i
        sta mag+i
    .endfor
    lsr mag+4
    .for i := 3, i >= 0, i -= 1
        ror mag+i
    .endfor
    clc
    .for i := 0, i < 5, i += 1
        lda acc+i
        adc mag+i
        sta acc+i
    .endfor
div_prepare:
    lda #0
    .for i := 0, i < 5, i += 1
        sta remainder+i
    .endfor
    lda #40
    sta counter
div_loop:
    asl acc
    .for i := 1, i < 5, i += 1
        rol acc+i
    .endfor
    .for i := 0, i < 5, i += 1
        rol remainder+i
    .endfor
    ; compare by subtraction, commit only when no borrow
    sec
    .for i := 0, i < 5, i += 1
        lda remainder+i
        sbc denominator+i
        sta trial+i
    .endfor
    bcc div_skip
    .for i := 0, i < 5, i += 1
        lda trial+i
        sta remainder+i
    .endfor
    inc acc
div_skip:
    dec counter
    bne div_loop
    bit sign
    bpl div_done
    jsr negate_acc
div_done:
    clc
    rts

; Exact unsigned40 floor isqrt, twenty radix-4 steps. Consumes acc.
sqrt40:
    cld
    lda #0
    .for i := 0, i < 5, i += 1
        sta root+i
        sta remainder+i
    .endfor
    lda #20
    sta counter
sqrt_loop:
    ; Shift two most significant input bits into remainder.
    .for j := 0, j < 2, j += 1
        asl acc
        .for i := 1, i < 5, i += 1
            rol acc+i
        .endfor
        .for i := 0, i < 5, i += 1
            rol remainder+i
        .endfor
    .endfor
    .for i := 0, i < 5, i += 1
        lda root+i
        sta trial+i
    .endfor
    .for j := 0, j < 2, j += 1
        asl trial
        .for i := 1, i < 5, i += 1
            rol trial+i
        .endfor
    .endfor
    inc trial
    asl root
    .for i := 1, i < 5, i += 1
        rol root+i
    .endfor
    sec
    .for i := 0, i < 5, i += 1
        lda remainder+i
        sbc trial+i
        sta mag+i
    .endfor
    bcc sqrt_skip
    .for i := 0, i < 5, i += 1
        lda mag+i
        sta remainder+i
    .endfor
    inc root
sqrt_skip:
    dec counter
    beq sqrt_done
    jmp sqrt_loop
sqrt_done:
    clc
    rts
