; Isolated NMOS 6502 experiment; ABI in docs/ARITHMETIC.md.
; $e0=n (0..32), $3000 signed INT8, $3100 LSB-first binary.
; $e1/e2=result INT16 LE. Clobbers A/X/Y/P, $e1..$e7.
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
    and #7
    bne decode
    lda $3100,y
    sta $e3
    iny
decode:
    lda $3000,x
    sta $e6
    lda #0
    bit $e6
    bpl positive
    lda #$ff
positive:
    sta $e7
    lsr $e3
    bcc subtract
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
end:
.cerror * > $2100, "kernel exceeds reserved code page"
