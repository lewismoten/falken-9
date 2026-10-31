; Signed INT32 -> INT16 requantization, nearest/ties-away, then saturation.
; Input $e0..$e3 INT32 LE, $e4 shift 0..31. Inputs preserved.
; Output $e5..$e6 INT16 LE; carry=1 iff saturated. CLD on entry.
; Scratch $e7..$ec; A/X/P clobbered. Caller owns addresses and valid shift.
; Standalone fixed-address experiment; not a linked model implementation.
* = $2000
entry:
    cld
    ldx #0
copy:
    lda $e0,x
    sta $e8,x
    inx
    cpx #4
    bne copy
    lda $e3
    and #$80
    sta $e7
    beq shift_setup
    sec
    lda #0
    sbc $e8
    sta $e8
    lda #0
    sbc $e9
    sta $e9
    lda #0
    sbc $ea
    sta $ea
    lda #0
    sbc $eb
    sta $eb
shift_setup:
    lda $e4
    sta $ec
    beq check_range
shift_loop:
    lsr $eb
    ror $ea
    ror $e9
    ror $e8
    dec $ec
    bne shift_loop
    bcc check_range
    inc $e8
    bne check_range
    inc $e9
    bne check_range
    inc $ea
    bne check_range
    inc $eb
check_range:
    lda $eb
    ora $ea
    bne overflow
    lda $e7
    bne negative_range
    lda $e9
    bmi saturate_positive
    lda $e8
    sta $e5
    lda $e9
    sta $e6
    clc
    rts
negative_range:
    lda $e9
    cmp #$80
    bcc negate
    bne saturate_negative
    lda $e8
    bne saturate_negative
negate:
    sec
    lda #0
    sbc $e8
    sta $e5
    lda #0
    sbc $e9
    sta $e6
    clc
    rts
overflow:
    lda $e7
    bne saturate_negative
saturate_positive:
    lda #$ff
    sta $e5
    lda #$7f
    sta $e6
    sec
    rts
saturate_negative:
    lda #0
    sta $e5
    lda #$80
    sta $e6
    sec
    rts
end:
.cerror * > $2100, "requantization kernel exceeds reserved page"
