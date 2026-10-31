; Signed Q11 GELU table interpolation, negative entries sign-extended.
; operand INT32 -> acc INT40; tails x<-8S =>0, x>8S =>x.
gelu_interpolate:
    cld
    lda operand+3
    bmi gelu_negative
    ora operand+2
    beq +
    jmp gelu_identity
+
    lda operand+1
    cmp #$40
    bcc +
    jmp gelu_identity
+
    jmp gelu_in_range
gelu_negative:
    lda operand+3
    cmp #$ff
    beq +
    jmp gelu_zero
+
    lda operand+2
    cmp #$ff
    beq +
    jmp gelu_zero
+
    lda operand+1
    cmp #$c0
    bcs +
    jmp gelu_zero
+
gelu_in_range:
    lda operand
    and #63
    sta lut_fraction
    lda operand
    sta lut_ptr
    clc
    lda operand+1
    adc #$40
    sta lut_ptr+1
    ldx #5
gelu_index:
    lsr lut_ptr+1
    ror lut_ptr
    dex
    bne gelu_index
    lda lut_ptr
    and #$fe
    clc
    adc #<gelu_table
    sta lut_ptr
    lda lut_ptr+1
    adc #>gelu_table
    sta lut_ptr+1
    jsr clear_acc
    jsr gelu_load
    sec
    lda #64
    sbc lut_fraction
    sta weight
    lda #0
    sta weight+1
    jsr mac40
    bcc +
    rts
+
    clc
    lda lut_ptr
    adc #2
    sta lut_ptr
    bcc +
    inc lut_ptr+1
+
    jsr gelu_load
    lda lut_fraction
    sta weight
    lda #0
    sta weight+1
    jsr mac40
    bcc +
    rts
+
    lda #6
    sta shift
    jmp scale40
gelu_load:
    ldy #0
    lda (lut_ptr),y
    sta operand
    iny
    lda (lut_ptr),y
    sta operand+1
    lda #0
    bit operand+1
    bpl +
    lda #$ff
+
    sta operand+2
    sta operand+3
    rts
gelu_identity:
    .for i := 0, i < 4, i += 1
        lda operand+i
        sta acc+i
    .endfor
    lda #0
    sta acc+4
    clc
    rts
gelu_zero:
    jsr clear_acc
    clc
    rts
