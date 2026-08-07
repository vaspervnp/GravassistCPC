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

; Παραγόμενοι ορισμοί (κωδικοί τύπων, μεγέθη). ΠΡΩΤΑ απ' όλα: τα `ds` των
; buffers χρειάζονται τις τιμές ήδη στο πρώτο πέρασμα.
                include "gamedefs.asm"

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
K_LEFT          equ  8          ; ισοδύναμα με N
K_RIGHT         equ  1          ; ισοδύναμα με M
K_SHIFT         equ  21         ; κρατημένο = τρέξιμο

;--- Δικλείδα ακινησίας ----------------------------------------------
STUCK_FRAMES    equ  5          ; πόσα frames κοιτάμε πίσω
STUCK_PX        equ  6          ; μέγιστη μετατόπιση ανά άξονα για "ακίνητος"

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
;--- Παλέτα (docs/concept-art.md §5) ---------------------------------
INK_BG          equ  1          ; σκούρο μπλε  - φόντο
INK_HERO        equ  26         ; λευκό        - ήρωας, HUD
INK_BODY        equ  18         ; πράσινο      - σώμα υλικού
INK_EDGE        equ  16         ; πορτοκαλί    - ακμές, κίνδυνος

;--- Οθόνη ------------------------------------------------------------
; --- HUD: πάνω 8 scanlines, πάνω από το grid της πίστας ---------------
HUD_X           equ  2          ; στήλη byte της μπάρας
HUD_Y           equ  2          ; πρώτη scanline
HUD_H           equ  4          ; ύψος σε γραμμές
HUD_SEG         equ  2          ; bytes ανά μονάδα ενέργειας
HUD_PARA_X      equ  24         ; στήλη byte του εικονιδίου αλεξίπτωτου
BYTE_PEN2       equ  #0F        ; 4 pixels pen2 (πράσινο)
BYTE_PEN3       equ  #FF        ; 4 pixels pen3 (πορτοκαλί)
LOW_ENERGY      equ  3          ; κάτω από αυτό, η μπάρα κοκκινίζει

LINEBUF_W         equ  24     ; πλάτος buffer γραμμής σε bytes
SCR_BASE        equ  #C000
SCR_WBYTES      equ  80         ; bytes ανά scanline σε MODE 1

;=====================================================================
main:           ld   a,1
                call SCR_SET_MODE
                call set_palette
                call init_linetab
                call render_room
                ld   a,1
                ld   (hud_dirty),a

                ld   hl,LVL_START_X     ; θέση και φορά από το αρχείο πίστας
                ld   (hero_x),hl
                ld   hl,LVL_START_Y
                ld   (hero_y),hl
                ld   a,LVL_START_G
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
                ld   b,a                ; φύλαξε τη φορά

                ; ΣΤΟΝ ΑΕΡΑ ΔΕΝ ΑΛΛΑΖΕΙ ΦΟΡΑ. Κάθε flip γίνεται έτσι δεσμευτική
                ; απόφαση: διαλέγεις πριν φύγεις, δεν διορθώνεις πέφτοντας.
                ;
                ; ΕΞΑΙΡΕΣΗ: αν έχει μείνει ουσιαστικά ακίνητος (καμία μετατόπιση
                ; πάνω από STUCK_PX σε κανέναν άξονα για STUCK_FRAMES frames),
                ; ξαναπαίρνει τον έλεγχο. Αλλιώς ένας ήρωας που γλιστράει
                ; ατέρμονα ή σφηνώνει θα έμενε για πάντα χωρίς επιλογές.
                ld   a,(hero_state)
                cp   HST_FALL
                jr   nz,ml_gok
                call h_stuck
                jr   nc,ml_walk

ml_gok:         ld   a,b
                call h_noflip           ; ...ούτε σε ζώνη κλειδώματος
                jr   c,ml_walk
                ld   (hero_g),a
                ld   a,HST_FALL         ; αλλαγή φοράς -> ξαναμετράει η πτώση
                ld   (hero_state),a
ml_walk:        call read_walk
                ld   (ml_dir),a
                call hero_update

                ; ΤΡΕΞΙΜΟ: δεύτερο ΠΛΗΡΕΣ βήμα φυσικής, όχι βήμα 2 pixels.
                ; Με βήμα 2 pixels ο ήρωας θα προσπερνούσε ακμές και ράμπες —
                ; το μοντέλο ανιχνεύει γωνίες και κλίσεις ανά pixel.
                xor  a
                ld   (ml_run),a
                ld   a,(ml_dir)
                or   a
                jr   z,ml_anim          ; τρέξιμο μόνο όταν περπατάει
                ld   a,K_SHIFT
                call KM_TEST_KEY
                jr   z,ml_anim
                ld   a,1
                ld   (ml_run),a
                ld   a,(ml_dir)
                call hero_update

ml_anim:        call anim_frame
                call prep_hero          ; μετασχηματισμός sprite (εκτός vblank)

                call MC_WAIT_FLYBACK
                call draw_hero          ; μόνο εγγραφές στην οθόνη
                call draw_hud

                ld   a,K_ESC
                call KM_TEST_KEY
                jr   z,main_loop
                ret                     ; επιστροφή στη BASIC

ml_dir          db   0
ml_run          db   0

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
; read_walk — M/N ή τα βελάκια· πάντα ΣΧΕΤΙΚΑ με τον προσανατολισμό
;             του ήρωα, όχι με την οθόνη
;   OUT: A = +1 (M), -1 (N), 0
;---------------------------------------------------------------------
read_walk:      ld   a,K_M
                call KM_TEST_KEY
                jr   nz,rw_fwd
                ld   a,K_RIGHT
                call KM_TEST_KEY
                jr   nz,rw_fwd
                ld   a,K_N
                call KM_TEST_KEY
                jr   nz,rw_back
                ld   a,K_LEFT
                call KM_TEST_KEY
                jr   nz,rw_back
                xor  a
                ret
rw_fwd:         ld   a,1
                ret
rw_back:        ld   a,-1
                ret

;---------------------------------------------------------------------
; anim_frame — διαλέγει frame ανάλογα με την κατάσταση
;---------------------------------------------------------------------
anim_frame:     ld   hl,anim_tick
                inc  (hl)
                ld   a,(ml_run)         ; στο τρέξιμο, διπλάσιος ρυθμός καρέ
                or   a
                jr   z,af_state
                inc  (hl)
af_state:
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
; draw_hud — μπάρα ενέργειας και εικονίδιο αλεξίπτωτου
;   Ζωγραφίζει ΜΟΝΟ όταν κάτι άλλαξε: το HUD είναι στατικό τις περισσότερες
;   στιγμές και δεν αξίζει 40 bytes εγγραφών ανά frame.
;---------------------------------------------------------------------
draw_hud:       ld   a,(hud_dirty)
                or   a
                ret  z
                xor  a
                ld   (hud_dirty),a

                ld   a,(hero_energy)    ; χαμηλή ενέργεια -> πορτοκαλί
                ld   b,BYTE_PEN2
                cp   LOW_ENERGY
                jr   nc,dhd_col
                ld   b,BYTE_PEN3
dhd_col:        ld   c,a                ; C = γεμάτες μονάδες
                ld   hl,hudbuf
                ld   d,ENERGY_MAX
dhd_seg:        ld   a,c
                or   a
                jr   z,dhd_empty
                dec  c
                ld   a,b
                jr   dhd_put
dhd_empty:      xor  a
dhd_put:        ld   (hl),a
                inc  hl
                ld   (hl),a
                inc  hl
                dec  d
                jr   nz,dhd_seg

                ld   a,HUD_H
                ld   (dhd_rows),a
                ld   b,HUD_Y
dhd_line:       push bc
                ld   c,HUD_X
                call scr_addr
                ex   de,hl
                ld   hl,hudbuf
                ld   bc,ENERGY_MAX*HUD_SEG
                ldir
                pop  bc
                inc  b
                ld   hl,dhd_rows
                dec  (hl)
                jr   nz,dhd_line

                ; εικονίδιο αλεξίπτωτου: το tile γραφικό του, 8 γραμμές
                ld   hl,tile_gfx+T_PARACHUTE*16
                ld   a,(hero_para)
                or   a
                jr   nz,dhd_para
                ld   hl,tile_gfx        ; κενό tile = σβήσιμο
dhd_para:       ld   (dhd_gfx),hl
                ld   a,8
                ld   (dhd_rows),a
                ld   b,0
dhd_pline:      push bc
                ld   c,HUD_PARA_X
                call scr_addr
                ex   de,hl
                ld   hl,(dhd_gfx)
                ldi
                ldi
                ld   (dhd_gfx),hl
                pop  bc
                inc  b
                ld   hl,dhd_rows
                dec  (hl)
                jr   nz,dhd_pline
                ret

hud_dirty       db   1
dhd_rows        db   0
dhd_gfx         dw   0
hudbuf          ds   ENERGY_MAX*HUD_SEG, 0

;---------------------------------------------------------------------
; prep_hero — μετασχηματισμός sprite και θέση. Τρέχει ΕΚΤΟΣ vblank και δεν
; αγγίζει την οθόνη, ώστε στο vblank να μένουν μόνο εγγραφές.
;---------------------------------------------------------------------
prep_hero:      call prep_para          ; ΠΡΩΤΑ: γράφει στο spr_buf και το φυλάει
                ld   a,(hero_g)         ; διαστάσεις sprite για αυτή τη φορά
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

;---------------------------------------------------------------------
; prep_para — θέση του ανοιγμένου αλεξίπτωτου, ΠΑΝΩ από τον ήρωα
;   "Πάνω" σημαίνει αντίθετα από τη βαρύτητα, όχι προς την κορυφή της οθόνης:
;   με βαρύτητα προς τα δεξιά, το αλεξίπτωτο πρέπει να είναι αριστερά του.
;---------------------------------------------------------------------
; Απόσταση του ΚΕΝΤΡΟΥ του αλεξίπτωτου από το κέντρο του ήρωα, αντίθετα στη
; βαρύτητα. Ο κόμπος των σχοινιών είναι 5.5 px κάτω από το κέντρο του sprite,
; οπότε με 14 πέφτει ~2 px πάνω από την κορυφή του κεφαλιού.
PARA_DIST       equ  14
PARA_TICKS      equ  5          ; frames ανά φάση ανοίγματος

prep_para:      ld   a,(hero_paraopen)
                ld   (para_on),a
                or   a
                jr   nz,pp_open
                xor  a                  ; κλειστό: η animation ξαναρχίζει
                ld   (para_frame),a
                ld   (para_tick),a
                ret

pp_open:        ld   a,(para_frame)     ; 4 φάσεις, ΜΙΑ φορά, μετά κρατάει την
                cp   para_gfx_frames-1      ; τελευταία
                jr   z,pp_rot
                ld   hl,para_tick
                inc  (hl)
                ld   a,(hl)
                cp   PARA_TICKS
                jr   nz,pp_rot
                ld   (hl),0
                ld   hl,para_frame
                inc  (hl)

                ; Το sprite γυρίζει στην πλησιέστερη ΟΡΘΗ φορά. Δεν αξίζει
                ; δεύτερη δέσμη στις 45 μοίρες για ένα αντικείμενο που φαίνεται
                ; λίγα δευτερόλεπτα.
                ; Το αλεξίπτωτο είναι ΠΑΝΤΑ πάνω από το κεφάλι, άρα γυρίζει
                ; και στις 8 φορές — όπως ο ήρωας: ζυγή φορά -> κανονική δέσμη,
                ; μονή -> δέσμη 45 μοιρών, και rot = φορά/2 και στις δύο.
pp_rot:         ld   a,(hero_g)
                and  1
                ld   (pp_odd),a
                ld   a,(hero_g)
                srl  a
                ld   (para_rot),a

                ld   a,(hero_g)         ; διαστάσεις εξόδου, πίνακας 8 θέσεων
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,para_dims
                add  hl,de
                ld   a,(hl)
                ld   (pp_w),a
                inc  hl
                ld   a,(hl)
                ld   (pp_h),a

                ; ΦΡΑΓΜΑ: ο GTAB καλύπτει b από -GTAB_OFF και πάνω. Με μεγαλύτερη
                ; απόσταση ο δείκτης γίνεται αρνητικός και διαβάζονται σκουπίδια
                ; — ακριβώς αυτό συνέβαινε με PARA_DIST=16.
                assert PARA_DIST<=GTAB_OFF
                ld   a,-PARA_DIST+GTAB_OFF   ; μετατόπιση ΑΝΤΙΘΕΤΑ στη βαρύτητα
                ld   hl,gtab
                call h_tabptr
                ld   a,(hl)
                ld   (pp_dx),a
                inc  hl
                ld   a,(hl)
                ld   (pp_dy),a

                ld   a,(pp_dx)          ; px = hero_x + dx - πλάτος/2
                call h_sext
                ld   hl,(hero_x)
                add  hl,de
                ld   a,(pp_w)
                srl  a
                ld   e,a
                ld   d,0
                or   a
                sbc  hl,de
                ld   a,l
                and  3
                ld   (spr_shift),a
                srl  h
                rr   l
                srl  h
                rr   l
                ld   a,l
                ld   (para_col),a

                ld   a,(pp_dy)          ; py = hero_y + dy - ύψος/2
                call h_sext
                ld   hl,(hero_y)
                add  hl,de
                ld   a,(pp_h)
                srl  a
                ld   e,a
                ld   d,0
                or   a
                sbc  hl,de
                ld   a,l
                ld   (para_y),a

                ld   a,(pp_odd)         ; --- επιλογή δέσμης ---
                or   a
                jr   nz,pp_diag
                ld   a,(para_frame)
                ld   de,para_gfx_size
                call spr_mul_ade
                ld   de,para_gfx
                add  hl,de
                ld   b,para_gfx_w
                ld   c,para_gfx_h
                jr   pp_go
pp_diag:        ld   a,(para_frame)
                ld   de,para45_gfx_size
                call spr_mul_ade
                ld   de,para45_gfx
                add  hl,de
                ld   b,para45_gfx_w
                ld   c,para45_gfx_h
pp_go:          ld   a,(para_rot)
                call spr_transform
                ld   a,(spr_bw)
                ld   (para_bw),a
                ld   a,(spr_bh)
                ld   (para_bh),a
                jp   spr_save_para

; Διαστάσεις εξόδου ανά φορά βαρύτητας (πλάτος px, ύψος γραμμές)
para_dims       db   para_gfx_w,para_gfx_h,  para45_gfx_w,para45_gfx_h
                db   para_gfx_h,para_gfx_w,  para45_gfx_w,para45_gfx_h
                db   para_gfx_w,para_gfx_h,  para45_gfx_w,para45_gfx_h
                db   para_gfx_h,para_gfx_w,  para45_gfx_w,para45_gfx_h
para_rot        db   0
para_frame      db   0
para_tick       db   0
para_bw         db   0
para_bh         db   0
pp_w            db   0
pp_h            db   0
pp_dx           db   0
pp_dy           db   0
pp_odd          db   0
para_on         db   0
para_col        db   0
para_y          db   0

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
draw_hero:      call dh_cur_rect        ; τρέχουσα περιοχή = ήρωας + αλεξίπτωτο
                ld   a,(last_valid)
                or   a
                call z,dh_remember      ; πρώτο frame: ένωση με τον εαυτό της

                ld   a,(cur_c0)         ; --- ένωση με την περιοχή του προηγούμενου
                ld   hl,last_c0
                cp   (hl)
                jr   c,dhu_c0
                ld   a,(hl)
dhu_c0:         ld   (dh_c0),a
                ld   a,(cur_c1)
                ld   hl,last_c1
                cp   (hl)
                jr   nc,dhu_c1
                ld   a,(hl)
dhu_c1:         ld   (dh_c1),a
                ld   hl,dh_c0
                sub  (hl)
                inc  a                  ; πλάτος σε bytes
                cp   LINEBUF_W+1          ; ΦΡΑΓΜΑ: τα pivot γωνίας μετακινούν τον
                jr   c,dhu_w            ; ήρωα ~12 px σε ένα frame· χωρίς αυτό η
                ld   a,LINEBUF_W          ; ένωση μπορεί να ξεπεράσει το linebuf
dhu_w:          ld   (dh_w),a

                ld   a,(cur_y0)
                ld   hl,last_y0
                cp   (hl)
                jr   c,dhu_y0
                ld   a,(hl)
dhu_y0:         ld   (dh_yy),a
                ld   a,(cur_y1)
                ld   hl,last_y1
                cp   (hl)
                jr   nc,dhu_y1
                ld   a,(hl)
dhu_y1:         ld   (dh_y1),a

dh_line:        call dh_bgline          ; φόντο -> linebuf
                call dh_sprline         ; ο ήρωας από πάνω
                call dh_paraline        ; και το αλεξίπτωτο
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

dh_remember:    ld   a,(cur_c0)
                ld   (last_c0),a
                ld   a,(cur_c1)
                ld   (last_c1),a
                ld   a,(cur_y0)
                ld   (last_y0),a
                ld   a,(cur_y1)
                ld   (last_y1),a
                ld   a,1
                ld   (last_valid),a
                ret

;--- τρέχουσα περιοχή: ήρωας, και το αλεξίπτωτο αν είναι ανοιγμένο -----
dh_cur_rect:    ld   a,(spr_col)
                ld   (cur_c0),a
                ld   hl,spr_bw
                add  a,(hl)
                dec  a
                ld   (cur_c1),a
                ld   a,(spr_y)
                ld   (cur_y0),a
                ld   hl,spr_bh
                add  a,(hl)
                dec  a
                ld   (cur_y1),a

                ld   a,(para_on)
                or   a
                ret  z
                ld   a,(para_col)
                ld   hl,cur_c0
                cp   (hl)
                jr   nc,dcr_c1
                ld   (hl),a
dcr_c1:         ld   a,(para_col)
                ld   hl,para_bw
                add  a,(hl)
                dec  a
                ld   hl,cur_c1
                cp   (hl)
                jr   c,dcr_y0
                ld   (hl),a
dcr_y0:         ld   a,(para_y)
                ld   hl,cur_y0
                cp   (hl)
                jr   nc,dcr_y1
                ld   (hl),a
dcr_y1:         ld   a,(para_y)
                ld   hl,para_bh
                add  a,(hl)
                dec  a
                ld   hl,cur_y1
                cp   (hl)
                ret  c
                ld   (hl),a
                ret

;--- σύνθεση του ανοιγμένου αλεξίπτωτου (8x8, ζεύγη mask/data) --------
dh_paraline:    ld   a,(para_on)
                or   a
                ret  z
                ld   a,(dh_yy)
                ld   hl,para_y
                sub  (hl)
                ret  c                  ; πάνω από το αλεξίπτωτο
                ld   hl,para_bh
                cp   (hl)
                ret  nc                 ; ή κάτω από αυτό

                ld   b,a                ; HL = para_buf + γραμμή*para_bw*2
                ld   a,(para_bw)
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,para_buf
                inc  b
                jr   dpl_chk
dpl_mul:        add  hl,de
dpl_chk:        djnz dpl_mul

                ld   a,(para_col)       ; DE = linebuf + (para_col - c0)
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
                ld   a,(para_bw)
                ld   b,a
dpl_lp:         ld   a,(de)
                and  (hl)               ; mask: κράτα το φόντο
                inc  hl
                or   (hl)               ; data: βάλε το αλεξίπτωτο
                inc  hl
                ld   (de),a
                inc  de
                djnz dpl_lp
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

cur_c0          db   0
cur_c1          db   0
cur_y0          db   0
cur_y1          db   0
last_c0         db   0
last_c1         db   0
last_y0         db   0
last_y1         db   0
last_valid      db   0
dh_c0           db   0
dh_c1           db   0
dh_w            db   0
dh_yy           db   0
dh_y1           db   0
dhb_off         db   0
dhb_half        db   0
linebuf         ds   LINEBUF_W, 0

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
                include "gfx_para.asm"
                include "gfx_para45.asm"
                include "gfx_objects.asm"
                include "level_test.asm"

prog_end
                save 'build/main.bin', #4000, prog_end-#4000
