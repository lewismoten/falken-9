; Full nine-token single-head attention; no causal mask in this board model.
board = $7020
board_index = $7030
copy_stage = $7031
att_i = $7032
att_j = $7033
att_lane = $7034
winner = $7035
maximum = $7040
exp_total = $7048
prob_total = $7050
exponents = $7060
copy_source = $70
copy_dest = $72
q_ptr = $74
k_ptr = $76
v_ptr = $78
score_ptr = $7a
prob_ptr = $7c
att_ptr = $7e
board_embedding = $6100
board_normalized = $6240
board_query = $6380
board_key = $64c0
board_value = $6600
attention_scores = $6740
attention_probs = $68a0
attended = $6a00

board_attention:
    cld
    lda #0
    sta token_side
    sta board_index
board_validate:
    ldx board_index
    lda board,x
    cmp #3
    bcc +
    sec
    rts
+
    cmp #0
    beq +
    inc token_side
+
    inc board_index
    lda board_index
    cmp #9
    bne board_validate
    lda token_side
    and #1
    sta token_side
    lda #0
    sta board_index
board_local:
    ldx board_index
    lda board,x
    sta token_occ
    stx token_pos
    jsr token_frontend
    bcc +
    rts
+
    lda #0
    sta copy_stage
board_copy:
    lda copy_stage
    asl a
    tax
    lda local_sources,x
    sta copy_source
    lda local_sources+1,x
    sta copy_source+1
    ldx board_index
    lda row_offset_low,x
    sta copy_dest
    lda row_offset_high,x
    sta copy_dest+1
    lda copy_stage
    asl a
    tax
    clc
    lda copy_dest
    adc local_destinations,x
    sta copy_dest
    lda copy_dest+1
    adc local_destinations+1,x
    sta copy_dest+1
    ldy #0
board_copy_bytes:
    lda (copy_source),y
    sta (copy_dest),y
    iny
    cpy #32
    bne board_copy_bytes
    inc copy_stage
    lda copy_stage
    cmp #5
    bne board_copy
    inc board_index
    lda board_index
    cmp #9
    beq board_scores_start
    jmp board_local
board_scores_start:
    lda #0
    sta att_i
board_score_row:
    lda att_i
    asl a
    tax
    lda q_rows,x
    sta q_ptr
    lda q_rows+1,x
    sta q_ptr+1
    lda score_rows,x
    sta score_ptr
    lda score_rows+1,x
    sta score_ptr+1
    lda #0
    sta att_j
board_score_col:
    lda att_j
    asl a
    tax
    lda k_rows,x
    sta k_ptr
    lda k_rows+1,x
    sta k_ptr+1
    jsr clear_acc
    lda #0
    sta att_lane
board_score_dot:
    lda att_lane
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda (q_ptr),y
        sta operand+i
        iny
    .endfor
    lda att_lane
    asl a
    asl a
    tay
    jsr load_key_weight
    bcc +
    rts
+
    jsr mac40
    bcc +
    rts
+
    inc att_lane
    lda att_lane
    cmp #8
    bne board_score_dot
    lda #11
    sta shift
    jsr scale40
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta operand+i
    .endfor
    jsr clear_acc
    lda #<11585
    sta weight
    lda #>11585
    sta weight+1
    jsr mac40
    bcc +
    rts
+
    lda #15
    sta shift
    jsr scale40
    jsr check_acc32
    bcc +
    rts
+
    lda att_j
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (score_ptr),y
        iny
    .endfor
    inc att_j
    lda att_j
    cmp #9
    beq board_score_next
    jmp board_score_col
board_score_next:
    inc att_i
    lda att_i
    cmp #9
    beq attention_softmax_start
    jmp board_score_row

attention_softmax_start:
    lda #0
    sta att_i
attention_softmax_row:
    lda att_i
    asl a
    tax
    lda score_rows,x
    sta score_ptr
    lda score_rows+1,x
    sta score_ptr+1
    lda prob_rows,x
    sta prob_ptr
    lda prob_rows+1,x
    sta prob_ptr+1
    lda attended_rows,x
    sta att_ptr
    lda attended_rows+1,x
    sta att_ptr+1
    ldy #0
    .for i := 0, i < 4, i += 1
        lda (score_ptr),y
        sta maximum+i
        iny
    .endfor
    lda #0
    sta winner
    lda #1
    sta att_j
attention_max:
    lda att_j
    asl a
    asl a
    tay
    sec
    .for i := 0, i < 4, i += 1
        lda (score_ptr),y
        sbc maximum+i
        iny
    .endfor
    bvc +
    eor #$80
+
    ora #0                         ; INY changed N after the last SBC.
    bmi attention_max_skip
    ; Equal values retain the first maximum, matching scalar argmax.
    lda att_j
    asl a
    asl a
    tay
    lda (score_ptr),y
    cmp maximum
    bne attention_new_max
    iny
    lda (score_ptr),y
    cmp maximum+1
    bne attention_new_max
    iny
    lda (score_ptr),y
    cmp maximum+2
    bne attention_new_max
    iny
    lda (score_ptr),y
    cmp maximum+3
    beq attention_max_skip
attention_new_max:
    lda att_j
    sta winner
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda (score_ptr),y
        sta maximum+i
        iny
    .endfor
attention_max_skip:
    inc att_j
    lda att_j
    cmp #9
    bne attention_max
    lda #0
    .for i := 0, i < 5, i += 1
        sta exp_total+i
        sta prob_total+i
    .endfor
    sta att_j
attention_exp:
    lda att_j
    asl a
    asl a
    tay
    sec
    .for i := 0, i < 4, i += 1
        lda maximum+i
        sbc (score_ptr),y
        sta operand+i
        iny
    .endfor
    jsr exp_interpolate
    bcc +
    rts
+
    lda att_j
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta exponents+i,x
    .endfor
    clc
    .for i := 0, i < 5, i += 1
        lda exp_total+i
        adc acc+i
        sta exp_total+i
    .endfor
    inc att_j
    lda att_j
    cmp #9
    bne attention_exp
    .for i := 0, i < 5, i += 1
        lda exp_total+i
        sta denominator+i
    .endfor
    lda #0
    sta att_j
attention_probability:
    lda att_j
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda exponents+i,x
        sta acc+i
    .endfor
    lda #0
    sta acc+4
    ldx #15
attention_p_shift:
    asl acc
    .for i := 1, i < 5, i += 1
        rol acc+i
    .endfor
    dex
    bne attention_p_shift
    jsr floor40
    bcc +
    rts
+
    clc
    .for i := 0, i < 5, i += 1
        lda prob_total+i
        adc acc+i
        sta prob_total+i
    .endfor
    lda att_j
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (prob_ptr),y
        iny
    .endfor
    inc att_j
    lda att_j
    cmp #9
    bne attention_probability
    sec
    lda #0
    sbc prob_total
    sta acc
    lda #$80
    sbc prob_total+1
    sta acc+1
    lda winner
    asl a
    asl a
    tay
    clc
    lda (prob_ptr),y
    adc acc
    sta (prob_ptr),y
    iny
    lda (prob_ptr),y
    adc acc+1
    sta (prob_ptr),y
    ; remainder <= 8 and winner p+remainder <=32768, high bytes stay zero.
    lda #0
    sta att_lane
attention_weighted_lane:
    jsr clear_acc
    lda #0
    sta att_j
attention_weighted_key:
    lda att_j
    asl a
    tax
    lda v_rows,x
    sta k_ptr
    lda v_rows+1,x
    sta k_ptr+1
    lda att_lane
    asl a
    asl a
    tay
    jsr load_key_weight
    bcc +
    rts
+
    lda att_j
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda (prob_ptr),y
        sta operand+i
        iny
    .endfor
    jsr mac40
    bcc +
    rts
+
    inc att_j
    lda att_j
    cmp #9
    bne attention_weighted_key
    lda #15
    sta shift
    jsr scale40
    jsr check_acc32
    bcc +
    rts
+
    lda att_lane
    asl a
    asl a
    tay
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (att_ptr),y
        iny
    .endfor
    inc att_lane
    lda att_lane
    cmp #8
    beq attention_next_row
    jmp attention_weighted_lane
attention_next_row:
    inc att_i
    lda att_i
    cmp #9
    beq attention_done
    jmp attention_softmax_row
attention_done:
    clc
    rts

; K/V fit INT16 over all 54 local combinations, checked again at use.
load_key_weight:
    lda (k_ptr),y
    sta weight
    iny
    lda (k_ptr),y
    sta weight+1
    lda #0
    bit weight+1
    bpl +
    lda #$ff
+
    sta oldsign
    iny
    lda (k_ptr),y
    cmp oldsign
    bne key_weight_bad
    iny
    lda (k_ptr),y
    cmp oldsign
    bne key_weight_bad
    clc
    rts
key_weight_bad:
    sec
    rts

local_sources: .word embedding,normalized,query,key,value
local_destinations: .word board_embedding,board_normalized,board_query,board_key,board_value
row_offset_low:
    .for i := 0, i < 9, i += 1
        .byte <(32*i)
    .endfor
row_offset_high:
    .for i := 0, i < 9, i += 1
        .byte >(32*i)
    .endfor
q_rows:
    .for i := 0, i < 9, i += 1
        .word board_query+32*i
    .endfor
k_rows:
    .for i := 0, i < 9, i += 1
        .word board_key+32*i
    .endfor
v_rows:
    .for i := 0, i < 9, i += 1
        .word board_value+32*i
    .endfor
score_rows:
    .for i := 0, i < 9, i += 1
        .word attention_scores+36*i
    .endfor
prob_rows:
    .for i := 0, i < 9, i += 1
        .word attention_probs+36*i
    .endfor
attended_rows:
    .for i := 0, i < 9, i += 1
        .word attended+32*i
    .endfor
