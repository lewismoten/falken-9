; Resident native art UI. Live planes bank 0: screen $0400, bitmap $2000,
; charset $3000 (view alias). Compressed backing $a000..$cfff, never I/O.
saved_zp = $7880
pending_key = $7850
neural_failed = $7851
view = $7852                    ; 0 title, 1 info, 2 game, 3 quit
mode = $7853                    ; 1 human/model, 2 human/human, 0 model/model
ui_port = $7854
ui_index = $7855
ui_count = $7856
packet_count = $7857
packet_kind = $7858
packet_value = $7859
status_index = $785a
text_column = $785b
text_glyph = $785c
activity_phase = $785d
ui_saved = $7860
src = $f7
dst = $f9
remaining = $fb
aux = $fd
app_start:
    sei
    cld
    ldx #$ff
    txs
    ldx #15
-
    lda core_backup,x
    sta $0800,x
    dex
    bpl -
    lda #$ff
    sta $cc
    lda $dd00
    ora #3
    sta $dd00
    lda #0
    sta $d020
    sta $d021
    sta history_length
    sta neural_failed
    sta activity_phase
    lda #1
    sta mode
    jsr enter_title
input_wait:
    cli
    jsr $ffe4
    sei
    cld
    cmp #0
    beq input_wait
    sta pending_key
    lda #0
    sta move_result
    lda view
    beq title_key
    cmp #1
    beq info_key
    cmp #2
    beq game_key
    jmp input_wait
; These transitions return through this dispatcher; no abandoned JSR frames.
title_key:
    lda pending_key
    and #$df
    cmp #$49
    bne +
    jsr enter_info
    jmp input_wait
+
    cmp #$51
    bne +
    jsr enter_quit
    jmp input_wait
+
    lda pending_key
    cmp #$30
    bcc title_navigation
    cmp #$33
    bcs title_navigation
    sec
    sbc #$30
    sta mode
    jmp start_game
title_navigation:
    cmp #13
    beq start_game
    cmp #$11
    beq next_mode
    cmp #$91
    beq previous_mode
    jmp input_wait
next_mode:
    lda mode
    clc
    adc #1
    cmp #3
    bcc +
    lda #0
+
    sta mode
    jsr enter_title
    jmp input_wait
previous_mode:
    lda mode
    bne +
    lda #3
+
    sec
    sbc #1
    sta mode
    jsr enter_title
    jmp input_wait
info_key:
    lda pending_key
    and #$df
    cmp #$51
    bne input_wait
    jsr enter_title
    jmp input_wait
start_game:
    lda #2
    sta view
new_game:
    lda #0
    sta history_length
    sta neural_failed
    sta move_result
    sta activity_phase
    jsr validate_history
    jsr draw_board
    jsr ready_status
    lda mode
    beq auto_turn
    jmp input_wait
game_key:
    lda pending_key
    and #$df
    cmp #$51
    bne +
    jsr enter_title
    jmp input_wait
+
    cmp #$52
    beq new_game
    lda terminal
    ora neural_failed
    bne input_wait
    lda pending_key
    cmp #$31
    bcc invalid_key
    cmp #$3a
    bcs invalid_key
    sec
    sbc #$31
    tax
    lda original_board,x
    bne invalid_key
    txa
    jsr commit_square
    bcs game_error
    jsr draw_board              ; accepted human mark is visible BEFORE NN
    lda terminal
    bne game_terminal
    lda mode
    cmp #2
    beq two_human_ready
auto_turn:
    lda #2
    jsr draw_status
    ldx #$5f
-
    lda $20,x
    sta saved_zp,x
    dex
    bpl -
neural_begin:
    jsr policy_request
    php
    ldx #$5f
-
    lda saved_zp,x
    sta $20,x
    dex
    bpl -
    plp
    bcs game_error
    lda #0
    sta activity_phase
    ldx selected_move
    cpx #9
    bcs game_error
    lda original_board,x
    bne game_error
    txa
    jsr commit_square
    bcs game_error
    jsr draw_board
    lda terminal
    bne game_terminal
    lda mode
    beq auto_turn
    jsr ready_status
    jmp input_wait
two_human_ready:
    jsr ready_status
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
    sta activity_phase
    lda #1
    sta neural_failed
    lda #7
    pha
    jsr draw_board
    pla
    jsr draw_status
    jmp input_wait
commit_square:
    clc
    adc #$61
    ldx history_length
    sta history,x
    inc history_length
    jmp validate_history
ready_status:
    lda #0
    ldx mode
    cpx #2
    bne +
    lda #8
+
    jmp draw_status
; Save all UI pointers and exact port; never hide KERNAL, I/O, or IRQ vectors.
ui_begin:
    sei
    cld
    ldx #7
-
    lda $f7,x
    sta ui_saved,x
    dex
    bpl -
    lda $01
    sta ui_port
    and #$fe
    sta $01
    rts
ui_end:
    lda ui_port
    sta $01
    ldx #7
-
    lda ui_saved,x
    sta $f7,x
    dex
    bpl -
    rts
; Expands packet stream into exactly remaining output bytes. Trusted bundled art.
unpack_plane:
    lda #0
    sta packet_count
unpack_next:
    lda remaining
    ora remaining+1
    beq unpack_done
    lda packet_count
    bne unpack_byte
    jsr source_byte
    pha
    and #$80
    sta packet_kind
    pla
    and #$7f
    clc
    adc #1
    sta packet_count
    lda packet_kind
    beq unpack_byte
    jsr source_byte
    sta packet_value
unpack_byte:
    lda packet_kind
    beq unpack_literal
    lda packet_value
    jmp unpack_store
unpack_literal:
    jsr source_byte
unpack_store:
    ldy #0
    sta (dst),y
    inc dst
    bne +
    inc dst+1
+
    lda remaining
    bne +
    dec remaining+1
+
    dec remaining
    dec packet_count
    jmp unpack_next
unpack_done:
    rts
source_byte:
    ldy #0
    lda (src),y
    inc src
    bne +
    inc src+1
+
    rts
; Compile-time macro sets disjoint source/destination and uncompressed count.
copy_plane .macro source, dest, length
    lda #<\source
    sta src
    lda #>\source
    sta src+1
    lda #<\dest
    sta dst
    lda #>\dest
    sta dst+1
    lda #<\length
    sta remaining
    lda #>\length
    sta remaining+1
    jsr unpack_plane
.endmacro
enter_title:
    lda #0
    sta view
    sta move_result
    sta activity_phase
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_charset,$3000,2048
    #copy_plane art_title_screen,$0400,1000
    #copy_plane art_title_color,$d800,1000
    ; One selector, one color, rendered before display enable.
    lda #0
    sta $0400+9*40+9
    sta $0400+11*40+9
    sta $0400+13*40+9
    ldx mode
    lda selector_rows,x
    tax
    lda #44
    sta $0400+9*40+9,x
    lda #7
    sta $d800+9*40+9,x
    lda #$1c
    sta $d018
    lda #8
    sta $d016
    lda #$1b
    sta $d011
    jmp ui_end
enter_info:
    lda #1
    sta view
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_charset,$3000,2048
    #copy_plane art_info_screen,$0400,1000
    #copy_plane art_info_color,$d800,1000
    lda #$1c
    sta $d018
    lda #8
    sta $d016
    lda #$1b
    sta $d011
    jmp ui_end
selector_rows:
    .byte 160,0,80
enter_quit:
    jsr enter_info
    lda #3
    sta view
    jsr ui_begin
    #copy_plane art_quit_screen,$0400,1000
    #copy_plane art_quit_color,$d800,1000
    jmp ui_end
; Immutable blank source + declared empty labels OR original occupied marks.
draw_board:
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_board_bitmap,$2000,8000
    #copy_plane art_board_screen,$0400,1000
    #copy_plane art_board_color,$d800,1000
    lda #0
    sta ui_index
draw_mark_loop:
    ldx ui_index
    lda original_board,x
    beq draw_empty_label
    sec
    sbc #1
    sta ui_count
    txa
    asl a
    clc
    adc ui_count
    tax
    lda mark_counts,x
    sta ui_count
    txa
    asl a
    tax
    lda mark_pointers,x
    sta src
    lda mark_pointers+1,x
    sta src+1
    jmp patch_loop
draw_empty_label:
    txa
    asl a
    tax
    lda numeric_label_pointers,x
    sta src
    lda numeric_label_pointers+1,x
    sta src+1
    lda #9                      ; eight bitmap rows + paired screen attribute
    sta ui_count
patch_loop:
    jsr source_byte
    sta dst
    jsr source_byte
    sta dst+1
    jsr source_byte
    ldy #0
    sta (dst),y
    dec ui_count
    bne patch_loop
draw_mark_next:
    inc ui_index
    lda ui_index
    cmp #9
    bne draw_mark_loop
    ; Controls have their own bottom panel, never touch the grid or lights.
    lda #<control_text
    sta src
    lda #>control_text
    sta src+1
    lda #<$2000+23*320+4*8
    sta dst
    lda #>($2000+23*320+4*8)
    sta dst+1
    lda #<($0400+23*40+4)
    sta aux
    lda #>($0400+23*40+4)
    sta aux+1
    jsr bitmap_text
    lda #$18
    sta $d018
    sta $d016
    lda #$3b
    sta $d011
    jmp ui_end
; A indexes a 32-column bitmap status panel at row 17, separate from marks.
draw_status:
    sta status_index
    jsr ui_begin
    lda #0
    sta src+1
    lda status_index
    ldx #5
-
    asl a
    rol src+1
    dex
    bne -
    clc
    adc #<status_messages
    sta src
    lda src+1
    adc #>status_messages
    sta src+1
    lda #<($2000+17*320+4*8)
    sta dst
    lda #>($2000+17*320+4*8)
    sta dst+1
    lda #<($0400+17*40+4)
    sta aux
    lda #>($0400+17*40+4)
    sta aux+1
    jsr bitmap_text
    jmp ui_end
bitmap_text:
    lda #0
    sta text_column
text_next:
    ldy text_column
    lda (src),y
    sta text_glyph
    lda #0
    sta remaining+1
    lda text_glyph
    asl a
    rol remaining+1
    asl a
    rol remaining+1
    asl a
    rol remaining+1
    clc
    adc #<bitmap_font
    sta remaining
    lda remaining+1
    adc #>bitmap_font
    sta remaining+1
    ldy #7
-
    lda (remaining),y
    sta (dst),y
    dey
    bpl -
    ldy text_column
    lda #$10
    sta (aux),y
    ; Color RAM is irrelevant for only 00/01 text pixels.
    clc
    lda dst
    adc #8
    sta dst
    bcc +
    inc dst+1
+
    inc text_column
    lda text_column
    cmp #32
    bne text_next
    rts
; Separate relocated orchestration, same immutable neural subkernels/weights.
; 627-vector parity is required before this path can be accepted.
graphical_forward:
    jmp graph_full_forward
activity_tick:
    php
    pha
    txa
    pha
    tya
    pha
    inc activity_phase
    lda activity_phase
    and #7
    tax
    lda activity_patterns,x
    sta packet_value
    ldx #0
-
    lsr packet_value
    lda activity_base,x
    and #$0f
    bcc +
    ora #$70
    bne activity_store
+
    ora #$60
activity_store:
    sta $0400+18*40+21,x
    inx
    cpx #4
    bne -
    pla
    tay
    pla
    tax
    pla
    plp
    rts
activity_patterns:
    .byte 5,10,3,12,9,6,1,14
    .include "presentation-forward.inc"
core_backup:
    .binary "core-backup.bin"
bitmap_font:
    .binary "bitmap-font.bin"
status_messages:
    .binary "statuses.bin"
control_text:
    .binary "controls.bin"
    .include "graphics.inc"
mark_patch_data:
    .binary "mark-patches.bin"
numeric_label_data:
    .binary "numeric-labels.bin"
