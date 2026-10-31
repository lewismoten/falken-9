; Original resident-byte embedding -> integer LayerNorm -> real Q/K/V.
; Local ABI inputs are occupancy 0..2, absolute square 0..8, side 0..1.
; This is not symmetry canonicalization or a complete board policy.
ptr_occ = $60
ptr_pos = $62
ptr_side = $64
ptr_weight = $66
ptr_exponent = $68
ptr_output = $6a
embedding = $6000
normalized = $6020
query = $6040
key = $6060
value = $6080
centered = $60a0
mean = $60c0
variance = $60c8
norm_root = $60d0
token_occ = $7000
token_pos = $7001
token_side = $7002
lane = $7010
matrix_row = $7011
matrix_col = $7012
matrix_stage = $7013

token_frontend:
    cld
    lda token_occ
    cmp #3
    bcs frontend_invalid
    lda token_pos
    cmp #9
    bcs frontend_invalid
    lda token_side
    cmp #2
    bcs frontend_invalid
    ; Three row pointers into the original INT16 embedding parameters.
    lda token_occ
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<occupancy_weight_data
    sta ptr_occ
    lda #>occupancy_weight_data
    adc #0
    sta ptr_occ+1
    lda token_pos
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<position_data
    sta ptr_pos
    lda #>position_data
    adc #0
    sta ptr_pos+1
    lda token_side
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<side_weight_data
    sta ptr_side
    lda #>side_weight_data
    adc #0
    sta ptr_side+1
    lda #0
    sta lane
    jmp embedding_loop
frontend_invalid:
    sec
    rts
embedding_loop:
    jsr clear_acc
    lda lane
    asl a
    tay
    lda (ptr_occ),y
    sta weight
    iny
    lda (ptr_occ),y
    sta weight+1
    jsr add_weight40
    lda lane
    asl a
    tay
    lda (ptr_pos),y
    sta weight
    iny
    lda (ptr_pos),y
    sta weight+1
    jsr add_weight40
    lda lane
    asl a
    tay
    lda (ptr_side),y
    sta weight
    iny
    lda (ptr_side),y
    sta weight+1
    jsr add_weight40
    lda lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta embedding+i,x
    .endfor
    inc lane
    lda lane
    cmp #8
    bne embedding_loop
    jsr norm1
    bcc +
    rts
+
    lda #0
    sta matrix_stage
frontend_matrix:
    lda matrix_stage
    asl a
    tax
    lda matrix_weights,x
    sta ptr_weight
    lda matrix_weights+1,x
    sta ptr_weight+1
    lda matrix_exponents,x
    sta ptr_exponent
    lda matrix_exponents+1,x
    sta ptr_exponent+1
    lda matrix_outputs,x
    sta ptr_output
    lda matrix_outputs+1,x
    sta ptr_output+1
    jsr matrix8
    bcc +
    rts
+
    inc matrix_stage
    lda matrix_stage
    cmp #3
    bne frontend_matrix
    clc
    rts
matrix_weights: .word query_weight_data,key_weight_data,value_weight_data
matrix_exponents: .word query_weight_exponents,key_weight_exponents,value_weight_exponents
matrix_outputs: .word query,key,value

; Every local embedding is a sum of three INT16 parameters. For this pinned
; artifact max magnitude <= 5030+1729+4719=11478; centered <=22956.
; Thus exact square multiplication fits signed16 weight, square sum <2**32.
norm1:
    jsr clear_acc
    lda #0
    sta lane
norm_sum:
    lda lane
    asl a
    asl a
    tax
    jsr load_embedding_operand
    jsr add_operand40
    inc lane
    lda lane
    cmp #8
    bne norm_sum
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
norm_squares:
    lda lane
    asl a
    asl a
    tax
    sec
    .for i := 0, i < 4, i += 1
        lda embedding+i,x
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
    bne norm_squares
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
        sta norm_root+i
    .endfor
    lda #0
    sta lane
    jmp norm_affine
norm_bad:
    sec
    rts
norm_affine:
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
norm_shift:
    asl acc
    .for i := 1, i < 5, i += 1
        rol acc+i
    .endfor
    dex
    bne norm_shift
    jsr divide40
    bcs norm_bad
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta operand+i
    .endfor
    lda lane
    asl a
    tax
    lda norm1_weight_data,x
    sta weight
    lda norm1_weight_data+1,x
    sta weight+1
    jsr clear_acc
    jsr mac40
    bcs norm_bad
    lda #11
    sta shift
    jsr scale40
    lda lane
    asl a
    tax
    lda norm1_bias_data,x
    sta weight
    lda norm1_bias_data+1,x
    sta weight+1
    jsr add_weight40
    jsr check_acc32
    bcs norm_bad
    lda lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta normalized+i,x
    .endfor
    inc lane
    lda lane
    cmp #8
    beq norm_done
    jmp norm_affine
norm_done:
    clc
    rts

; 8x8 actual INT32 activation x INT16 weight, signed40 partial sums,
; original per-row exponents, exact nearest rounding. C=1 on rejected width.
matrix8:
    lda #0
    sta matrix_row
matrix_row_loop:
    jsr clear_acc
    lda #0
    sta matrix_col
matrix_col_loop:
    lda matrix_col
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda normalized+i,x
        sta operand+i
    .endfor
    ldy #0
    lda (ptr_weight),y
    sta weight
    iny
    lda (ptr_weight),y
    sta weight+1
    jsr mac40
    bcc +
    rts
+
    clc
    lda ptr_weight
    adc #2
    sta ptr_weight
    bcc +
    inc ptr_weight+1
+
    inc matrix_col
    lda matrix_col
    cmp #8
    bne matrix_col_loop
    ldy matrix_row
    lda (ptr_exponent),y
    bmi +
    ; Pinned frontend matrices only have negative exponents.
    sec
    rts
+
    eor #$ff
    clc
    adc #1
    sta shift
    jsr scale40
    bcc +
    rts
+
    jsr check_acc32
    bcc +
    rts
+
    lda matrix_row
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (ptr_output),y
        iny
    .endfor
    inc matrix_row
    lda matrix_row
    cmp #8
    beq matrix_done
    jmp matrix_row_loop
matrix_done:
    clc
    rts

clear_acc:
    lda #0
    .for i := 0, i < 5, i += 1
        sta acc+i
    .endfor
    rts
load_embedding_operand:
    .for i := 0, i < 4, i += 1
        lda embedding+i,x
        sta operand+i
    .endfor
    rts
add_operand40:
    lda #0
    bit operand+3
    bpl +
    lda #$ff
+
    sta product+4
    clc
    .for i := 0, i < 4, i += 1
        lda acc+i
        adc operand+i
        sta acc+i
    .endfor
    lda acc+4
    adc product+4
    sta acc+4
    rts
add_weight40:
    lda #0
    bit weight+1
    bpl +
    lda #$ff
+
    sta product+2
    sta product+3
    sta product+4
    lda weight
    sta product
    lda weight+1
    sta product+1
    clc
    .for i := 0, i < 5, i += 1
        lda acc+i
        adc product+i
        sta acc+i
    .endfor
    rts
check_acc32:
    lda #0
    bit acc+3
    bpl +
    lda #$ff
+
    cmp acc+4
    beq +
    sec
    rts
+
    clc
    rts
