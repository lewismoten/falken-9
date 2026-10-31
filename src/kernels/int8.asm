; Signed INT8 x INT8, n=$e0 0..32; fixed inputs $3000/$3100.
; INT32 output $e1..$e4 little-endian. A/X/Y/P clobbered.
; Scratch $e5..$ec; no input writes. Return C=0, D=0.
* = $2000
entry:
    cld
    lda #0
    sta $e1
    sta $e2
    sta $e3
    sta $e4
    ldx #0
    lda $e0
    bne loop
    jmp done
loop:
    lda $3000,x
    eor $3100,x
    sta $ea
    lda $3000,x
    bpl xpositive
    eor #$ff
    clc
    adc #1
xpositive:
    sta $e6
    lda $3100,x
    bpl wpositive
    eor #$ff
    clc
    adc #1
wpositive:
    sta $e5
    lda #0
    sta $e7
    sta $e8
    sta $e9
    lda #8
    sta $eb
multiply:
    lsr $e5
    bcc skipadd
    clc
    lda $e8
    adc $e6
    sta $e8
    lda $e9
    adc $e7
    sta $e9
skipadd:
    asl $e6
    rol $e7
    dec $eb
    bne multiply
    bit $ea
    bpl productpositive
    sec
    lda #0
    sbc $e8
    sta $e8
    lda #0
    sbc $e9
    sta $e9
productpositive:
    lda #0
    bit $e9
    bpl extend
    lda #$ff
extend:
    sta $ec
    clc
    lda $e1
    adc $e8
    sta $e1
    lda $e2
    adc $e9
    sta $e2
    lda $e3
    adc $ec
    sta $e3
    lda $e4
    adc $ec
    sta $e4
    inx
    cpx $e0
    beq done
    jmp loop
done:
    clc
    rts
end:
.cerror * > $2100, "kernel exceeds reserved code page"
