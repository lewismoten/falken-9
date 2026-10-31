expert_slot = $73b0
expert_id = $73b1
expert_stage = $73b2
merge_lane = $73b3
full_forward:
    jsr board_router
    bcc +
    rts
+
    lda #0
    sta expert_slot
expert_slot_loop:
    ldx expert_slot
    lda routes,x
    cmp #EXPERT_COUNT
    bcc +
    sec
    rts
+
    sta expert_id
    lda #0
    sta expert_stage
    lda #<norm2_output
    sta matrix_input_base
    lda #>norm2_output
    sta matrix_input_base+1
    lda #8
    sta matrix_input_count
    lda #4
    sta matrix_output_count
    lda #8
    sta matrix_weight_step
    lda expert_slot
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<expert_hidden_pre
    sta ptr_output
    lda #>expert_hidden_pre
    adc #0
    sta ptr_output+1
    jsr expert_matrix
    bcc +
    rts
+
    lda expert_slot
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<expert_hidden_pre
    sta copy_source
    lda #>expert_hidden_pre
    adc #0
    sta copy_source+1
    lda expert_slot
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<expert_hidden
    sta copy_dest
    sta matrix_input_base
    lda #>expert_hidden
    adc #0
    sta copy_dest+1
    sta matrix_input_base+1
    lda #4
    sta gelu_count
    jsr gelu_vector
    bcc +
    rts
+
    lda #1
    sta expert_stage
    lda #4
    sta matrix_input_count
    lda #8
    sta matrix_output_count
    lda #16
    sta matrix_weight_step
    lda expert_slot
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #<expert_outputs
    sta ptr_output
    lda #>expert_outputs
    adc #0
    sta ptr_output+1
    jsr expert_matrix
    bcc +
    rts
+
    inc expert_slot
    lda expert_slot
    cmp #2
    beq +
    jmp expert_slot_loop
+
    jsr expert_merge
    bcc +
    rts
+
    jmp output_head

; Input-major source layout [expert,input,output], never dense-row assumed.
expert_matrix:
    lda expert_id
    asl a
    tax
    lda expert_stage
    bne expert_second_matrix
    lda w1_ptrs,x
    sta ptr_weight
    lda w1_ptrs+1,x
    sta ptr_weight+1
    lda b1_ptrs,x
    sta matrix_bias
    lda b1_ptrs+1,x
    sta matrix_bias+1
    lda e1_ptrs,x
    sta ptr_exponent
    lda e1_ptrs+1,x
    sta ptr_exponent+1
    jmp expert_matrix_ready
expert_second_matrix:
    lda w2_ptrs,x
    sta ptr_weight
    lda w2_ptrs+1,x
    sta ptr_weight+1
    lda b2_ptrs,x
    sta matrix_bias
    lda b2_ptrs+1,x
    sta matrix_bias+1
    lda e2_ptrs,x
    sta ptr_exponent
    lda e2_ptrs+1,x
    sta ptr_exponent+1
expert_matrix_ready:
    lda #2
    sta matrix_row_step
    lda #0
    sta matrix_row_step+1
    sta matrix_weight_step+1
    jmp matrix_variable
w1_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_w1_data+64*i
    .endfor
w2_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_w2_data+64*i
    .endfor
b1_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_b1_data+8*i
    .endfor
b2_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_b2_data+16*i
    .endfor
e1_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_w1_exponents+4*i
    .endfor
e2_ptrs:
    .for i := 0, i < EXPERT_COUNT, i += 1
        .word expert_w2_exponents+8*i
    .endfor

expert_merge:
    cld
    lda #0
    sta merge_lane
merge_loop:
    jsr clear_acc
    lda merge_lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda expert_outputs+i,x
        sta operand+i
    .endfor
    lda gates
    sta weight
    lda gates+1
    sta weight+1
    jsr mac_gate
    bcc +
    rts
+
    lda merge_lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda expert_outputs+32+i,x
        sta operand+i
    .endfor
    lda gates+4
    sta weight
    lda gates+5
    sta weight+1
    jsr mac_gate
    bcc +
    rts
+
    lda #15
    sta shift
    jsr scale40
    bcc +
    rts
+
    lda merge_lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda readout_gelu+i,x
        sta operand+i
    .endfor
    jsr add_operand40
    jsr check_acc32
    bcc +
    rts
+
    lda merge_lane
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta merged+i,x
    .endfor
    inc merge_lane
    lda merge_lane
    cmp #8
    beq +
    jmp merge_loop
+
    clc
    rts
; unsigned gates <=32768; 32768 uses two exact signed multiplications.
mac_gate:
    lda weight+1
    bpl +
    cmp #$80
    bne gate_invalid
    lda weight
    bne gate_invalid
    lda #$40
    sta weight+1
    jsr mac40
    bcc +
    rts
+
    jmp mac40
gate_invalid:
    sec
    rts

output_head:
    lda #<merged
    sta matrix_input_base
    lda #>merged
    sta matrix_input_base+1
    lda #<output_weight_data
    sta ptr_weight
    lda #>output_weight_data
    sta ptr_weight+1
    lda #<output_weight_exponents
    sta ptr_exponent
    lda #>output_weight_exponents
    sta ptr_exponent+1
    lda #<output_bias_data
    sta matrix_bias
    lda #>output_bias_data
    sta matrix_bias+1
    lda #<logits
    sta ptr_output
    lda #>logits
    sta ptr_output+1
    lda #8
    sta matrix_input_count
    lda #9
    sta matrix_output_count
    lda #2
    sta matrix_weight_step
    lda #16
    sta matrix_row_step
    lda #0
    sta matrix_weight_step+1
    sta matrix_row_step+1
    jmp matrix_variable
