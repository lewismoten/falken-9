; $e0=n (0..32), $3000 INT8, $3100 packed 00=0,01=+1,10=-1.
; $e1/e2 INT16 LE. 11 returns C=1; output then unspecified.
; Clobbers A/X/Y/P, $e1..$e7. No input stores.
* = $2000
entry:
    cld
    lda #0
    sta $e1
    sta $e2
    ldx #0
    ldy #0
    lda $e0
    beq done
loop:
    txa
    and #3
    bne decode
    lda $3100,y
    sta $e3
    iny
decode:
    lda $e3
    and #3
    sta $e4
    lsr $e3
    lsr $e3
    cmp #0
    beq next
    cmp #3
    beq invalid
    lda $3000,x
    sta $e6
    lda #0
    bit $e6
    bpl positive
    lda #$ff
positive:
    sta $e7
    lda $e4
    cmp #1
    bne subtract
    clc
    lda $e1
    adc $e6
    sta $e1
    lda $e2
    adc $e7
    sta $e2
    jmp next
subtract:
    sec
    lda $e1
    sbc $e6
    sta $e1
    lda $e2
    sbc $e7
    sta $e2
next:
    inx
    cpx $e0
    bne loop
done:
    clc
    rts
invalid:
    sec
    rts
end:
.cerror * > $2100, "kernel exceeds reserved code page"
