; Falken-9 isolated binary-weight / INT16-activation dot product.
; ABI: $e0=n (0..32), activations $3000 INT16 LE, weights $3100
; LSB-first bits (0=-1,1=+1). Output $e1..$e4 INT32 LE.
; Clobbers A/X/Y/P and $e1..$e8. No rounding or saturation.
; Caller guarantees bounds and owns these addresses. Not a complete inference.
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
    beq done
loop:
    txa
    and #7
    bne have_weight_byte
    txa
    lsr
    lsr
    lsr
    tay
    lda $3100,y
    sta $e5
have_weight_byte:
    txa
    asl
    tay
    lda $3000,y
    sta $e6
    lda $3001,y
    sta $e7
    lda #0
    bit $e7
    bpl positive
    lda #$ff
positive:
    sta $e8
    lsr $e5
    bcc subtract
    clc
    lda $e1
    adc $e6
    sta $e1
    lda $e2
    adc $e7
    sta $e2
    lda $e3
    adc $e8
    sta $e3
    lda $e4
    adc $e8
    sta $e4
    jmp next
subtract:
    sec
    lda $e1
    sbc $e6
    sta $e1
    lda $e2
    sbc $e7
    sta $e2
    lda $e3
    sbc $e8
    sta $e3
    lda $e4
    sbc $e8
    sta $e4
next:
    inx
    cpx $e0
    beq done
    jmp loop
done:
    clc
    rts
end:
.cerror * > $2100, "kernel exceeds reserved code page"
