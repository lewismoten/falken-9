; No board-policy tables: these eight fixed permutations are geometry only.
candidate_board = $7820
selected_transform = $7830
original_set = $7840
selected_move = $7849
transform_offset = $784a
transform_index = $784b
source_index = $784c
move_result = $784d             ; public 1..9 square, 0 invalid/no result
canonicalize_board:
    cld
    lda #0
    sta transform_offset
    sta transform_index
    ldx #8
-
    lda #3
    sta board,x
    dex
    bpl -
canonical_transform_loop:
    lda #0
    sta source_index
canonical_build:
    ldx source_index
    txa
    clc
    adc transform_offset
    tay
    lda transforms,y
    tay
    lda original_board,x
    sta candidate_board,y
    inc source_index
    lda source_index
    cmp #9
    bne canonical_build
    ldx #0
canonical_compare:
    lda candidate_board,x
    cmp board,x
    bcc canonical_keep
    bne canonical_next
    inx
    cpx #9
    bne canonical_compare
    beq canonical_next     ; retain first transform on equal board
canonical_keep:
    ldx #0
canonical_copy:
    lda candidate_board,x
    sta board,x
    txa
    clc
    adc transform_offset
    tay
    lda transforms,y
    sta selected_transform,x
    inx
    cpx #9
    bne canonical_copy
canonical_next:
    lda transform_offset
    clc
    adc #9
    sta transform_offset
    inc transform_index
    lda transform_index
    cmp #8
    bne canonical_transform_loop
    clc
    rts
; Canonical signed32 logits >=0 represent the COMPLETE set.
; Gather via original->canonical permutation, mask original occupied cells,
; then choose only after the whole original-coordinate set is restored.
restore_set:
    lda #0
    sta move_result
    ldx #0
restore_loop:
    lda #0
    sta original_set,x
    lda original_board,x
    bne restore_next
    lda selected_transform,x
    asl a
    asl a
    tay
    lda logits+3,y
    bmi restore_next
    lda #1
    sta original_set,x
restore_next:
    inx
    cpx #9
    bne restore_loop
    ldy #0
restore_tie:
    ldx tie_order,y
    lda original_set,x
    bne restore_found
    iny
    cpy #9
    bne restore_tie
    lda #$ff
    sta selected_move
    sec
    rts
restore_found:
    stx selected_move
    txa
    clc
    adc #1
    sta move_result
    clc
    rts
; Production entry ALWAYS executes the complete accepted neural forward.
; C=1 also for terminal input: no fallback and no NN for invalid histories.
policy_request:
    lda #0
    sta move_result
    jsr validate_history
    bcs policy_bad
    lda terminal
    bne policy_bad
    jsr canonicalize_board
    jsr full_forward
    bcs policy_bad
    jmp restore_set
policy_bad:
    sec
    rts
transforms:
    .byte 0,1,2,3,4,5,6,7,8
    .byte 2,5,8,1,4,7,0,3,6
    .byte 8,7,6,5,4,3,2,1,0
    .byte 6,3,0,7,4,1,8,5,2
    .byte 2,1,0,5,4,3,8,7,6
    .byte 8,5,2,7,4,1,6,3,0
    .byte 6,7,8,3,4,5,0,1,2
    .byte 0,3,6,1,4,7,2,5,8
tie_order:
    .byte 4,1,3,5,7,2,6,8,0
