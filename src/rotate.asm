;=====================================================================
;  GRAVASSIST — περιστροφή + packing sprites  (MODE 1)
;
;  Μία πέραση κάνει και τα τρία:
;     unpacked (1 byte/pixel) -> περιστροφή 90n -> MODE 1 bytes -> x-shift
;
;  Έτσι τα sprites αποθηκεύονται ΜΙΑ φορά, σε ΜΙΑ φορά βαρύτητας, χωρίς
;  pre-shifted αντίγραφα. Ο ίδιος κώδικας εξυπηρετεί ήρωα και αντικείμενα.
;  Πλήρες σκεπτικό: docs/sprites.md §1-3.
;=====================================================================

SPR_MAXW        equ 4           ; μέγιστο πλάτος εξόδου σε bytes (12px + 3 shift)
SPR_MAXH        equ 12          ; μέγιστο ύψος εξόδου σε γραμμές
SPR_BUFSZ       equ SPR_MAXW*2*SPR_MAXH

;---------------------------------------------------------------------
; spr_transform
;   IN:  HL = unpacked frame (W*H bytes, 1 byte/pixel, pen 0..3)
;        B  = W (πλάτος πηγής)   C = H (ύψος πηγής)
;        A  = orient 0..3  (0=DOWN 1=LEFT 2=UP 3=RIGHT — docs/sprites.md §2)
;        (spr_shift) = 0..3, μετατόπιση σε pixels μέσα στο πρώτο byte
;   OUT: spr_buf· ανά γραμμή (spr_bw) ζεύγη bytes (mask, data)
;        (spr_bw) = πλάτος εξόδου σε bytes, (spr_bh) = γραμμές εξόδου
;   ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL, IX
;
;   Το blit μετά είναι:  ld a,(de) : and mask : or data : ld (de),a
;---------------------------------------------------------------------
spr_transform:
                and  3
                ld   (spr_orient),a         ; ΠΡΩΤΑ αυτό: το A χάνεται αμέσως μετά
                ld   (spr_srcbase),hl
                ld   a,b
                ld   (spr_w),a
                ld   a,c
                ld   (spr_h),a

                call spr_mul                ; HL = B*C = W*H  (max 144)
                ld   (spr_wh),hl

                ld   a,(spr_orient)
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,spr_setup_tab
                add  hl,de
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                ex   de,hl
                jp   (hl)

spr_setup_tab   dw   spr_set0, spr_set1, spr_set2, spr_set3

; Κάθε setup ορίζει start / dx / dy / διαστάσεις εξόδου. docs/sprites.md §2:
;   DOWN   0 μοιρών   start 0        dx +1  dy +W   W x H
;   LEFT   90 CW      start (H-1)*W  dx -W  dy +1   H x W
;   UP     180 μοιρών start W*H-1    dx -1  dy -W   W x H
;   RIGHT  90 CCW     start W-1      dx +W  dy -1   H x W

spr_set0:                                   ; DOWN
                ld   hl,0
                ld   de,1
                ld   a,(spr_w)
                ld   c,a
                ld   b,0
                call spr_store
                call spr_dims_same
                jp   spr_core

spr_set1:                                   ; LEFT (90 δεξιόστροφα)
                ld   hl,(spr_wh)
                ld   a,(spr_w)
                ld   c,a
                ld   b,0
                or   a
                sbc  hl,bc                  ; start = W*H - W
                ld   a,(spr_w)
                neg
                ld   e,a
                ld   d,#FF                  ; dx = -W
                ld   bc,1                   ; dy = +1
                call spr_store
                call spr_dims_swap
                jp   spr_core

spr_set2:                                   ; UP (180)
                ld   hl,(spr_wh)
                dec  hl                     ; start = W*H - 1
                ld   de,-1                  ; dx = -1
                ld   a,(spr_w)
                neg
                ld   c,a
                ld   b,#FF                  ; dy = -W
                call spr_store
                call spr_dims_same
                jp   spr_core

spr_set3:                                   ; RIGHT (90 αριστερόστροφα)
                ld   a,(spr_w)
                dec  a
                ld   l,a
                ld   h,0                    ; start = W-1
                ld   a,(spr_w)
                ld   e,a
                ld   d,0                    ; dx = +W
                ld   bc,-1                  ; dy = -1
                call spr_store
                call spr_dims_swap
                ; πέφτει στο spr_core

;---------------------------------------------------------------------
spr_core:
                ; πλάτος εξόδου σε bytes = (dw + shift + 3) / 4
                ld   a,(spr_shift)
                and  3
                ld   (spr_shift),a
                ld   hl,spr_dw
                add  a,(hl)
                add  a,3
                srl  a                      ; srl, ΟΧΙ rra: το carry εδώ δεν είναι 0
                srl  a
                ld   (spr_bw),a
                ld   a,(spr_dh)
                ld   (spr_bh),a

                ; καθάρισμα buffer: mask=FF (κράτα το φόντο), data=00
                ld   hl,spr_buf
                ld   b,SPR_MAXW*SPR_MAXH
spr_clr:        ld   (hl),#FF
                inc  hl
                ld   (hl),0
                inc  hl
                djnz spr_clr

                ld   hl,(spr_srcbase)
                ld   de,(spr_start)
                add  hl,de
                ld   (spr_rowptr),hl
                ld   hl,spr_buf
                ld   (spr_rowdst),hl
                ld   a,(spr_dh)
                ld   (spr_rowcnt),a

spr_row:
                ld   hl,(spr_rowptr)        ; HL = τρέχον pixel της πηγής
                ld   ix,(spr_rowdst)        ; IX = τρέχον ζεύγος (mask,data)
                ld   a,(spr_shift)
                ld   e,a                    ; E = θέση pixel μέσα στο byte
                ld   a,(spr_dw)
                ld   b,a                    ; B = pixels της γραμμής

spr_pix:
                ld   a,(hl)
                and  3
                jr   z,spr_pix_next         ; pen 0 = διαφανές

                add  a,a                    ; data |= pixtab[pen*4 + slot]
                add  a,a
                add  a,e
                push hl
                ld   hl,spr_pixtab
                add  a,l
                ld   l,a
                adc  a,h
                sub  l
                ld   h,a
                ld   c,(hl)
                pop  hl
                ld   a,(ix+1)
                or   c
                ld   (ix+1),a

                push hl                     ; mask &= andtab[slot]
                ld   hl,spr_andtab
                ld   a,e
                add  a,l
                ld   l,a
                adc  a,h
                sub  l
                ld   h,a
                ld   c,(hl)
                pop  hl
                ld   a,(ix+0)
                and  c
                ld   (ix+0),a

spr_pix_next:
                inc  e                      ; κάθε 4 pixels -> επόμενο byte
                ld   a,e
                cp   4
                jr   nz,spr_pix_adv
                ld   e,0
                inc  ix
                inc  ix
spr_pix_adv:
                push de
                ld   de,(spr_dx)
                add  hl,de
                pop  de
                djnz spr_pix

                ld   hl,(spr_rowptr)        ; επόμενη γραμμή πηγής
                ld   de,(spr_dy)
                add  hl,de
                ld   (spr_rowptr),hl
                ld   hl,(spr_rowdst)        ; επόμενη γραμμή buffer
                ld   a,(spr_bw)
                add  a,a
                ld   e,a
                ld   d,0
                add  hl,de
                ld   (spr_rowdst),hl
                ld   hl,spr_rowcnt
                dec  (hl)
                jr   nz,spr_row
                ret

;--- βοηθητικά --------------------------------------------------------
spr_store:      ld   (spr_start),hl         ; HL=start, DE=dx, BC=dy
                ld   (spr_dx),de
                ld   (spr_dy),bc
                ret

spr_dims_same:  ld   a,(spr_w)              ; έξοδος W x H
                ld   (spr_dw),a
                ld   a,(spr_h)
                ld   (spr_dh),a
                ret

spr_dims_swap:  ld   a,(spr_h)              ; έξοδος H x W (περιστροφή 90)
                ld   (spr_dw),a
                ld   a,(spr_w)
                ld   (spr_dh),a
                ret

spr_mul:        ld   hl,0                   ; HL = B * C
                ld   a,b
                or   a
                ret  z
                ld   d,0
                ld   e,c
spr_mul_l:      add  hl,de
                dec  a
                jr   nz,spr_mul_l
                ret

;--- πίνακες MODE 1 (docs/sprites.md §3) ------------------------------
; θέση pixel s: bit(7-s) = bit0 του pen, bit(3-s) = bit1 του pen
spr_pixtab:     db #00,#00,#00,#00          ; pen 0
                db #80,#40,#20,#10          ; pen 1
                db #08,#04,#02,#01          ; pen 2
                db #88,#44,#22,#11          ; pen 3
spr_andtab:     db #77,#BB,#DD,#EE          ; καθαρίζει τη θέση s

;--- κατάσταση --------------------------------------------------------
spr_srcbase     dw 0        ; αρχή του unpacked frame
spr_start       dw 0        ; offset πρώτου pixel μέσα στο frame
spr_dx          dw 0        ; βήμα ανά pixel γραμμής (προσημασμένο)
spr_dy          dw 0        ; βήμα ανά γραμμή        (προσημασμένο)
spr_rowptr      dw 0
spr_rowdst      dw 0
spr_wh          dw 0        ; W*H
spr_w           db 0
spr_h           db 0
spr_dw          db 0        ; πλάτος εξόδου σε pixels
spr_dh          db 0        ; ύψος εξόδου σε γραμμές
spr_rowcnt      db 0
spr_orient      db 0        ; 0..3
spr_shift       db 0        ; 0..3 — γράψ' το ΠΡΙΝ την κλήση
spr_bw          db 0        ; ΕΞΟΔΟΣ: πλάτος σε bytes
spr_bh          db 0        ; ΕΞΟΔΟΣ: γραμμές (= spr_dh)

spr_buf         ds SPR_BUFSZ, 0
