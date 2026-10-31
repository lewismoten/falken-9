; Standalone resident integer proof. No KERNAL/UI or old-game RAM assumptions.
; NMOS 6502, IRQ-disabled caller, A/X/Y/P clobbered, decimal clear.
operand = $20                    ; preserved signed INT32
weight = $24                     ; preserved signed INT16
acc = $26                        ; signed INT40 input/output
shift = $2b                      ; preserved unsigned right shift 0..39
mag = $30                        ; INT40 magnitude scratch
product = $35                    ; INT40 scratch
wm = $3a                         ; unsigned16 multiplier scratch
sign = $3c
counter = $3d
oldsign = $3e
* = $0800
; acc += operand * weight. Operand abs <= $7fffff; C=1 otherwise or
; signed40 sum overflow. Product fits signed40 under this explicit bound.
mac40:
    cld
    lda operand+3
    eor weight+1
    sta sign
    lda #0
    sta mag+4
    lda operand+3
    bpl mac_copy
    sec
    .for i := 0, i < 4, i += 1
        lda #0
        sbc operand+i
        sta mag+i
    .endfor
    jmp mac_bound
mac_copy:
    .for i := 0, i < 4, i += 1
        lda operand+i
        sta mag+i
    .endfor
mac_bound:
    lda mag+3
    bne mac_bad
    lda mag+2
    bpl mac_valid
mac_bad:
    sec
    rts
mac_valid:
    lda weight+1
    bpl mac_wcopy
    sec
    lda #0
    sbc weight
    sta wm
    lda #0
    sbc weight+1
    sta wm+1
    jmp mac_init
mac_wcopy:
    lda weight
    sta wm
    lda weight+1
    sta wm+1
mac_init:
    lda #0
    .for i := 0, i < 5, i += 1
        sta product+i
    .endfor
    lda #16
    sta counter
mac_loop:
    lsr wm+1
    ror wm
    bcc mac_skip
    clc
    .for i := 0, i < 5, i += 1
        lda product+i
        adc mag+i
        sta product+i
    .endfor
mac_skip:
    asl mag
    .for i := 1, i < 5, i += 1
        rol mag+i
    .endfor
    dec counter
    bne mac_loop
    bit sign
    bpl mac_add
    sec
    .for i := 0, i < 5, i += 1
        lda #0
        sbc product+i
        sta product+i
    .endfor
mac_add:
    lda acc+4
    sta oldsign
    clc
    .for i := 0, i < 5, i += 1
        lda acc+i
        adc product+i
        sta acc+i
    .endfor
    ; Overflow iff operands have same sign and result has different sign.
    lda oldsign
    eor product+4
    bmi math_ok
    lda oldsign
    eor acc+4
    bmi math_bad
math_ok:
    clc
    rts
math_bad:
    sec
    rts

; Signed40 / 2**shift, nearest ties away. Handles -2**39 without abs overflow.
scale40:
    cld
    lda shift
    cmp #40
    bcs math_bad
    lda acc+4
    sta sign
    bpl scale_abs_done
    jsr negate_acc
scale_abs_done:
    ldx shift
    beq scale_sign
scale_loop:
    lsr acc+4
    .for i := 3, i >= 0, i -= 1
        ror acc+i
    .endfor
    dex
    bne scale_loop
    bcc scale_sign
    ; Last discarded bit is exactly the round-to-nearest increment.
    inc acc
    bne scale_sign
    inc acc+1
    bne scale_sign
    inc acc+2
    bne scale_sign
    inc acc+3
    bne scale_sign
    inc acc+4
scale_sign:
    bit sign
    bpl math_ok
    jsr negate_acc
    clc
    rts
negate_acc:
    sec
    .for i := 0, i < 5, i += 1
        lda #0
        sbc acc+i
        sta acc+i
    .endfor
    rts
    .include "model.inc"
    .include "divsqrt.asm"
    .include "frontend.asm"
    .include "lookup.asm"
    .include "attention.asm"
    .include "projection.asm"
.if FULL_FORWARD
    .include "forward.asm"
.endif
code_end:
.cerror * > $4000, "runtime code overlaps resident model"
* = $4000
model:
    .binary "model.f9j"
model_end:
.cerror * > $6000, "model overlaps activation arena"
