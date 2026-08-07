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
                call init_linetab
                call render_room

                ld   hl,60              ; αρχική θέση: πέφτει στο πάτωμα
                ld   (hero_x),hl
                ld   hl,40
                ld   (hero_y),hl
                xor  a
                ld   (hero_g),a
                ld   a,HST_FALL
                ld   (hero_state),a
                call prep_hero
                call draw_hero

; Ο βρόχος υπολογίζει ΠΡΩΤΑ και ζωγραφίζει ΜΕΤΑ το flyback. Ανάποδα, η
; φυσική (εκατοντάδες solid_at) έτρεχε ανάμεσα στο σβήσιμο και τη σχεδίαση
; και ο ήρωας έλειπε από την οθόνη για το μεγαλύτερο μέρος του frame.
main_loop:      call read_gravity       ; ο παίκτης ρίχνει τη βαρύτητα
                jr   c,ml_walk
                ld   (hero_g),a
                ld   a,HST_FALL         ; αλλαγή φοράς -> ξαναμετράει η πτώση
                ld   (hero_state),a
ml_walk:        call read_walk
                call hero_update
                call anim_frame
                call prep_hero          ; μετασχηματισμός sprite (εκτός vblank)

                call MC_WAIT_FLYBACK
                call draw_hero          ; μόνο εγγραφές στην οθόνη

                ld   a,K_ESC
                call KM_TEST_KEY
                jr   z,main_loop
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
; prep_hero — μετασχηματισμός sprite και θέση. Τρέχει ΕΚΤΟΣ vblank και δεν
; αγγίζει την οθόνη, ώστε στο vblank να μένουν μόνο εγγραφές.
;---------------------------------------------------------------------
prep_hero:      ld   a,(hero_g)         ; διαστάσεις sprite για αυτή τη φορά
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,hero_dims
                add  hl,de
                ld   c,(hl)             ; C = πλάτος px
                inc  hl
                ld   b,(hl)             ; B = ύψος γραμμές

                ld   a,c                ; px = hero_x - πλάτος/2 (θέση = ΚΕΝΤΡΟ)
                srl  a
                ld   e,a
                ld   d,0
                ld   hl,(hero_x)
                or   a
                sbc  hl,de
                push hl

                ld   a,b                ; py = hero_y - ύψος/2
                srl  a
                ld   e,a
                ld   d,0
                ld   hl,(hero_y)
                or   a
                sbc  hl,de
                ld   a,l
                ld   (spr_y),a

                pop  hl                 ; MODE 1: 4 pixels ανά byte
                ld   a,l
                and  3
                ld   (spr_shift),a
                srl  h
                rr   l
                srl  h
                rr   l
                ld   a,l
                ld   (spr_col),a

                ld   a,(anim_cur)
                ld   b,a
                ld   a,(hero_g)
                jp   hero_transform     ; A = φορά, B = frame

; Διαστάσεις sprite ανά φορά βαρύτητας (πλάτος px, ύψος γραμμές)
hero_dims       db   7,12, 13,13, 12,7, 13,13
                db   7,12, 13,13, 12,7, 13,13
spr_col         db   0
spr_y           db   0

;---------------------------------------------------------------------
; draw_hero — φόντο και sprite σε ΜΙΑ πέραση, ΧΩΡΙΣ φάση σβησίματος.
;
; Για κάθε byte υπολογίζεται το φόντο από τα δεδομένα της πίστας και
; συντίθεται από πάνω το sprite στην ΙΔΙΑ εγγραφή. Κανένα pixel δεν μένει
; ποτέ κενό — εκεί ήταν το flicker, όχι στον συγχρονισμό.
;
; Η περιοχή είναι η ΕΝΩΣΗ παλιάς και νέας θέσης, ώστε να σβήνει μαζί και το
; ίχνος της προηγούμενης χωρίς δεύτερο πέρασμα.
;---------------------------------------------------------------------
draw_hero:      ld   a,(last_bw)
                or   a
                jr   nz,dh_union
                call dh_remember        ; πρώτο frame: ένωση με τον εαυτό της

dh_union:       ld   a,(spr_col)        ; c0 = min(νέο, παλιό)
                ld   hl,last_col
                cp   (hl)
                jr   c,dh_c0a
                ld   a,(hl)
dh_c0a:         ld   (dh_c0),a

                ld   a,(spr_col)        ; c1 = max(τέλος) - 1
                ld   hl,spr_bw
                add  a,(hl)
                ld   c,a
                ld   a,(last_col)
                ld   hl,last_bw
                add  a,(hl)
                cp   c
                jr   nc,dh_c1a
                ld   a,c
dh_c1a:         dec  a
                ld   (dh_c1),a
                ld   hl,dh_c0
                sub  (hl)
                inc  a                  ; πλάτος περιοχής σε bytes
                cp   17                 ; ΦΡΑΓΜΑ: τα pivot γωνίας μετακινούν τον
                jr   c,dh_wok           ; ήρωα ~12 px σε ένα frame· χωρίς αυτό η
                ld   a,16               ; ένωση μπορεί να ξεπεράσει το linebuf
dh_wok:         ld   (dh_w),a

                ld   a,(spr_y)          ; y0 = min
                ld   hl,last_y
                cp   (hl)
                jr   c,dh_y0a
                ld   a,(hl)
dh_y0a:         ld   (dh_yy),a

                ld   a,(spr_y)          ; y1 = max(τέλος) - 1
                ld   hl,spr_bh
                add  a,(hl)
                ld   c,a
                ld   a,(last_y)
                ld   hl,last_bh
                add  a,(hl)
                cp   c
                jr   nc,dh_y1a
                ld   a,c
dh_y1a:         dec  a
                ld   (dh_y1),a

dh_line:        call dh_bgline          ; φόντο -> linebuf
                call dh_sprline         ; sprite από πάνω
                ld   a,(dh_yy)
                ld   b,a
                ld   a,(dh_c0)
                ld   c,a
                call scr_addr
                ex   de,hl
                ld   hl,linebuf
                ld   a,(dh_w)
                ld   c,a
                ld   b,0
                ldir                    ; μία εγγραφή ανά byte, χωρίς ενδιάμεσο κενό
                ld   hl,dh_yy
                inc  (hl)
                ld   a,(hl)
                ld   hl,dh_y1
                cp   (hl)
                jr   z,dh_line
                jr   c,dh_line

dh_remember:    ld   a,(spr_col)
                ld   (last_col),a
                ld   a,(spr_y)
                ld   (last_y),a
                ld   a,(spr_bw)
                ld   (last_bw),a
                ld   a,(spr_bh)
                ld   (last_bh),a
                ret

;--- φόντο μιας γραμμής από τα δεδομένα της πίστας --------------------
; Κάθε byte της οθόνης ανήκει σε ΑΚΡΙΒΩΣ ένα κελί (8 px = 2 bytes), οπότε
; δεν χρειάζεται σύνθεση γειτόνων: byte = tile_gfx[τύπος*16 + γραμμή*2 + μισό]
dh_bgline:      ld   a,(dh_yy)
                sub  LVL_Y0
                jr   nc,dhb_in
                ld   hl,linebuf         ; πάνω από το grid = ζώνη HUD
                ld   a,(dh_w)
                ld   b,a
                xor  a
dhb_clr:        ld   (hl),a
                inc  hl
                djnz dhb_clr
                ret

dhb_in:         ld   c,a
                and  7
                add  a,a
                ld   (dhb_off),a        ; γραμμή μέσα στο tile, x2 bytes
                ld   a,c
                srl  a
                srl  a
                srl  a
                ld   l,a                ; HL = level_data + row*40
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ld   d,h
                ld   e,l
                add  hl,hl
                add  hl,hl
                add  hl,de
                ld   de,level_data
                add  hl,de
                ld   a,(dh_c0)
                srl  a
                ld   e,a
                ld   d,0
                add  hl,de              ; HL -> τύπος του πρώτου κελιού
                ld   a,(dh_c0)
                and  1
                ld   (dhb_half),a
                ld   de,linebuf
                ld   a,(dh_w)
                ld   b,a

dhb_lp:         ld   a,(hl)             ; τύπος*16 + offset + μισό  (<= 95)
                add  a,a
                add  a,a
                add  a,a
                add  a,a
                ld   c,a
                ld   a,(dhb_off)
                add  a,c
                ld   c,a
                ld   a,(dhb_half)
                add  a,c
                push hl
                ld   l,a
                ld   h,0
                push de
                ld   de,tile_gfx
                add  hl,de
                ld   a,(hl)
                pop  de
                ld   (de),a
                inc  de
                pop  hl
                ld   a,(dhb_half)       ; κάθε 2 bytes -> επόμενο κελί
                xor  1
                ld   (dhb_half),a
                jr   nz,dhb_next
                inc  hl
dhb_next:       djnz dhb_lp
                ret

;--- σύνθεση του sprite πάνω στο linebuf ------------------------------
dh_sprline:     ld   a,(dh_yy)
                ld   hl,spr_y
                sub  (hl)
                ret  c                  ; η γραμμή είναι πάνω από το sprite
                ld   hl,spr_bh
                cp   (hl)
                ret  nc                 ; ή κάτω από αυτό

                ld   b,a                ; HL = spr_buf + γραμμή*spr_bw*2
                ld   a,(spr_bw)
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,spr_buf
                inc  b
                jr   dhs_chk
dhs_mul:        add  hl,de
dhs_chk:        djnz dhs_mul

                ld   a,(spr_col)        ; DE = linebuf + (spr_col - c0)
                ld   c,a
                ld   a,(dh_c0)
                ld   b,a
                ld   a,c
                sub  b
                ld   e,a
                ld   d,0
                push hl
                ld   hl,linebuf
                add  hl,de
                ex   de,hl
                pop  hl
                ld   a,(spr_bw)
                ld   b,a
dhs_lp:         ld   a,(de)
                and  (hl)               ; mask: κράτα το φόντο
                inc  hl
                or   (hl)               ; data: βάλε τον ήρωα
                inc  hl
                ld   (de),a
                inc  de
                djnz dhs_lp
                ret

last_col        db   0
last_y          db   0
last_bw         db   0
last_bh         db   0
dh_c0           db   0
dh_c1           db   0
dh_w            db   0
dh_yy           db   0
dh_y1           db   0
dhb_off         db   0
dhb_half        db   0
linebuf         ds   16, 0

;---------------------------------------------------------------------
; scr_addr — διεύθυνση οθόνης για (στήλη byte, scanline)
;   IN: C = X σε bytes, B = Y σε scanlines    OUT: HL = διεύθυνση
;   Lookup αντί για υπολογισμό: καλείται εκατοντάδες φορές ανά frame και ο
;   υπολογισμός με ολισθήσεις κόστιζε 4x περισσότερο.
;---------------------------------------------------------------------
scr_addr:       ld   l,b
                ld   h,0
                add  hl,hl
                ld   de,linetab
                add  hl,de
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                ld   l,c
                ld   h,0
                add  hl,de
                ret

;---------------------------------------------------------------------
; init_linetab — χτίζει τον πίνακα διευθύνσεων των 200 scanlines
;   Διάταξη CPC: base + (Y/8)*80 + (Y&7)*#800
;---------------------------------------------------------------------
init_linetab:   ld   hl,linetab
                ld   b,0
ilt_lp:         push hl
                push bc

                ld   a,b                ; HL = (Y & 7) * #800
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
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ld   d,h
                ld   e,l
                add  hl,hl
                add  hl,hl
                add  hl,de              ; x64 + x16 = x80
                ex   de,hl
                pop  hl
                add  hl,de
                ld   de,SCR_BASE
                add  hl,de

                ex   de,hl
                pop  bc
                pop  hl
                ld   (hl),e
                inc  hl
                ld   (hl),d
                inc  hl
                inc  b
                ld   a,b
                cp   200
                jr   nz,ilt_lp
                ret

linetab         ds   400, 0

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
