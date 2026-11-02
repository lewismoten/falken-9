* = $5500
activity_prng = $54f0
activity_phase = $785d
activity_tick:
    php
    pha
    txa
    pha
    tya
    pha
    cld
    inc activity_phase
    lda activity_prng
    bne +
    lda #$b7
+
    lsr a
    bcc +
    eor #$b8
+
    sta activity_prng
    lda activity_prng
    and #1
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $0687
    lda activity_prng
    and #2
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $0688
    lda activity_prng
    and #4
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $068b
    lda activity_prng
    and #8
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $0693
    lda activity_prng
    and #16
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $0694
    lda activity_prng
    and #32
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $069b
    lda activity_prng
    and #64
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $069c
    lda activity_prng
    and #128
    beq +
    lda #103
    bne ++
+
    lda #105
+
    sta $069f
    lda activity_prng
    and #1
    beq +
    lda #121
    bne ++
+
    lda #153
+
    sta $06f8
    lda activity_prng
    and #2
    beq +
    lda #121
    bne ++
+
    lda #153
+
    sta $06ff
    lda activity_prng
    and #4
    beq +
    lda #121
    bne ++
+
    lda #153
+
    sta $0704
    lda activity_prng
    and #8
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $0705
    lda activity_prng
    and #16
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $070c
    lda activity_prng
    and #32
    beq +
    lda #126
    bne ++
+
    lda #158
+
    sta $0712
    lda activity_prng
    and #64
    beq +
    lda #121
    bne ++
+
    lda #153
+
    sta $0713
    lda activity_prng
    and #128
    beq +
    lda #121
    bne ++
+
    lda #153
+
    sta $0718
    lda activity_prng
    and #1
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $071f
    lda activity_prng
    and #2
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $0750
    lda activity_prng
    and #4
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $0751
    lda activity_prng
    and #8
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $0760
    lda activity_prng
    and #16
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $0761
    lda activity_prng
    and #32
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $076a
    lda activity_prng
    and #64
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $076b
    lda activity_prng
    and #128
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $076e
    lda activity_prng
    and #1
    beq +
    lda #112
    bne ++
+
    lda #144
+
    sta $076f
    lda #1
    jsr audio_event
    pla
    tay
    pla
    tax
    pla
    plp
    rts
activity_reset:
    lda #0
    sta activity_phase
    lda #103
    sta $0687
    lda #103
    sta $0688
    lda #112
    sta $068b
    lda #103
    sta $0693
    lda #103
    sta $0694
    lda #103
    sta $069b
    lda #112
    sta $069c
    lda #103
    sta $069f
    lda #121
    sta $06f8
    lda #121
    sta $06ff
    lda #121
    sta $0704
    lda #112
    sta $0705
    lda #112
    sta $070c
    lda #126
    sta $0712
    lda #121
    sta $0713
    lda #121
    sta $0718
    lda #112
    sta $071f
    lda #112
    sta $0750
    lda #112
    sta $0751
    lda #112
    sta $0760
    lda #112
    sta $0761
    lda #112
    sta $076a
    lda #112
    sta $076b
    lda #112
    sta $076e
    lda #112
    sta $076f
    rts
paint_footer:
    lda $7819
    beq footer_subdued
    lda #$10
    sta $07c0
    lda #$c0
    bne footer_body
footer_subdued:
    lda #$b0
    sta $07c0
    lda #$60
footer_body:
    sta $07c1
    sta $07c2
    sta $07c3
    sta $07c4
    lda #$10
    sta $07e4
    lda #$c0
    sta $07e5
    sta $07e6
    sta $07e7
    rts
    .include "sid_audio.asm"
    .include "auto_demo.asm"
    .include "quit_capture.asm"
services_end:
.cerror * > $6000, "services overlap neural scratch"
