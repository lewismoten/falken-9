; Q11 exp-gap interpolation from the original unsigned16 resident LUT.
; Mathematically reduces (table[i]*(2048-r)+table[i+1]*r)/2048
; to (table[i]*(64-f)+table[i+1]*f)/64, gap=64*i+f.
lut_ptr = $6c
lut_fraction = $7014
exp_interpolate:
    cld
    lda operand+3
    bmi exp_bad
    ora operand+2
    bne exp_clamp
    lda operand+1
    bmi exp_clamp
    lda operand
    and #63
    sta lut_fraction
    ; index*2 = floor(gap/64)*2 = (gap>>5)&~1
    lda operand
    sta lut_ptr
    lda operand+1
    sta lut_ptr+1
    ldx #5
exp_index:
    lsr lut_ptr+1
    ror lut_ptr
    dex
    bne exp_index
    lda lut_ptr
    and #$fe
    clc
    adc #<exp_table
    sta lut_ptr
    lda lut_ptr+1
    adc #>exp_table
    sta lut_ptr+1
    jsr clear_acc
    jsr exp_load
    sec
    lda #64
    sbc lut_fraction
    sta weight
    lda #0
    sta weight+1
    jsr mac40
    clc
    lda lut_ptr
    adc #2
    sta lut_ptr
    bcc +
    inc lut_ptr+1
+
    jsr exp_load
    lda lut_fraction
    sta weight
    lda #0
    sta weight+1
    jsr mac40
    lda #6
    sta shift
    jmp scale40
exp_clamp:
    jsr clear_acc
    lda exp_table+1024
    sta acc
    lda exp_table+1025
    sta acc+1
    clc
    rts
exp_bad:
    sec
    rts
exp_load:
    ldy #0
    lda (lut_ptr),y
    sta operand
    iny
    lda (lut_ptr),y
    sta operand+1
    lda #0
    sta operand+2
    sta operand+3
    rts
