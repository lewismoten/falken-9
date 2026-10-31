; Fixed-screen UI. No LOAD, CHROUT, host callback, or policy fallback.
saved_zp = $7880                ; KERNAL-owned $20..$7f during NN (96 bytes)
pending_key = $7850
neural_failed = $7851
app_start:
    sei
    cld
    ldx #$ff
    txs
    ; BASIC SYS overlays $0801..$080c. Restore the ORIGINAL core before use.
    ldx #15
-
    lda core_backup,x
    sta $0800,x
    dex
    bpl -
    lda $dd00
    ora #3
    sta $dd00
    lda #$ff
    sta $cc                    ; KERNAL cursor blink off for fixed screen
    lda #$14
    sta $d018
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #0
    sta $d020
    sta $d021
    ldx #0
-
    .for i := 0, i < 4, i += 1
        lda screen_template+$100*i,x
        sta $0400+$100*i,x
        lda #1
        sta $d800+$100*i,x
    .endfor
    inx
    bne -
new_game:
    lda #0
    sta history_length
    sta neural_failed
    sta move_result
    jsr validate_history
    jsr draw_board
    lda #0
    jsr draw_status
input_wait:
    ; Let stock KERNAL IRQ scan keyboard only outside model execution.
    cli
    jsr $ffe4
    sei
    cld
    cmp #0
    beq input_wait
    cmp #$52
    beq new_game
    cmp #$72
    beq new_game
    sta pending_key
    lda #0
    sta move_result
    lda terminal
    ora neural_failed
    bne input_wait
    lda pending_key
    cmp #1
    bcc invalid_key
    cmp #10
    bcc key_screen_code
    cmp #$31
    bcc invalid_key
    cmp #$3a
    bcc key_digit
    cmp #$41
    bcc invalid_key
    cmp #$4a
    bcc key_uppercase
    cmp #$61
    bcc invalid_key
    cmp #$6a
    bcs invalid_key
    sec
    sbc #$61
    jmp accept_square
key_digit:
    sec
    sbc #$31
    jmp accept_square
key_uppercase:
    sec
    sbc #$41
    jmp accept_square
key_screen_code:
    sec
    sbc #1
accept_square:
    tax
    lda original_board,x
    bne invalid_key
    txa
    clc
    adc #$61
    ldx history_length
    sta history,x
    inc history_length
    jsr validate_history
    bcs game_error
    jsr draw_board             ; immediate human X BEFORE any inference
    lda terminal
    bne game_terminal
    lda #2
    jsr draw_status
    ; Protect KERNAL workspace from all neural scratch writes; IRQ stays off.
    ldx #$5f
-
    lda $20,x
    sta saved_zp,x
    dex
    bpl -
neural_begin:
    jsr policy_request        ; complete live NN, no move/logit fixtures
    php
    ldx #$5f
-
    lda saved_zp,x
    sta $20,x
    dex
    bpl -
    plp
    bcs game_error
    lda #3
    jsr draw_status
    ldx selected_move
    cpx #9
    bcs game_error
    lda original_board,x
    bne game_error
    txa
    clc
    adc #$61
    ldx history_length
    sta history,x
    inc history_length
    jsr validate_history
    bcs game_error
    jsr draw_board
    lda terminal
    bne game_terminal
    lda #0
    jsr draw_status
    jmp input_wait
invalid_key:
    lda #1
    jsr draw_status
    jmp input_wait
game_terminal:
    clc
    adc #3
    jsr draw_status
    jmp input_wait
game_error:
    lda #0
    sta move_result
    lda #1
    sta neural_failed
    lda #7
    jsr draw_status
    jmp input_wait
; A=0..7 fixed 32-character status. No KERNAL cursor/scroll interaction.
draw_status:
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    ldy #0
-
    lda status_messages,x
    sta $0684,y               ; row 16 column 4
    lda #1
    sta $da84,y
    inx
    iny
    cpy #32
    bne -
    rts
; Empty cells dim labels, X light red, O light blue.
draw_board:
    .for i := 0, i < 9, i += 1
    .block
        lda original_board+i
        beq empty_cell
        cmp #1
        bne o_cell
        lda #24
        ldx #10
        jmp store_cell
o_cell:
        lda #15
        ldx #14
        jmp store_cell
empty_cell:
        lda #i+$31
        ldx #12
store_cell:
        sta $0400+(7+2*(i / 3))*40+15+4*(i % 3)
        stx $d800+(7+2*(i / 3))*40+15+4*(i % 3)
    .bend
    .endfor
    rts
core_backup:
    .binary "core-backup.bin"
screen_template:
    .binary "screen.bin"
status_messages:
    .binary "statuses.bin"
