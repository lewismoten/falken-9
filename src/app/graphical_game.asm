; Resident native art UI. Live planes bank 0: screen $0400, bitmap $2000,
; charset $3000 (view alias). Compressed backing $a000..$cfff, never I/O.
    .include "service-labels.inc"
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
painted_board = $78e0           ; after saved_zp $7880..$78df; never model input
info_scroll = $785e
info_row = $785f
progress_active = $78e9
progress_event_index = $78ea
progress_filled = $78eb
progress_color = $78ec
progress_segment = $78ed
progress_pattern = $78ee
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
    sta progress_active
    lda #1
    sta mode
    jsr audio_init
    jsr enter_title
input_wait:
    sei
    jsr quit_release_guard
    lda quit_pending
    beq +
    lda view
    cmp #2
    beq auto_exit
+
    cli
    jsr $ffe4
    sei
    cld
    cmp #0
    bne input_received
    lda view
    cmp #2
    bne input_wait
    lda mode
    bne input_wait
    jsr auto_pause_due
    bcc input_wait
auto_restart:
    jmp new_game
input_received:
    sta pending_key
    and #$df
    cmp #$51
    bne +
    lda quit_blocked
    bne input_wait
    lda pending_key
    and #$df
+
    cmp #$4d
    bne +
    lda view
    cmp #3
    beq input_wait
    jsr audio_toggle
    jmp input_wait
+
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
    jsr patch_title_selector
    lda #3
    jsr audio_event
    jmp input_wait
previous_mode:
    lda mode
    bne +
    lda #3
+
    sec
    sbc #1
    sta mode
    jsr patch_title_selector
    lda #3
    jsr audio_event
    jmp input_wait
info_key:
    lda pending_key
    cmp #$11
    beq info_down
    cmp #$91
    beq info_up
    and #$df
    cmp #$51
    bne input_wait
    jsr enter_title
    jmp input_wait
info_down:
    lda info_scroll
    cmp #info_line_count-18
    bcs input_wait
    inc info_scroll
    jsr render_info
    lda #2
    jsr audio_event
    jmp input_wait
info_up:
    lda info_scroll
    beq input_wait
    dec info_scroll
    jsr render_info
    lda #2
    jsr audio_event
    jmp input_wait
start_game:
    lda #0
    sta quit_pending
    lda #1
    sta quit_active
    lda #2
    sta view
    jsr auto_session_reset
    jsr reset_game_state
    jsr draw_board
    jmp new_game_ready
new_game:
    lda mode
    bne +
    lda #1
    sta auto_later
+
    jsr reset_game_state
    jsr update_board
    jsr progress_reset
new_game_ready:
    jsr ready_status
    lda mode
    bne input_wait
    lda #1
    sta auto_started
    jmp auto_turn
auto_exit:
    lda #0
    sta quit_active
    sta quit_pending
    sta move_result
    sta history_length
    sta auto_pausing
    sta auto_started
    sta auto_later
    sta auto_sampled
    lda #1
    sta quit_blocked
    jsr validate_history
    jsr enter_title
    jmp input_wait
reset_game_state:
    lda #0
    sta auto_pausing
    sta auto_sampled
    sta history_length
    sta neural_failed
    sta move_result
    sta activity_phase
    jmp validate_history
game_key:
    lda pending_key
    and #$df
    cmp #$51
    bne +
    jmp auto_exit
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
    jsr update_board            ; accepted human mark is visible BEFORE NN
    jsr audio_mark
    lda terminal
    bne game_terminal
    lda mode
    cmp #2
    beq two_human_ready
auto_turn:
    lda quit_pending
    bne auto_exit
    lda mode
    bne compute_forward
    ; Bounded safe-boundary input only; no KERNAL scanner inside neural work.
    cli
    jsr $ffe4
    sei
    cld
    and #$df
    cmp #$51
    beq auto_exit
    cmp #$52
    beq new_game
    cmp #$4d
    bne compute_forward
    jsr audio_toggle
compute_forward:
    lda #2
    jsr draw_status
    jsr progress_begin
    ldx #$5f
-
    lda $20,x
    sta saved_zp,x
    dex
    bpl -
neural_begin:
    jsr audio_work_begin
    jsr policy_request
    php
    sei
    ldx #$5f
-
    lda saved_zp,x
    sta $20,x
    dex
    bpl -
    jsr audio_work_end
    plp
    php
    lda quit_pending
    beq +
    plp
    jmp auto_exit
+
    plp
    bcs game_error
    jsr auto_resolve_opening
    bcs game_error
    lda #0
    sta activity_phase
    ldx selected_move
    cpx #9
    bcs game_error
    lda original_board,x
    bne game_error
    lda mode
    bne +
    lda history_length
    bne +
    stx auto_last_opening
+
    txa
    jsr commit_square
    bcs game_error
    jsr update_board
    jsr audio_mark
    jsr progress_commit
    jsr progress_reset
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
    lda mode
    bne input_wait
    jsr auto_pause_begin
    jmp input_wait
game_error:
    lda #0
    sta auto_pausing
    jsr progress_reset
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
    jsr audio_work_begin
    rts
ui_end:
    sei
    lda ui_port
    sta $01
    ldx #7
-
    lda ui_saved,x
    sta $f7,x
    dex
    bpl -
    jsr audio_work_end
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
    sta quit_active
    sta quit_pending
    sta view
    sta move_result
    sta activity_phase
    sta progress_active
    sta progress_filled
    sta auto_pausing
    sta auto_started
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_charset,$3000,2048
    #copy_plane art_title_screen,$0400,1000
    #copy_plane art_title_color,$d800,1000
    jsr patch_title_selector
    lda #$1c
    sta $d018
    lda #8
    sta $d016
    lda #$1b
    sta $d011
    jmp ui_end
; Selection is a bounded six-cell delta, not a view transition.
patch_title_selector:
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
    rts
enter_info:
    lda #1
    sta view
    lda #0
    sta info_scroll
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_charset,$3000,2048
    #copy_plane art_info_screen,$0400,1000
    #copy_plane art_info_color,$d800,1000
    jsr paint_info
    lda #$1c
    sta $d018
    lda #8
    sta $d016
    lda #$1b
    sta $d011
    jmp ui_end
selector_rows:
    .byte 160,0,80
render_info:
    jsr ui_begin
    jsr paint_info
    jmp ui_end
paint_info:
    lda #<info_chars
    sta src
    lda #>info_chars
    sta src+1
    ldx info_scroll
    beq info_seek_done
info_seek:
    clc
    lda src
    adc #29
    sta src
    bcc +
    inc src+1
+
    dex
    bne info_seek
info_seek_done:
    lda #<$04a5
    sta dst
    lda #>$04a5
    sta dst+1
    lda #<$d8a5
    sta aux
    lda #>$d8a5
    sta aux+1
    lda #0
    sta info_row
info_copy_row:
    lda info_scroll
    clc
    adc info_row
    tax
    lda info_line_colors,x
    sta packet_value
    ldy #0
-
    lda (src),y
    sta (dst),y
    lda packet_value
    sta (aux),y
    iny
    cpy #29
    bne -
    ; Source rows are tightly packed; destinations retain the supplied frame.
    clc
    lda src
    adc #29
    sta src
    bcc +
    inc src+1
+
    clc
    lda dst
    adc #40
    sta dst
    bcc +
    inc dst+1
+
    clc
    lda aux
    adc #40
    sta aux
    bcc +
    inc aux+1
+
    inc info_row
    lda info_row
    cmp #18
    bne info_copy_row
    ldx info_scroll
    lda info_scroll_positions,x
    sta packet_value
    ldx #0
info_track_loop:
    lda info_track_lo,x
    sta dst
    lda info_track_hi,x
    sta dst+1
    lda #info_track_glyph
    cpx packet_value
    bne +
    lda #info_marker_glyph
+
    ldy #0
    sta (dst),y
    lda dst+1
    clc
    adc #$d4
    sta dst+1
    lda #info_track_color
    cpx packet_value
    bne +
    lda #info_marker_color
+
    sta (dst),y
    inx
    cpx #18
    bne info_track_loop
    rts
enter_quit:
    jsr enter_info
    lda #3
    sta view
    jsr ui_begin
    #copy_plane art_quit_screen,$0400,1000
    #copy_plane art_quit_color,$d800,1000
    jsr ui_end
    jmp audio_stop
; Immutable blank source + declared empty labels OR original occupied marks.
draw_board:
    jsr ui_begin
    lda #$0b
    sta $d011
    #copy_plane art_board_bitmap,$2000,8000
    #copy_plane art_board_screen,$0400,1000
    #copy_plane art_board_color,$d800,1000
    ldx #8
    lda #$ff
-
    sta painted_board,x
    dex
    bpl -
    jsr patch_board
    jsr progress_reset
    lda #$18
    sta $d018
    sta $d016
    lda #$3b
    sta $d011
    jmp ui_end
update_board:
    jsr ui_begin
    jsr patch_board
    jmp ui_end
patch_board:
    lda #0
    sta ui_index
draw_mark_loop:
    ldx ui_index
    lda original_board,x
    cmp painted_board,x
    beq draw_mark_next
    sta painted_board,x
    cmp #0
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
    lda empty_counts,x
    sta ui_count
    txa
    asl a
    tax
    lda empty_pointers,x
    sta src
    lda empty_pointers+1,x
    sta src+1
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
    rts
; Native one-cell turn/result glyph. Commands live in INFO, not over the art.
draw_status:
    sta status_index
    jsr ui_begin
    lda status_index
    cmp #1
    beq status_invalid
    cmp #7
    beq status_error
    lda terminal
    bne +
    lda side
+
    sec
    sbc #1
    tax
    jmp status_paint
status_invalid:
    ldx #3
    bne status_paint
status_error:
    ldx #4
status_paint:
    lda status_colors,x
    sta $0643
    txa
    asl a
    asl a
    asl a
    tax
    ldy #7
-
    lda status_glyphs,x
    sta $3218,y
    inx
    dey
    bpl -
    jsr paint_footer
    jmp ui_end
status_colors: .byte $a0,$30,$70,$70,$20
; Stored reverse-scanline for the descending destination loop above.
status_glyphs:
    .byte $00,$41,$41,$14,$14,$41,$41,$00
    .byte $00,$14,$41,$41,$41,$41,$14,$00
    .byte $00,$54,$41,$41,$41,$41,$54,$00
    .byte $00,$10,$00,$10,$04,$44,$14,$00
    .byte $00,$10,$00,$10,$10,$10,$10,$00
; Separate relocated orchestration, same immutable neural subkernels/weights.
; 627-vector parity is required before this path can be accepted.
graphical_forward:
    jmp graph_full_forward

; Preserves live arithmetic flags, registers, and every ZP byte. No IRQ/timer.
progress_event:
    php
    pha
    txa
    pha
    tya
    pha
    jsr activity_tick
    bcs progress_event_done       ; failed computations earn no completed work
    cld
    lda progress_active
    cmp #1
    bne progress_event_done
    ldx progress_event_index
    cpx #32
    bcs progress_event_done
    lda progress_thresholds,x
    sta progress_filled
    inc progress_event_index
    jsr paint_progress
progress_event_done:
    pla
    tay
    pla
    tax
    pla
    plp
    rts
progress_begin:
    lda #1
    sta progress_active
    lda #0
    sta progress_event_index
    sta progress_filled
    lda #$20
    ldx side
    cpx #1
    beq +
    lda #$60
+
    sta progress_color
    jmp paint_progress
progress_commit:
    lda #48
    sta progress_filled
    jmp paint_progress
progress_reset:
    lda #0
    sta progress_active
    sta progress_filled
    sta progress_color
    jsr activity_reset
    jmp paint_progress
; All eight scanlines, paired with exact screen cells. Two boxes skip turn cell.
; Direct absolute indexed writes avoid borrowing neural zero-page pointers.
paint_progress:
    ldx #0
    lda progress_filled
    sta progress_segment
progress_cell_loop:
    lda progress_color
    sta $063e,x
    lda #0
    ldy progress_segment
    cpy #4
    bcc +
    lda #$55
    bne progress_pattern_ready
+
    lda progress_partial,y
progress_pattern_ready:
    sta progress_pattern
    lda progress_color
    beq +
    lda progress_pattern
    cpx #0
    beq progress_left
    cpx #6
    beq progress_left
    cpx #4
    beq progress_right
    cpx #12
    bne +
progress_right:
    ora #$01
    bne +
progress_left:
    ora #$40
+
    sta progress_pattern
    txa
    pha
    asl a
    asl a
    asl a
    tax
    lda progress_pattern
    sta $31f1,x
    sta $31f2,x
    sta $31f3,x
    sta $31f4,x
    sta $31f5,x
    sta $31f6,x
    lda #0
    ldy progress_color
    beq +
    lda #$55
+
    sta $31f0,x
    sta $31f7,x
    pla
    tax
    lda progress_segment
    sec
    sbc #4
    bcs +
    lda #0
+
    sta progress_segment
    inx
    cpx #5
    bne +
    inx                         ; native turn/result glyph is $0643/$3218
+
    cpx #13
    bne progress_cell_loop
    rts
progress_partial: .byte $00,$40,$50,$54
    .include "presentation-forward.inc"
core_backup:
    .binary "core-backup.bin"
    .include "graphics.inc"
mark_patch_data:
    .binary "mark-patches.bin"
numeric_label_data:
    .binary "numeric-labels.bin"
