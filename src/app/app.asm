; Resident original-coordinate protocol. Core remains byte-identical.
    .include "core-labels.inc"
history = $7800
history_length = $7809
original_board = $7810
terminal = $7819             ; 0 ongoing, 1 X win, 2 O win, 3 draw
side = $781a
history_index = $781b
cell_index = $781c
line_index = $781d
line_mark = $781e
* = $8000
    jmp app_start
; Callable protocol accepts uppercase A-I as well as lowercase a-i.
; C=1 malformed/repeated/continuation; terminal board itself succeeds.
validate_history:
    cld
    lda history_length
    cmp #10
    bcc +
    sec
    rts
+
    lda #0
    sta terminal
    sta history_index
    ldx #8
-
    sta original_board,x
    dex
    bpl -
    lda #1
    sta side
history_loop:
    lda history_index
    cmp history_length
    beq history_good
    lda terminal
    bne history_bad
    ldx history_index
    lda history,x
    cmp #$41
    bcc +
    cmp #$4a
    bcs +
    ora #$20
+
    cmp #$61
    bcc history_bad
    cmp #$6a
    bcs history_bad
    sec
    sbc #$61
    tax
    lda original_board,x
    bne history_bad
    lda side
    sta original_board,x
    eor #3
    sta side
    inc history_index
    jsr check_terminal
    jmp history_loop
history_good:
    clc
    rts
history_bad:
    sec
    rts
; Rules only: no strategy or move computation.
check_terminal:
    lda #0
    sta terminal
    sta line_index
terminal_lines_loop:
    ldy line_index
    ldx winning_lines,y
    lda original_board,x
    beq terminal_next
    sta line_mark
    iny
    ldx winning_lines,y
    cmp original_board,x
    bne terminal_next
    iny
    ldx winning_lines,y
    cmp original_board,x
    bne terminal_next
    sta terminal
    rts
terminal_next:
    lda line_index
    clc
    adc #3
    sta line_index
    cmp #24
    bne terminal_lines_loop
    ldx #8
-
    lda original_board,x
    beq terminal_done
    dex
    bpl -
    lda #3
    sta terminal
terminal_done:
    rts
winning_lines:
    .byte 0,1,2,3,4,5,6,7,8,0,3,6,1,4,7,2,5,8,0,4,8,2,4,6
    .include "wrapper.asm"
    .include "game.asm"
app_end:
.cerror * > $a000, "app overlaps BASIC ROM"
