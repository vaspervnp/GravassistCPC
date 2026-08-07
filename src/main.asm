;=====================================================================
;  GRAVASSIST  -  Amstrad CPC 6128 - Z80 assembly - MODE 1
;
;  Puzzle game: ο παίκτης αλλάζει την κατεύθυνση της βαρύτητας για να
;  περπατάει σε πατώματα, τοίχους, ταβάνια και ράμπες.
;
;  ΚΑΤΑΣΤΑΣΗ: δοκιμαστικό δωμάτιο με πλήρη φυσική. Το μοντέλο είναι
;  επαληθευμένο σε Python (make test)· αυτό εδώ είναι η μεταγραφή του.
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
; Βαρύτητα: δύο ισοδύναμα σετ των 8, το καθένα σε πλέγμα 3x3 όπου η ΘΕΣΗ
; του πλήκτρου είναι η κατεύθυνση. Το κέντρο μένει αχρησιμοποίητο.
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
K_N             equ  46         ; βάδισμα πίσω  (σχετικά με τον ήρωα)
K_M             equ  38         ; βάδισμα μπροστά

;--- Φορές βαρύτητας (docs/sprites.md §2) ----------------------------
GRAV_DOWN       equ  0
GRAV_DOWNLEFT   equ  1
GRAV_LEFT       equ  2
GRAV_UPLEFT     equ  3
GRAV_UP         equ  4
GRAV_UPRIGHT    equ  5
GRAV_RIGHT      equ  6
GRAV_DOWNRIGHT  equ  7

;--- Κανόνες παιχνιδιού (plan.md §2.2, §2.4) -------------------------
FALL_SAFE       equ  36         ; 3 x ύψος ήρωα· πάνω από αυτό, ζημιά
ENERGY_MAX      equ  8

;--- Παλέτα (docs/concept-art.md §5) ---------------------------------
INK_BG          equ  1          ; σκούρο μπλε  - φόντο
INK_HERO        equ  26         ; λευκό        - ήρωας, HUD
INK_BODY        equ  18         ; πράσινο      - σώμα υλικού
INK_EDGE        equ  16         ; πορτοκαλί    - ακμές, κίνδυνος

;--- Οθόνη ------------------------------------------------------------
SCR_BASE        equ  #C000
SCR_WBYTES      equ  80         ; bytes ανά scanline σε MODE 1

;=====================================================================
main:           ld   a,1
                call SCR_SET_MODE
                call set_palette
                call render_room

                ld   hl,60              ; αρχική θέση: πέφτει στο πάτωμα
                ld   (hero_x),hl
                ld   hl,40
                ld   (hero_y),hl
                xor  a
                ld   (hero_g),a
                ld   a,HST_FALL
                ld   (hero_state),a
                call draw_hero

main_loop:      call MC_WAIT_FLYBACK

                call read_gravity       ; ο παίκτης ρίχνει τη βαρύτητα
                jr   c,ml_walk
                ld   (hero_g),a
                ld   a,HST_FALL         ; αλλαγή φοράς -> ξαναμετράει η πτώση
                ld   (hero_state),a
ml_walk:        call read_walk          ; A = -1 / 0 / +1
                ld   (ml_dir),a

                call erase_hero
                ld   a,(ml_dir)
                call hero_update
                call anim_frame
                call draw_hero

                ld   a,K_ESC
                call KM_TEST_KEY
                jr   z,main_loop
                ret                     ; επιστροφή στη BASIC

ml_dir          db   0

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
; read_gravity — σαρώνει τα 16 πλήκτρα βαρύτητας
;   OUT: NC και A = φορά 0..7 αν πατήθηκε κάποιο, CY αν κανένα
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
; read_walk — M / N· πάντα ΣΧΕΤΙΚΑ με τον προσανατολισμό του ήρωα
;   OUT: A = +1 (M), -1 (N), 0
;---------------------------------------------------------------------
read_walk:      ld   a,K_M
                call KM_TEST_KEY
                jr   z,rw_n
                ld   a,1
                ret
rw_n:           ld   a,K_N
                call KM_TEST_KEY
                jr   z,rw_none
                ld   a,-1
                ret
rw_none:        xor  a
                ret

;---------------------------------------------------------------------
; anim_frame — διαλέγει frame ανάλογα με την κατάσταση
;---------------------------------------------------------------------
anim_frame:     ld   hl,anim_tick
                inc  (hl)
                ld   a,(hero_state)
                cp   HST_WALK
                jr   z,af_walk
                cp   HST_FALL
                jr   z,af_fall
                ld   a,(anim_tick)      ; IDLE: 2 frames, αργά
                rrca
                rrca
                rrca
                rrca
                rrca
                and  1
                jr   af_set
af_walk:        ld   a,(anim_tick)      ; WALK: 8 frames, ένα ανά 4
                rrca
                rrca
                and  7
                add  a,2
                jr   af_set
af_fall:        ld   a,(anim_tick)      ; FALL: 4 frames
                rrca
                rrca
                rrca
                and  3
                add  a,18
af_set:         ld   (anim_cur),a
                ret

anim_tick       db   0
anim_cur        db   0

;---------------------------------------------------------------------
; draw_hero — μετασχηματίζει και ζωγραφίζει τον ήρωα στη θέση του
;   Η θέση είναι το ΚΕΝΤΡΟ του σώματος, οπότε το sprite κεντράρεται.
;---------------------------------------------------------------------
draw_hero:      ld   a,(hero_g)         ; διαστάσεις sprite για αυτή τη φορά
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,hero_dims
                add  hl,de
                ld   c,(hl)             ; C = πλάτος σε pixels
                inc  hl
                ld   b,(hl)             ; B = ύψος σε γραμμές

                ld   a,c                ; px = hero_x - πλάτος/2
                srl  a
                ld   e,a
                ld   d,0
                ld   hl,(hero_x)
                or   a
                sbc  hl,de
                ld   (dh_px),hl

                ld   a,b                ; py = hero_y - ύψος/2
                srl  a
                ld   e,a
                ld   d,0
                ld   hl,(hero_y)
                or   a
                sbc  hl,de
                ld   a,l
                ld   (dh_py),a

                ld   hl,(dh_px)         ; MODE 1: 4 pixels ανά byte
                ld   a,l
                and  3
                ld   (spr_shift),a
                srl  h
                rr   l
                srl  h
                rr   l
                ld   a,l
                ld   (dh_col),a

                ld   a,(hero_g)
                ld   b,a
                ld   a,(anim_cur)
                ld   c,a
                ld   a,b
                ld   b,c
                call hero_transform     ; A = φορά, B = frame

                ld   a,(dh_col)
                ld   c,a
                ld   a,(dh_py)
                ld   b,a
                call blit_spr

                ld   a,(dh_col)         ; θυμήσου το ορθογώνιο για το σβήσιμο
                ld   (last_col),a
                ld   a,(dh_py)
                ld   (last_y),a
                ld   a,(spr_bw)
                ld   (last_bw),a
                ld   a,(spr_bh)
                ld   (last_bh),a
                ret

dh_px           dw   0
dh_py           db   0
dh_col          db   0

; Διαστάσεις sprite ανά φορά βαρύτητας (πλάτος px, ύψος γραμμές)
hero_dims       db   7,12, 13,13, 12,7, 13,13
                db   7,12, 13,13, 12,7, 13,13

;---------------------------------------------------------------------
; erase_hero — ξαναζωγραφίζει τα κελιά κάτω από την προηγούμενη θέση
;---------------------------------------------------------------------
erase_hero:     ld   a,(last_bh)
                or   a
                ret  z                  ; δεν έχει ζωγραφιστεί ακόμα

                ld   a,(last_col)       ; στήλες κελιών: byte/2
                srl  a
                ld   (eh_c0),a
                ld   a,(last_col)
                ld   hl,last_bw
                add  a,(hl)
                dec  a
                srl  a
                ld   (eh_c1),a

                ld   a,(last_y)         ; γραμμές κελιών
                sub  LVL_Y0
                jr   nc,eh_r0
                xor  a
eh_r0:          srl  a
                srl  a
                srl  a
                ld   (eh_row),a
                ld   a,(last_y)
                ld   hl,last_bh
                add  a,(hl)
                dec  a
                sub  LVL_Y0
                srl  a
                srl  a
                srl  a
                cp   LVL_ROWS
                jr   c,eh_r1
                ld   a,LVL_ROWS-1
eh_r1:          ld   (eh_r1v),a

eh_rowlp:       ld   a,(eh_c0)
                ld   (eh_col),a
eh_collp:       ld   a,(eh_col)
                cp   LVL_COLS
                jr   nc,eh_nextrow
                ld   c,a
                ld   a,(eh_row)
                ld   b,a
                call draw_tile
                ld   hl,eh_col
                inc  (hl)
                ld   a,(hl)
                ld   hl,eh_c1
                cp   (hl)
                jr   z,eh_collp
                jr   c,eh_collp
eh_nextrow:     ld   hl,eh_row
                inc  (hl)
                ld   a,(hl)
                ld   hl,eh_r1v
                cp   (hl)
                jr   z,eh_rowlp
                jr   c,eh_rowlp
                ret

last_col        db   0
last_y          db   0
last_bw         db   0
last_bh         db   0
eh_c0           db   0
eh_c1           db   0
eh_row          db   0
eh_r1v          db   0
eh_col          db   0

;---------------------------------------------------------------------
; blit_spr — ζωγραφίζει το spr_buf στην οθόνη
;   IN: C = X σε bytes (0..79), B = Y σε scanlines (0..199)
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

;--- υποσυστήματα -----------------------------------------------------
                include "rotate.asm"
                include "tables.asm"
                include "level.asm"
                include "hero.asm"

;--- δεδομένα ---------------------------------------------------------
                include "gfx_hero.asm"
                include "gfx_hero45.asm"
                include "gfx_objects.asm"
                include "level_test.asm"

prog_end
                save 'build/main.bin', #4000, prog_end-#4000
