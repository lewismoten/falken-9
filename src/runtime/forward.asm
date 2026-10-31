; Four-expert Q11 W16 downstream kernels. Original E9 build excludes this.
    .include "gelu.asm"
    .include "norm2.asm"
    .include "router.asm"
    .include "experts.asm"
readout_pre = $7200
readout_gelu = $7220
norm2_output = $7240
router_scores = $7260
routes = $7280
gates = $7284
expert_hidden_pre = $7290
expert_hidden = $72b0
expert_outputs = $72d0
merged = $7310
logits = $7330
matrix_input_base = $7380
matrix_weight_base = $7382
matrix_input_count = $7384
matrix_output_count = $7385
matrix_weight_step = $7386
matrix_row_step = $7388
matrix_bias = $6e
; copy_source is the advancing input pointer, not an 8-bit byte offset.
board_readout:
    jsr board_attention_block
    bcc +
    rts
+
readout_only:
    lda #<attention_residual
    sta matrix_input_base
    lda #>attention_residual
    sta matrix_input_base+1
    lda #<readout_weight_data
    sta ptr_weight
    lda #>readout_weight_data
    sta ptr_weight+1
    lda #<readout_weight_exponents
    sta ptr_exponent
    lda #>readout_weight_exponents
    sta ptr_exponent+1
    lda #<readout_bias_data
    sta matrix_bias
    lda #>readout_bias_data
    sta matrix_bias+1
    lda #<readout_pre
    sta ptr_output
    lda #>readout_pre
    sta ptr_output+1
    lda #72
    sta matrix_input_count
    lda #8
    sta matrix_output_count
    lda #2
    sta matrix_weight_step
    lda #144
    sta matrix_row_step
    lda #0
    sta matrix_weight_step+1
    sta matrix_row_step+1
    jmp matrix_variable

; Row-major or input-major W16, with explicit strides; mandatory INT16 bias.
; Positive/zero exponents are rejected rather than silently mis-scaled.
matrix_variable:
    lda #0
    sta matrix_row
matrix_variable_row:
    lda ptr_weight
    sta matrix_weight_base
    lda ptr_weight+1
    sta matrix_weight_base+1
    lda matrix_input_base
    sta copy_source
    lda matrix_input_base+1
    sta copy_source+1
    jsr clear_acc
    lda #0
    sta matrix_col
matrix_variable_col:
    ldy #0
    .for i := 0, i < 4, i += 1
        lda (copy_source),y
        sta operand+i
        iny
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
    lda copy_source
    adc #4
    sta copy_source
    bcc +
    inc copy_source+1
+
    clc
    lda ptr_weight
    adc matrix_weight_step
    sta ptr_weight
    lda ptr_weight+1
    adc matrix_weight_step+1
    sta ptr_weight+1
    inc matrix_col
    lda matrix_col
    cmp matrix_input_count
    bne matrix_variable_col
    ldy matrix_row
    lda (ptr_exponent),y
    bmi +
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
    lda matrix_row
    asl a
    tay
    lda (matrix_bias),y
    sta weight
    iny
    lda (matrix_bias),y
    sta weight+1
    jsr add_weight40
    jsr check_acc32
    bcc +
    rts
+
    ldy #0
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta (ptr_output),y
        iny
    .endfor
    clc
    lda ptr_output
    adc #4
    sta ptr_output
    bcc +
    inc ptr_output+1
+
    clc
    lda matrix_weight_base
    adc matrix_row_step
    sta ptr_weight
    lda matrix_weight_base+1
    adc matrix_row_step+1
    sta ptr_weight+1
    inc matrix_row
    lda matrix_row
    cmp matrix_output_count
    beq +
    jmp matrix_variable_row
+
    clc
    rts
