norm2_root = $7390
; Norm2 uses the same exact arithmetic, with independently guarded centered INT16.
norm2:
    jsr clear_acc
    lda #0
    sta lane
norm2_sum:
    lda lane
    asl a
    asl a
    tax
    jsr load_readout_operand
    jsr add_operand40
    inc lane
    lda lane
    cmp #8
    bne norm2_sum
    lda #3
    sta shift
    jsr scale40
    .for i := 0, i < 5, i += 1
        lda acc+i
        sta mean+i
    .endfor
    jsr clear_acc
    lda #0
    sta lane
norm2_squares:
    lda lane
    asl a
    asl a
    tax
    sec
    .for i := 0, i < 4, i += 1
        lda readout_gelu+i,x
        sbc mean+i
        sta operand+i
        sta centered+i,x
    .endfor
    lda operand
    sta weight
    lda operand+1
    sta weight+1
    ; Guard centered weight's INT16 representation even for corrupted inputs.
    lda #0
    bit operand+1
    bpl +
    lda #$ff
+
    cmp operand+2
    beq +
    sec
    rts
+
    cmp operand+3
    beq +
    sec
    rts
+
    jsr mac40
    bcc +
    rts
+
    inc lane
    lda lane
    cmp #8
    bne norm2_squares
    lda #3
    sta shift
    jsr scale40
    clc
    lda acc
    adc #42
    sta acc
    .for i := 1, i < 5, i += 1
        lda acc+i
        adc #0
        sta acc+i
    .endfor
    .for i := 0, i < 5, i += 1
        lda acc+i
        sta variance+i
    .endfor
    jsr sqrt40
    .for i := 0, i < 5, i += 1
        lda root+i
        sta denominator+i
        sta norm2_root+i
    .endfor
    lda #0
    sta lane
    jmp norm2_affine
norm2_bad:
    sec
    rts
norm2_affine:
    lda lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda centered+i,x
        sta acc+i
    .endfor
    lda #0
    bit acc+3
    bpl +
    lda #$ff
+
    sta acc+4
    ldx #11
norm2_shift:
    asl acc
    .for i := 1, i < 5, i += 1
        rol acc+i
    .endfor
    dex
    bne norm2_shift
    jsr divide40
    bcs norm2_bad
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta operand+i
    .endfor
    lda lane
    asl a
    tax
    lda norm2_weight_data,x
    sta weight
    lda norm2_weight_data+1,x
    sta weight+1
    jsr clear_acc
    jsr mac40
    bcs norm2_bad
    lda #11
    sta shift
    jsr scale40
    lda lane
    asl a
    tax
    lda norm2_bias_data,x
    sta weight
    lda norm2_bias_data+1,x
    sta weight+1
    jsr add_weight40
    jsr check_acc32
    bcs norm2_bad
    lda lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta norm2_output+i,x
    .endfor
    inc lane
    lda lane
    cmp #8
    beq norm2_done
    jmp norm2_affine
norm2_done:
    clc
    rts

load_readout_operand:
    .for i := 0, i < 4, i += 1
        lda readout_gelu+i,x
        sta operand+i
    .endfor
    rts
board_norm2:
    jsr board_readout
    bcc +
    rts
+
    lda #<readout_pre
    sta copy_source
    lda #>readout_pre
    sta copy_source+1
    lda #<readout_gelu
    sta copy_dest
    lda #>readout_gelu
    sta copy_dest+1
    lda #8
    sta gelu_count
    jsr gelu_vector
    bcc +
    rts
+
    jmp norm2

; source/dest use 16-bit progression, both preserved across scalar GELU.
gelu_count = $738a
gelu_vector:
    ldy #0
    .for i := 0, i < 4, i += 1
        lda (copy_source),y
        sta operand+i
        iny
    .endfor
    jsr gelu_interpolate
    bcc +
    rts
+
    ldy #0
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (copy_dest),y
        iny
    .endfor
    clc
    lda copy_source
    adc #4
    sta copy_source
    bcc +
    inc copy_source+1
+
    clc
    lda copy_dest
    adc #4
    sta copy_dest
    bcc +
    inc copy_dest+1
+
    dec gelu_count
    bne gelu_vector
    clc
    rts
