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

;--- Πλήκτρα (firmware key numbers) ----------------------------------
; Δύο ισοδύναμα σετ των 8, το καθένα σε πλέγμα 3x3 με αχρησιμοποίητο κέντρο:
;       Q W E          F7 F8 F9
;       A . D          F4 F5 F6
;       Z X C          F1 F2 F3
K_ESC           equ  66
K_Q             equ  67
K_W             equ  59
K_E             equ  58
K_A             equ  69
K_D             equ  61
K_Z             equ  71
K_X             equ  63
K_C             equ  62
K_F7            equ  10
K_F8            equ  11
K_F9            equ  3
K_F4            equ  20
K_F6            equ  4
K_F1            equ  13
K_F2            equ  14
K_F3            equ  5

;--- Φορές βαρύτητας (docs/sprites.md §2) ----------------------------
GRAV_DOWN       equ  0
GRAV_DOWNLEFT   equ  1
GRAV_LEFT       equ  2
GRAV_UPLEFT     equ  3
GRAV_UP         equ  4
GRAV_UPRIGHT    equ  5
GRAV_RIGHT      equ  6
GRAV_DOWNRIGHT  equ  7

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

                call demo_orients       ; η σειρά αναφοράς: και οι 8 φορές
                ld   a,GRAV_DOWN
                ld   (cur_grav),a
                call draw_live

;--- Βρόχος επίδειξης: τα πλήκτρα βαρύτητας γυρίζουν τον κάτω ήρωα ----
main_loop:      call MC_WAIT_FLYBACK
                call read_gravity
                jr   c,ml_esc           ; τίποτα πατημένο
                ld   hl,cur_grav
                cp   (hl)
                jr   z,ml_esc           ; ίδια φορά, μην ξαναζωγραφίζεις
                ld   (hl),a
                call draw_live
ml_esc:         ld   a,K_ESC
                call KM_TEST_KEY
                jr   z,main_loop
                ret                     ; επιστροφή στη BASIC

cur_grav        db   0

;---------------------------------------------------------------------
; read_gravity — σαρώνει τα 16 πλήκτρα βαρύτητας
;   OUT: NC και A = φορά 0..7 αν πατήθηκε κάποιο, CY αν κανένα
;   ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;   (το KM_TEST_KEY χαλάει A, C, F, HL — γι' αυτό τα push/pop)
;---------------------------------------------------------------------
read_gravity:   ld   hl,grav_keys
                ld   b,0                ; B = φορά βαρύτητας
rg_dir:         ld   c,2                ; δύο ισοδύναμα πλήκτρα ανά φορά
rg_key:         ld   a,(hl)
                push hl
                push bc
                call KM_TEST_KEY
                pop  bc
                pop  hl
                jr   nz,rg_hit
                inc  hl
                dec  c
                jr   nz,rg_key
                inc  b
                ld   a,b
                cp   8
                jr   nz,rg_dir
                scf                     ; κανένα πατημένο
                ret
rg_hit:         ld   a,b
                or   a                  ; καθαρίζει το carry
                ret

; Η σειρά ΠΡΕΠΕΙ να ακολουθεί τους κωδικούς φοράς GRAV_*
grav_keys       db   K_X, K_F2          ; 0 DOWN
                db   K_Z, K_F1          ; 1 DOWN-LEFT
                db   K_A, K_F4          ; 2 LEFT
                db   K_Q, K_F7          ; 3 UP-LEFT
                db   K_W, K_F8          ; 4 UP
                db   K_E, K_F9          ; 5 UP-RIGHT
                db   K_D, K_F6          ; 6 RIGHT
                db   K_C, K_F3          ; 7 DOWN-RIGHT

;---------------------------------------------------------------------
; draw_live — ξαναζωγραφίζει τον διαδραστικό ήρωα στη φορά (cur_grav)
;---------------------------------------------------------------------
LIVE_X          equ  38                 ; στήλη byte
LIVE_Y          equ  130                ; scanline

draw_live:      ld   c,LIVE_X           ; σβήσε πρώτα το προηγούμενο
                ld   b,LIVE_Y
                call clear_box
                xor  a
                ld   (spr_shift),a
                ld   a,(cur_grav)
                ld   b,0                ; frame IDLE0
                call hero_transform
                ld   c,LIVE_X
                ld   b,LIVE_Y
                jp   blit_spr

;---------------------------------------------------------------------
; clear_box — καθαρίζει SPR_MAXW bytes x SPR_MAXH γραμμές σε pen 0
;   IN: C = X σε bytes, B = Y σε scanlines
;---------------------------------------------------------------------
clear_box:      ld   a,SPR_MAXH
                ld   (cb_rows),a
cb_row:         push bc
                call scr_addr
                ld   b,SPR_MAXW
                xor  a
cb_byte:        ld   (hl),a
                inc  hl
                djnz cb_byte
                pop  bc
                inc  b
                ld   hl,cb_rows
                dec  (hl)
                jr   nz,cb_row
                ret

cb_rows         db   0

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

                xor  a
                ld   (spr_shift),a      ; shift 0 προς το παρόν
                ld   a,(do_orient)
                ld   b,0                ; frame 0 = IDLE0
                call hero_transform

                ld   a,(do_orient)      ; θέση: μία στήλη ανά φορά
                add  a,a                ; x2
                add  a,a                ; x4
                add  a,a                ; x8
                ld   c,a
                ld   a,(do_orient)
                add  a,c                ; x9 -> απόσταση 9 bytes = 36 pixels
                add  a,4                ; X σε bytes: 4, 13, 22, ... 67
                ld   c,a
                ld   b,60               ; Y σε scanlines
                call blit_spr

                pop  af
                inc  a
                cp   8
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
                include "gfx_hero45.asm"
                include "gfx_objects.asm"

prog_end
                save 'build/main.bin', #4000, prog_end-#4000
