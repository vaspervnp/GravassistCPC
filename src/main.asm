;=====================================================================
;  GRAVASSIST  -  Amstrad CPC 6128 - Z80 assembly - MODE 1
;
;  Puzzle game: ο παίκτης αλλάζει την κατεύθυνση της βαρύτητας για να
;  περπατάει σε πατώματα, τοίχους, ταβάνια και πλατφόρμες.
;
;  ΚΑΤΑΣΤΑΣΗ: σκελετός (M0). Προς το παρόν στήνει MODE 1 + παλέτα και
;  δείχνει τον ήρωα στις 4 φορές βαρύτητας για να φανεί ότι δουλεύει η
;  ρουτίνα περιστροφής. Το gameplay έρχεται στα M1+ (δες plan.md).
;
;  Load / exec: #4000
;=====================================================================

                org  #4000

;--- Firmware jumpblock ----------------------------------------------
SCR_SET_MODE    equ  #BC0E      ; A = mode (καθαρίζει την οθόνη)
SCR_SET_INK     equ  #BC32      ; A=pen, B=colour1, C=colour2
SCR_SET_BORDER  equ  #BC38      ; B=colour1, C=colour2
MC_WAIT_FLYBACK equ  #BD19      ; αναμονή flyback (sync 50 Hz)
KM_TEST_KEY     equ  #BB1E      ; A=key nr -> NZ αν πατημένο (ΧΑΛΑΕΙ A,C,F,HL)

K_ESC           equ  66

;--- Παλέτα (docs/concept-art.md §5) ---------------------------------
INK_BG          equ  1          ; σκούρο μπλε  - φόντο
INK_HERO        equ  26         ; λευκό        - ήρωας, HUD
INK_BODY        equ  18         ; πράσινο      - σώμα υλικού
INK_EDGE        equ  16         ; πορτοκαλί    - ακμές, κίνδυνος

;--- Οθόνη ------------------------------------------------------------
SCR_BASE        equ  #C000
SCR_WBYTES      equ  80         ; bytes ανά scanline σε MODE 1

;=====================================================================
main:
                ld   a,1
                call SCR_SET_MODE
                call set_palette

                call demo_orients       ; προσωρινή επίδειξη περιστροφής

main_wait:      call MC_WAIT_FLYBACK
                ld   a,K_ESC
                call KM_TEST_KEY
                jr   z,main_wait
                ret                     ; επιστροφή στη BASIC

;---------------------------------------------------------------------
; set_palette — τα 4 pens του MODE 1
;---------------------------------------------------------------------
set_palette:    ld   hl,palette
                ld   d,0                ; D = αριθμός pen
sp_loop:        ld   a,(hl)
                ld   b,a
                ld   c,a                ; χωρίς flashing: colour1 = colour2
                ld   a,d
                push de
                push hl
                call SCR_SET_INK
                pop  hl
                pop  de
                inc  hl
                inc  d
                ld   a,d
                cp   4
                jr   nz,sp_loop
                ld   b,INK_BG           ; border ίδιο με το φόντο
                ld   c,INK_BG
                jp   SCR_SET_BORDER

palette         db   INK_BG, INK_HERO, INK_BODY, INK_EDGE

;---------------------------------------------------------------------
; demo_orients — ο ήρωας (frame IDLE0) και στις 4 φορές βαρύτητας.
; Επιβεβαιώνει οπτικά ότι spr_transform + blit δουλεύουν.
;---------------------------------------------------------------------
demo_orients:   xor  a
do_loop:        push af
                ld   (do_orient),a

                ld   a,0                ; shift 0 προς το παρόν
                ld   (spr_shift),a
                ld   hl,hero_gfx        ; frame 0 = IDLE0
                ld   b,hero_gfx_w
                ld   c,hero_gfx_h
                ld   a,(do_orient)
                call spr_transform

                ld   a,(do_orient)      ; θέση: μία στήλη ανά φορά
                add  a,a
                add  a,a
                add  a,a
                add  a,10               ; X σε bytes: 10, 18, 26, 34
                ld   c,a
                ld   b,80               ; Y σε scanlines
                call blit_spr

                pop  af
                inc  a
                cp   4
                jr   nz,do_loop
                ret

do_orient       db   0

;---------------------------------------------------------------------
; blit_spr — ζωγραφίζει το spr_buf στην οθόνη
;   IN: C = X σε bytes (0..79), B = Y σε scanlines (0..199)
;   ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
blit_spr:       ld   a,(spr_bh)
                ld   (bs_rows),a
                ld   hl,spr_buf
                ld   (bs_src),hl

bs_row:         push bc
                call scr_addr           ; HL = διεύθυνση οθόνης για (C,B)
                ld   de,(bs_src)
                ld   a,(spr_bw)
                ld   b,a
bs_byte:        ld   a,(de)             ; mask
                inc  de
                ld   c,a
                ld   a,(hl)
                and  c
                ld   c,a
                ld   a,(de)             ; data
                inc  de
                or   c
                ld   (hl),a
                inc  hl
                djnz bs_byte
                ld   (bs_src),de
                pop  bc
                inc  b                  ; επόμενη scanline
                ld   hl,bs_rows
                dec  (hl)
                jr   nz,bs_row
                ret

bs_rows         db   0
bs_src          dw   0

;---------------------------------------------------------------------
; scr_addr — διεύθυνση οθόνης για (στήλη byte, scanline)
;   IN:  C = X σε bytes (0..79), B = Y σε scanlines (0..199)
;   OUT: HL = διεύθυνση
;   Διάταξη CPC: HL = base + (Y/8)*80 + (Y&7)*#800 + X
;---------------------------------------------------------------------
scr_addr:       ld   a,b                ; HL = (Y & 7) * #800
                and  7
                ld   h,a
                ld   l,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                push hl

                ld   a,b                ; DE = (Y >> 3) * 80
                srl  a
                srl  a
                srl  a
                ld   l,a
                ld   h,0
                add  hl,hl              ; x2
                add  hl,hl              ; x4
                add  hl,hl              ; x8
                add  hl,hl              ; x16
                ld   d,h
                ld   e,l
                add  hl,hl              ; x32
                add  hl,hl              ; x64
                add  hl,de              ; x64 + x16 = x80
                ex   de,hl

                pop  hl
                add  hl,de
                ld   e,c                ; + X σε bytes
                ld   d,0
                add  hl,de
                ld   de,SCR_BASE
                add  hl,de
                ret

;--- δεδομένα ---------------------------------------------------------
                include "rotate.asm"
                include "gfx_hero.asm"
                include "gfx_objects.asm"

prog_end
                save 'build/main.bin', #4000, prog_end-#4000
