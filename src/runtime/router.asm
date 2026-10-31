route_slot = $7398
route_scan = $7399
route_best = $739a
route_maximum = $739c
gate_exp = $73a0
board_router:
    jsr board_norm2
    bcc +
    rts
+
    lda #<norm2_output
    sta matrix_input_base
    lda #>norm2_output
    sta matrix_input_base+1
    lda #<router_weight_data
    sta ptr_weight
    lda #>router_weight_data
    sta ptr_weight+1
    lda #<router_weight_exponents
    sta ptr_exponent
    lda #>router_weight_exponents
    sta ptr_exponent+1
    lda #<router_bias_data
    sta matrix_bias
    lda #>router_bias_data
    sta matrix_bias+1
    lda #<router_scores
    sta ptr_output
    lda #>router_scores
    sta ptr_output+1
    lda #8
    sta matrix_input_count
    lda #EXPERT_COUNT
    sta matrix_output_count
    lda #2
    sta matrix_weight_step
    lda #16
    sta matrix_row_step
    lda #0
    sta matrix_weight_step+1
    sta matrix_row_step+1
    jsr matrix_variable
    bcc +
    rts
+
    jsr route_top2
    jmp route_gates

; Stable lower-index ties; signed32 comparisons include overflow correction.
route_top2:
    cld
    lda #0
    sta route_slot
route_select:
    lda #$ff
    sta route_best
    lda #0
    sta route_scan
route_candidate:
    lda route_slot
    beq +
    lda route_scan
    cmp routes
    beq route_skip
+
    lda route_best
    cmp #$ff
    beq route_update
    lda route_scan
    asl a
    asl a
    tax
    sec
    .for i := 0, i < 4, i += 1
        lda router_scores+i,x
        sbc route_maximum+i
    .endfor
    bvc +
    eor #$80
+
    bmi route_skip
    ; Reject equality, preserving the earlier index.
    lda router_scores,x
    cmp route_maximum
    bne route_update
    lda router_scores+1,x
    cmp route_maximum+1
    bne route_update
    lda router_scores+2,x
    cmp route_maximum+2
    bne route_update
    lda router_scores+3,x
    cmp route_maximum+3
    beq route_skip
route_update:
    lda route_scan
    sta route_best
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda router_scores+i,x
        sta route_maximum+i
    .endfor
route_skip:
    inc route_scan
    lda route_scan
    cmp #EXPERT_COUNT
    beq +
    jmp route_candidate
+
    ldx route_slot
    lda route_best
    sta routes,x
    inc route_slot
    lda route_slot
    cmp #2
    beq +
    jmp route_select
+
    clc
    rts

route_gates:
    lda routes
    asl a
    asl a
    tax
    .for i := 0, i < 4, i += 1
        lda router_scores+i,x
        sta route_maximum+i
    .endfor
    lda routes+1
    asl a
    asl a
    tax
    sec
    .for i := 0, i < 4, i += 1
        lda route_maximum+i
        sbc router_scores+i,x
        sta operand+i
    .endfor
    ; Signed score gap may exceed INT32. Clamp large unsigned gaps for exp.
    lda operand+3
    bpl +
    lda #0
    sta operand
    sta operand+2
    sta operand+3
    lda #$80
    sta operand+1
+
    jsr exp_interpolate
    bcc +
    rts
+
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta gate_exp+i
    .endfor
    clc
    lda acc
    adc #0
    sta denominator
    lda acc+1
    adc #$80
    sta denominator+1
    lda #0
    adc #0
    sta denominator+2
    lda #0
    sta denominator+3
    sta denominator+4
    ; Only compute floor p1; p0 receives the deterministic remainder.
    ldx #15
gate_shift:
    asl acc
    .for i := 1, i < 5, i += 1
        rol acc+i
    .endfor
    dex
    bne gate_shift
    jsr floor40
    bcc +
    rts
+
    .for i := 0, i < 4, i += 1
        lda acc+i
        sta gates+4+i
    .endfor
    sec
    lda #0
    sbc acc
    sta gates
    lda #$80
    sbc acc+1
    sta gates+1
    lda #0
    sta gates+2
    sta gates+3
    clc
    rts
