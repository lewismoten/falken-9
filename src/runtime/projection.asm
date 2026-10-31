; Full learned attention projection and residual, after the actual board path.
projected = $6b40
attention_residual = $6c80
board_attention_block:
    jsr board_attention
    bcc +
    rts
+
    lda #0
    sta board_index
block_projection_row:
    lda board_index
    asl a
    tax
    lda attended_rows,x
    sta copy_source
    lda attended_rows+1,x
    sta copy_source+1
    ldy #0
block_copy_attended:
    lda (copy_source),y
    sta normalized,y
    iny
    cpy #32
    bne block_copy_attended
    lda #<projection_weight_data
    sta ptr_weight
    lda #>projection_weight_data
    sta ptr_weight+1
    lda #<projection_weight_exponents
    sta ptr_exponent
    lda #>projection_weight_exponents
    sta ptr_exponent+1
    lda #<query
    sta ptr_output
    lda #>query
    sta ptr_output+1
    jsr matrix8
    bcc +
    rts
+
    lda board_index
    asl a
    tax
    lda projected_rows,x
    sta copy_dest
    lda projected_rows+1,x
    sta copy_dest+1
    lda embedding_rows,x
    sta k_ptr
    lda embedding_rows+1,x
    sta k_ptr+1
    lda residual_rows,x
    sta q_ptr
    lda residual_rows+1,x
    sta q_ptr+1
    ldy #0
block_copy_projected:
    lda query,y
    sta (copy_dest),y
    iny
    cpy #32
    bne block_copy_projected
    ldy #0
block_residual_lane:
    clc
    .for i := 0, i < 4, i += 1
        lda query,y
        adc (k_ptr),y
        sta (q_ptr),y
        iny
    .endfor
    cpy #32
    bne block_residual_lane
    inc board_index
    lda board_index
    cmp #9
    beq block_done
    jmp block_projection_row
block_done:
    clc
    rts
embedding_rows:
    .for i := 0, i < 9, i += 1
        .word board_embedding+32*i
    .endfor
projected_rows:
    .for i := 0, i < 9, i += 1
        .word projected+32*i
    .endfor
residual_rows:
    .for i := 0, i < 9, i += 1
        .word attention_residual+32*i
    .endfor
