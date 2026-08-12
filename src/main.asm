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
TXT_SET_CURSOR  equ  #BB75      ; H = στήλη, L = γραμμή (και οι δύο από 1)
TXT_SET_PEN     equ  #BB90      ; A = pen
TXT_OUTPUT      equ  #BB5A      ; A = χαρακτήρας

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
K_UP            equ  0          ; ενεργοποίηση — ΠΑΝΩ ή ΚΑΤΩ ανοίγει πόρτα
K_DOWN          equ  2          ; ενεργοποίηση αντικειμένου
K_SPACE         equ  47         ; το ίδιο
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
INK_HERO_PEN    equ  1          ; ο pen που δείχνει αυτό το χρώμα
INK_BODY        equ  18         ; πράσινο      - σώμα υλικού
INK_EDGE        equ  16         ; πορτοκαλί    - ακμές, κίνδυνος

;--- Οθόνη ------------------------------------------------------------
; --- HUD: πάνω 8 scanlines, πάνω από το grid της πίστας ---------------
HUD_X           equ  2          ; στήλη byte της μπάρας
HUD_Y           equ  2          ; πρώτη scanline
HUD_H           equ  4          ; ύψος σε γραμμές
HUD_SEG         equ  2          ; bytes ανά μονάδα ενέργειας
INV_X           equ  22         ; πρώτη στήλη byte του inventory
; Τα δύο βελάκια βαρύτητας, δεξιά από το inventory. Δύο ΞΕΧΩΡΙΣΤΑ πράγματα:
; η βαρύτητα του ΚΟΣΜΟΥ είναι αυτή που όρισε ο παίκτης και την ακολουθούν τα
; κιβώτια· η βαρύτητα του ΗΡΩΑ γυρίζει μόνη της σε κάθε γωνία που περπατάει.
; Χωρίς αυτά ο παίκτης δεν είχε τρόπο να δει γιατί το κιβώτιο πάει αλλού.
GRAV_WX         equ  68          ; στήλη byte του βέλους του κόσμου
GRAV_HX         equ  72          ; στήλη byte του βέλους του ήρωα
INV_MAX         equ  10         ; πόσα εικονίδια χωράνε δίπλα στη μπάρα
BYTE_PEN2       equ  #0F        ; 4 pixels pen2 (πράσινο)
BYTE_PEN3       equ  #FF        ; 4 pixels pen3 (πορτοκαλί)
LOW_ENERGY      equ  3          ; κάτω από αυτό, η μπάρα κοκκινίζει

; --- Μήνυμα πόρτας ----------------------------------------------------
; Το κείμενο το τυπώνει το firmware με τη δική του γραμματοσειρά: δεν έχουμε
; δική μας και δεν αξίζει 768 bytes για μία φράση.
;
; Η ΘΕΣΗ ΑΠΟΦΕΥΓΕΙ ΤΗΝ ΠΟΡΤΑ: αν ο ήρωας είναι στο πάνω μισό, το μήνυμα πάει
; χαμηλά, αλλιώς ψηλά. Έτσι δεν σκεπάζει ποτέ αυτό που περιγράφει, όπου κι αν
; έχει βάλει την πόρτα ο σχεδιαστής.
MSG_ROW_HI      equ  7          ; γραμμή πλέγματος όταν ο ήρωας είναι χαμηλά
MSG_ROW_LO      equ  16         ; …και όταν είναι ψηλά
MSG_NONE        equ  #FF        ; δεν φαίνεται μήνυμα
HINT_ROOMS      equ  10         ; ως ποια αίθουσα δείχνονται τα μηνύματα

; Δείκτες στον hint_ptr. Η σειρά τους ΔΕΝ είναι αυθαίρετη: είναι η σειρά
; προτεραιότητας του h_use, ώστε το μήνυμα να μην υπόσχεται κάτι άλλο από
; αυτό που θα κάνει το πλήκτρο.
MSG_EXIT        equ  0
MSG_UNLOCK      equ  1
MSG_NOKEY       equ  2
MSG_TP          equ  3
MSG_DROP        equ  4
MSG_TAKE        equ  5
MSG_PLATE       equ  6
MSG_GATE        equ  7
MSG_GSW         equ  8          ; κλειστή πύλη με διακόπτη
MSG_GPLATE      equ  9          ; …με πλάκα πίεσης
MSG_GBOTH       equ  10         ; …και με τα δύο
MSG_GDEAD       equ  11         ; …χωρίς τίποτα: λάθος του σχεδιαστή
MSG_AUTOKEY     equ  12         ; μάζεψες κλειδί που ανοίγει με την επαφή
MSG_GKEY        equ  13         ; …και ΚΡΑΤΑΣ το κλειδί της: άνοιξέ την
MSG_HOLD        equ  150        ; frames = 3 δευτερόλεπτα

LINEBUF_W         equ  24     ; πλάτος buffer γραμμής σε bytes
SCR_BASE        equ  #C000
SCR_WBYTES      equ  80         ; bytes ανά scanline σε MODE 1

;=====================================================================
main:           ld   a,1
                call SCR_SET_MODE
                call set_palette
                call init_linetab
                ; ΠΡΙΝ ΤΟ ΜΕΝΟΥ: οι αίθουσες μπαίνουν στη δεύτερη μνήμη όσο ο
                ; παίκτης δεν περιμένει τίποτα ακόμα. Μία φορά ανά εκτέλεση —
                ; το ml_again ξαναμπαίνει εδώ και δεν πρέπει να ξαναδιαβάσει.
                call bank_boot
                call menu_show          ; τίτλος και επίδειξη· γυρίζει με SPACE
                ld   a,1
                call SCR_SET_MODE       ; καθάρισε ό,τι άφησε το μενού
                call set_palette
                call game_reset         ; καθαρή ενέργεια, τσέπες, ημερολόγιο
                ld   a,START_ROOM       ; ποια αίθουσα· ορίζεται στο build
                call room_load
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

                ; Με ανοιγμένο αλεξίπτωτο ΚΑΜΙΑ αλλαγή, ούτε μέσω της δικλείδας:
                ; η κάθοδος είναι 0.5 px/frame, δηλαδή 2.5 px στα 5 frames, που
                ; περνάει άνετα για "ακίνητος" και θα έδινε πλήρη έλεγχο εν πτήσει.
                ld   a,(hero_paraopen)
                or   a
                jr   nz,ml_walk

                call h_stuck
                jr   nc,ml_walk

ml_gok:         ld   a,b
                ; ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΖΕΙ ΟΝΤΩΣ: το πλήκτρο μένει πατημένο και θα
                ; χρέωνε πενήντα φορές το δευτερόλεπτο για μία απόφαση.
                ld   hl,world_g
                cp   (hl)
                jr   z,ml_gsame
                push af
                ld   a,SCORE_GRAV
                call score_cost
                pop  af
ml_gsame:       ld   (ml_grav),a
                call h_noflip
                jr   c,ml_conly         ; ζώνη κλειδώματος: ΜΟΝΟ τα κιβώτια

                ld   a,(ml_grav)        ; ο ήρωας ακολουθεί
                ld   (hero_g),a
                ld   a,HST_FALL         ; αλλαγή φοράς -> ξαναμετράει η πτώση
                ld   (hero_state),a

                ; Μέσα σε ζώνη κλειδώματος ο παίκτης χάνει τον έλεγχο του
                ; ΣΩΜΑΤΟΣ του, όχι του κόσμου: η βαρύτητα του κόσμου αλλάζει
                ; κανονικά και τα κιβώτια την ακολουθούν.
ml_conly:       ld   a,(ml_grav)
                ld   (world_g),a
                ld   a,1
                ld   (crates_on),a
                ; Ενεργοποίηση αντικειμένου: ΑΚΜΗ πλήκτρου, όχι κράτημα.
                ; Αλλιώς ένα πάτημα θα σήκωνε και θα άφηνε το κιβώτιο δεκάδες
                ; φορές, ή θα τηλεμεταφερόταν πέρα-δώθε 50 φορές το δευτερόλεπτο.
ml_walk:        call read_use
                ld   hl,use_prev
                ld   b,a
                cp   (hl)
                ld   (hl),a
                jr   z,ml_nouse
                or   a
                call nz,h_use
ml_nouse:       call read_walk
                ld   (ml_dir),a

                ; Το τρέξιμο ΔΕΝ είναι δεύτερη ενημέρωση: αυτό θα διπλασίαζε και
                ; την πτώση, τα κιβώτια και τα αντικείμενα. Είναι σημαία που
                ; διπλασιάζει ΜΟΝΟ τον ρυθμό βημάτων βάδισης.
                xor  a
                ld   (hero_run),a
                ld   a,(ml_dir)
                or   a
                jr   z,ml_upd
                ld   a,K_SHIFT
                call KM_TEST_KEY
                jr   z,ml_upd
                ld   a,1
                ld   (hero_run),a
ml_upd:         ld   a,(ml_dir)
                call hero_update

ml_anim:        ld   a,(hero_zone)      ; παράσιτα όσο είναι σε ζώνη κλειδώματος
                call sfx_amb
                call anim_frame
                call prep_hero          ; μετασχηματισμός sprite (εκτός vblank)

                call MC_WAIT_FLYBACK
                call draw_hero          ; μόνο εγγραφές στην οθόνη
                call draw_hud
                call score_draw
                call hint_msg
if DEMO_MODE
                call demo_mark
endif

                ; Η αλλαγή αίθουσας γίνεται στο ΤΕΛΟΣ του frame, όχι μέσα στην
                ; ενημέρωση: το render_room ξαναζωγραφίζει όλη την οθόνη και δεν
                ; πρέπει να συμβεί ενώ μισοϋπολογισμένη κατάσταση δείχνει ακόμα
                ; στην παλιά αίθουσα.
                ld   a,(pending_room)
                or   a
                jr   z,ml_esc
                push af
                xor  a
                ld   (pending_room),a
                ld   a,(cur_room)       ; από πού ερχόμαστε: το χρειάζεται η
                ld   (from_room),a      ; άφιξη δίπλα στην πόρτα επιστροφής
                pop  af
                call room_load
                call sfx_reset          ; η ζώνη της παλιάς αίθουσας δεν ισχύει
                ld   a,SFXID_ENTER
                call sfx_play
ml_esc:
                ; ΔΥΟ ΤΡΟΠΟΙ ΝΑ ΤΕΛΕΙΩΣΕΙ ΜΙΑ ΠΑΡΤΙΔΑ, και οι δύο εδώ, στο τέλος
                ; του frame: μέσα στην ενημέρωση θα άλλαζε οθόνη με τη μισή
                ; κατάσταση υπολογισμένη.
                ld   a,(game_done)
                or   a
                jr   nz,ml_end
                ld   a,(hero_energy)
                or   a
                jr   z,ml_dead
                ld   a,(score_dead)     ; αρνητικό σκορ: το ίδιο τέλος, άλλη
                or   a                  ; αιτία — δες το score_add
                jr   nz,ml_dead

                ld   a,K_ESC
                call KM_TEST_KEY
                jp   z,main_loop        ; jp: ο βρόχος ξεπερνά το εύρος του jr
                ret                     ; επιστροφή στη BASIC

ml_dead:        call game_over
                jr   ml_again
ml_end:         xor  a
                ld   (game_done),a
                call the_end
ml_again:       jp   main               ; από την αρχή: μενού και πρώτη αίθουσα

ml_dir          db   0
ml_grav         db   0
game_done       db   0   ; 1 = πέρασε την πόρτα τέλους

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
; read_use — κάτω βελάκι ή SPACE
;   OUT: A = 1 αν πατιέται
;---------------------------------------------------------------------
read_use:       ld   a,K_UP             ; ΠΑΝΩ ή ΚΑΤΩ ανοίγει την πόρτα· η
                call KM_TEST_KEY        ; επαφή δεν αρκεί πια
                jr   nz,ru_yes
                ld   a,K_DOWN
                call KM_TEST_KEY
                jr   nz,ru_yes
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   nz,ru_yes
                xor  a
                ret
ru_yes:         ld   a,1
                ret

use_prev        db   0

;---------------------------------------------------------------------
; anim_frame — διαλέγει frame ανάλογα με την κατάσταση
;---------------------------------------------------------------------
anim_frame:     ld   hl,anim_tick
                inc  (hl)
                ld   a,(hero_run)       ; στο τρέξιμο, διπλάσιος ρυθμός καρέ
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
                ; WALK: 8 frames, ένα ανά 2 tick. Ήταν ένα ανά 4, όταν το
                ; βάδισμα ήταν 2 px/frame: 4 tick x 2 px = 8 px ανά καρέ
                ; animation, όσο σχεδιάστηκαν τα sprites. Με 4 px/frame η ίδια
                ; διαίρεση έδινε 16 px και ο ήρωας γλιστρούσε — δρασκελιά δύο
                ; ολόκληρων tile. Μία ολίσθηση λιγότερη το ξαναφέρνει στα 8 px,
                ; και στο τρέξιμο (όπου ο anim_tick διπλασιάζεται) επίσης.
                ;
                ; ΚΑΙ Ο ΗΧΟΣ ΜΑΖΙ: το βήμα δένεται παρακάτω στα καρέ 2 και 6
                ; αυτού του κύκλου, οπότε ο κύκλος των 64 px επαναφέρει το ένα
                ; πάτημα ανά 32 px — ακριβώς ό,τι καρφώνει το physics.js:513.
af_walk:        ld   a,(anim_tick)
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
af_set:         ld   hl,anim_cur
                cp   (hl)
                ld   (hl),a             ; το ld δεν πειράζει τα flags
                ret  z                  ; ίδιο καρέ: δεν άλλαξε τίποτα

                ; ΗΧΟΣ ΒΗΜΑΤΟΣ. Δένεται στο ΚΑΡΕ, όχι σε μετρητή: ο κύκλος
                ; βάδισης είναι 2..9 και τα 2 και 6 είναι οι στιγμές επαφής,
                ; οπότε ο ήχος πέφτει πάνω στο πόδι που πατάει. Στο τρέξιμο ο
                ; anim_tick διπλασιάζεται, άρα ο ρυθμός ακολουθεί μόνος του.
                cp   2
                jr   z,af_foot
                cp   6
                ret  nz
                ; Η κατάσταση WALK ισχύει και όταν στέκεσαι ακίνητος σε πάτωμα:
                ; χωρίς αυτόν τον έλεγχο ο ήρωας θα περπατούσε επί τόπου.
af_foot:        ld   a,(ml_dir)
                or   a
                ret  z
                ld   a,SCORE_STEP       ; ΑΝΑ ΠΑΤΗΜΑ, όχι ανά pixel
                call score_cost
                ld   a,SFXID_STEP
                jp   sfx_play

anim_tick       db   0
anim_cur        db   0


;---------------------------------------------------------------------
; draw_hud — μπάρα ενέργειας και εικονίδιο αλεξίπτωτου
;   Ζωγραφίζει ΜΟΝΟ όταν κάτι άλλαξε: το HUD είναι στατικό τις περισσότερες
;   στιγμές και δεν αξίζει 40 bytes εγγραφών ανά frame.
;---------------------------------------------------------------------
draw_hud:       call draw_garrows       ; τα βελάκια έχουν ΔΙΚΟ ΤΟΥΣ κριτήριο:
                ld   a,(hud_dirty)      ; η βαρύτητα του ήρωα αλλάζει σε κάθε
                or   a                  ; γωνία που περπατάει, χωρίς να πειράζει
                ret  z                  ; ενέργεια ή inventory
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

                ; --- inventory ---------------------------------------
                ; Ένα εικονίδιο ΑΝΑ ΜΟΝΑΔΑ, όχι εικονίδιο συν αριθμός: δεν
                ; υπάρχει γραμματοσειρά για ψηφία στο HUD, και η επανάληψη
                ; διαβάζεται αμέσως ("τρία κλειδιά" = τρία κλειδιά).
                ld   hl,inv_list
                ld   b,INV_MAX
                push hl                 ; ΣΥΝΟΛΟ κλειδιών, όλων των ταυτοτήτων:
                push bc                 ; το HUD δείχνει ΠΟΣΑ έχεις, όχι ποια
                ld   hl,hero_keys
                ld   b,ATTR_MAX
                xor  a
dhd_ksum:       add  a,(hl)
                inc  hl
                djnz dhd_ksum
                pop  bc
                pop  hl
                ld   c,T_KEY
                call inv_add
                ld   a,(hero_para)
                ld   c,T_PARACHUTE
                call inv_add
                ld   a,(hero_carry)
                ld   c,T_CRATE
                call inv_add
inv_pad:        ld   a,b                ; οι υπόλοιπες θέσεις καθαρίζουν, ώστε
                or   a                  ; να σβήνει ό,τι χρησιμοποιήθηκε
                jr   z,inv_draw
                ld   (hl),T_EMPTY
                inc  hl
                dec  b
                jr   inv_pad

inv_draw:       xor  a
                ld   (inv_i),a
inv_dlp:        ld   a,(inv_i)
                ld   e,a
                ld   d,0
                ld   hl,inv_list
                add  hl,de
                ld   a,(hl)             ; τύπος -> γραφικό, ΣΕ 16-BIT
                ld   l,a
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ld   de,tile_gfx
                add  hl,de
                ld   (dhd_gfx),hl
                ld   a,(inv_i)
                add  a,a
                add  a,INV_X
                ld   (inv_col),a
                ld   a,8
                ld   (dhd_rows),a
                ld   b,0
inv_line:       push bc
                ld   a,(inv_col)
                ld   c,a
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
                jr   nz,inv_line
                ld   hl,inv_i
                inc  (hl)
                ld   a,(hl)
                cp   INV_MAX
                jr   nz,inv_dlp
                ret

;---------------------------------------------------------------------
; draw_garrows — τα δύο βελάκια βαρύτητας, ΜΟΝΟ όταν άλλαξε κάτι
;
;   Δικό τους κριτήριο και όχι το hud_dirty: η βαρύτητα του ήρωα γυρίζει σε
;   κάθε γωνία που περπατάει, χωρίς να αλλάζει ενέργεια ή inventory. Με το
;   hud_dirty τα βελάκια θα έμεναν παγωμένα· χωρίς κανένα κριτήριο θα
;   ξαναγράφονταν 50 φορές το δευτερόλεπτο.
;
;   ΠΡΟΣΟΧΗ ΣΤΟ ΠΟΥ ΜΠΑΙΝΕΙ Η ΚΛΗΣΗ: πρώτη γραφή τους ήταν μετά από ένα
;   `jr inv_pad`, δηλαδή σε σημείο όπου δεν φτάνει ποτέ η ροή — ο κώδικας ήταν
;   σωστός αλλά δεν τον καλούσε κανείς και στον Amstrad δεν φαινόταν τίποτα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
draw_garrows:   ld   a,(world_g)
                ld   hl,hud_g_last
                cp   (hl)
                jr   nz,dga_go
                ld   a,(hero_g)
                inc  hl
                cp   (hl)
                ret  z                  ; τίποτα δεν άλλαξε
dga_go:         ld   a,(world_g)
                ld   (hud_g_last),a
                ld   hl,grav_gfx_world
                ld   c,GRAV_WX
                call draw_garrow
                ld   a,(hero_g)
                ld   (hud_g_last+1),a
                ld   hl,grav_gfx_hero
                ld   c,GRAV_HX
                jp   draw_garrow

; #FF: καμία έγκυρη φορά, ώστε η πρώτη κλήση να ζωγραφίζει σίγουρα.
hud_g_last      db #FF,#FF

; inv_add — προσθέτει A αντίγραφα του τύπου C, όσο υπάρχει χώρος (B)
inv_add:        or   a
                ret  z
                ld   d,a
ia_lp:          ld   a,b
                or   a
                ret  z
                ld   (hl),c
                inc  hl
                dec  b
                dec  d
                jr   nz,ia_lp
                ret

inv_i           db   0
inv_col         db   0
inv_list        ds   INV_MAX, 0

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

                ; Μετά από τηλεμεταφορά η παλιά θέση απέχει πολύ: η ένωση των
                ; δύο ορθογωνίων ξεπερνά το φράγμα του linebuf και το παλιό
                ; sprite θα έμενε ως φάντασμα. Σβήνεται ρητά.
                ld   a,(hero_warp)
                or   a
                jr   z,dh_nowarp
                xor  a
                ld   (hero_warp),a
                call dh_erase_last
                call dh_remember        ; η ένωση = μόνο η νέα θέση

dh_nowarp:      ld   a,(last_valid)
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
                ; ΑΝΑΒΟΣΒΗΝΕΙ ΟΣΟ ΕΙΝΑΙ ΑΤΡΩΤΟΣ. Παραλείπουμε ΜΟΝΟ το sprite,
                ; όχι τη σχεδίαση: το φόντο γράφεται κανονικά, οπότε ο ήρωας
                ; σβήνεται σωστά. Αν παραλείπαμε όλο το draw_hero, θα έμενε
                ; παγωμένος στην οθόνη.
                ld   a,(hero_hurt)
                and  4                  ; 4 καρέ μέσα, 4 έξω
                jr   nz,dh_blink
                call dh_sprline         ; ο ήρωας από πάνω
                call dh_paraline        ; και το αλεξίπτωτο
dh_blink:
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

;--- ρητό σβήσιμο της τελευταίας θέσης, ξαναζωγραφίζοντας τα κελιά ----
dh_erase_last:  ld   a,(last_valid)
                or   a
                ret  z
                ld   a,(last_c0)        ; στήλες byte -> στήλες κελιών
                srl  a
                ld   (el_col0),a
                ld   a,(last_c1)
                srl  a
                ld   (el_col1),a

                ld   a,(last_y0)        ; scanlines -> γραμμές κελιών
                sub  LVL_Y0
                jr   nc,el_r0
                xor  a
el_r0:          srl  a
                srl  a
                srl  a
                ld   (el_row),a
                ld   a,(last_y1)
                sub  LVL_Y0
                srl  a
                srl  a
                srl  a
                cp   LVL_ROWS
                jr   c,el_r1
                ld   a,LVL_ROWS-1
el_r1:          ld   (el_row1),a

el_rowlp:       ld   a,(el_col0)
                ld   (el_c),a
el_collp:       ld   a,(el_c)
                cp   LVL_COLS
                jr   nc,el_next
                ld   c,a
                ld   a,(el_row)
                ld   b,a
                call draw_tile
                ld   hl,el_c
                inc  (hl)
                ld   a,(hl)
                ld   hl,el_col1
                cp   (hl)
                jr   z,el_collp
                jr   c,el_collp
el_next:        ld   hl,el_row
                inc  (hl)
                ld   a,(hl)
                ld   hl,el_row1
                cp   (hl)
                jr   z,el_rowlp
                jr   c,el_rowlp
                ret

el_col0         db   0
el_col1         db   0
el_row          db   0
el_row1         db   0
el_c            db   0

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
                ld   de,(level_ptr)
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

dhb_lp:         ld   a,(hl)             ; τύπος*16 + offset γραμμής + μισό
                push hl
                push bc                 ; το B είναι ο μετρητής της γραμμής
                ld   l,a                ; ΣΕ 16-BIT: το τύπος*16 ξεπερνά το byte
                ld   h,0                ; από τον τύπο 16 και πάνω
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ld   a,(dhb_off)
                ld   c,a
                ld   a,(dhb_half)
                add  a,c
                ld   c,a
                ld   b,0
                add  hl,bc
                ld   bc,tile_gfx
                add  hl,bc
                ld   a,(hl)
                pop  bc
                pop  hl
                ld   (de),a
                inc  de
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
; draw_garrow — ζωγραφίζει ένα βελάκι βαρύτητας στο HUD
;
;   Το γραφικό είναι 8 γραμμές x 2 bytes, δηλαδή ακριβώς το ύψος του HUD.
;   Ο πολλαπλασιασμός φορά*16 γίνεται σε 16 bits: με 8 φορές δεν ξεχειλίζει
;   σήμερα, αλλά η ίδια πράξη σε 8 bits έχει ήδη δώσει δύο σφάλματα σε αυτό
;   το project (type*16, col*8) και δεν αξίζει να ξαναγραφτεί λάθος.
;
; IN:  A = φορά βαρύτητας (0..7), HL = πίνακας γραφικών, C = στήλη byte
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
draw_garrow:    push hl
                ld   l,a
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl              ; φορά * 16
                pop  de
                add  hl,de
                ld   (dga_src),hl
                ld   a,c
                ld   (dga_col),a
                ld   b,0                ; scanline 0 = πρώτη γραμμή του HUD
dga_line:       push bc
                ld   a,(dga_col)
                ld   c,a
                call scr_addr
                ex   de,hl
                ld   hl,(dga_src)
                ldi                     ; δύο bytes = 8 pixels σε MODE 1
                ldi
                ld   (dga_src),hl
                pop  bc
                inc  b
                ld   a,b
                cp   8
                jr   c,dga_line
                ret

dga_src         dw 0
dga_col         db 0

;---------------------------------------------------------------------
; hint_msg — μήνυμα για ΟΤΙ έχει ο ήρωας κάτω/γύρω του
;
;   Ο παίκτης δεν έχει εγχειρίδιο. Κάθε αντικείμενο λέει μόνο του τι κάνει,
;   τη στιγμή που το πατάς — και σβήνει μόλις φύγεις.
;
;   Η ΣΕΙΡΑ ΕΙΝΑΙ Η ΙΔΙΑ με του h_use, αλλιώς το μήνυμα θα υποσχόταν κάτι που
;   το πλήκτρο δεν κάνει: πάνω σε τηλεμεταφορά με γεμάτα χέρια, το h_use
;   τηλεμεταφέρει και ΔΕΝ αφήνει το κιβώτιο.
;
;   Το μήνυμα δεν εμποδίζει τίποτα: είναι σκέτη σχεδίαση στο τέλος του frame.
;   Σβήνει ξαναζωγραφίζοντας τα πλακίδια από κάτω του, γιατί εκεί μπορεί να
;   υπάρχει οτιδήποτε — γράψιμο κενών δεν αρκεί.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
                ; ΜΗΝΥΜΑ ΜΕ ΧΡΟΝΟΜΕΤΡΟ: το μάζεμα κλειδιού είναι ΓΕΓΟΝΟΣ, όχι
                ; κατάσταση — δεν υπάρχει κελί να το «κρατά» ενόσω φαίνεται.
                ; Δείχνεται ΠΑΝΤΑ, ανεξάρτητα από το όριο των αιθουσών: είναι η
                ; μόνη φορά που μαθαίνεις ότι δεν θα χρειαστεί να πατήσεις.
hint_msg:       ld   hl,msg_left
                ld   a,(hl)
                or   a
                jr   z,hm_normal
                dec  (hl)
                ld   a,(msg_force)
                jr   hm_have

hm_normal:      ld   a,(cur_room)       ; ΟΔΗΓΟΣ, όχι μόνιμο HUD: μετά τις πρώτες
                cp   HINT_ROOMS+1       ; αίθουσες ο παίκτης τα ξέρει και τα
                jr   c,hm_on            ; μηνύματα γίνονται θόρυβος
                ld   a,MSG_NONE
                jr   hm_have
hm_on:          call hint_pick
hm_have:
                ld   b,a                ; B = ποιο μήνυμα θέλουμε τώρα
                ld   a,(msg_cur)
                cp   b
                jr   nz,hm_change
                cp   MSG_NONE           ; ίδιο μήνυμα: μήπως άλλαξε μισό οθόνης;
                ret  z
                call hint_row
                ld   b,a
                ld   a,(msg_row)
                cp   b
                ret  z
                ld   a,(msg_cur)
                ld   b,a
hm_change:      push bc
                call hint_erase
                pop  bc
                ld   a,b
                ld   (msg_cur),a
                cp   MSG_NONE
                ret  z
                jp   hint_draw

; hint_pick — ποιο μήνυμα ταιριάζει· A = δείκτης ή MSG_NONE
hint_pick:      call h_support          ; τι ΠΑΤΑΜΕ (η κλειδαριά είναι στερεή)
                ld   (hp_sup),a
                ld   a,(cell_col)       ; ΦΥΛΑΞΕ ΤΟ ΤΩΡΑ: το cell_at από κάτω
                ld   (hp_scol),a        ; ξαναγράφει τα cell_col/cell_row με το
                ld   a,(cell_row)       ; κελί του ΣΩΜΑΤΟΣ, και η ταυτότητα της
                ld   (hp_srow),a        ; κλειδαριάς θα διαβαζόταν από λάθος κελί
                ld   bc,(hero_x)        ; τι μας ΠΕΡΙΒΑΛΛΕΙ
                ld   de,(hero_y)
                call cell_at
                ld   (hp_body),a

                cp   T_EXIT
                ld   a,MSG_EXIT
                ret  z

                ld   a,(hp_sup)         ; κλειδαριά: με ή χωρίς το κλειδί της
                cp   T_LOCK
                jr   nz,hp_notlock
                ld   a,(hp_scol)
                ld   b,a
                ld   a,(hp_srow)
                ld   c,a
                call cell_attr
                ld   e,a
                ld   d,0
                ld   hl,hero_keys
                add  hl,de
                ld   a,(hl)
                or   a
                ld   a,MSG_UNLOCK
                ret  nz
                ld   a,MSG_NOKEY
                ret

hp_notlock:     ld   a,(hp_body)
                cp   T_TELEPORT
                ld   a,MSG_TP
                ret  z

                ; ΜΕ ΓΕΜΑΤΑ ΧΕΡΙΑ μήνυμα μόνο πάνω σε ΠΛΑΚΑ: εκεί το άφημα
                ; κάνει κάτι ορατό (κρατά τις πύλες ανοιχτές). Παντού αλλού το
                ; πλήκτρο αφήνει κι αυτό το κιβώτιο, αλλά μια μόνιμη υπενθύμιση
                ; σε κάθε βήμα είναι θόρυβος, όχι οδηγία.
                ld   a,(hero_carry)
                or   a
                jr   z,hp_free
                ld   a,(hp_body)
                cp   T_PLATE
                ld   a,MSG_DROP
                ret  z
                ld   a,MSG_NONE
                ret

hp_free:        ld   a,(hp_body)
                cp   T_CRATE
                ld   a,MSG_TAKE
                ret  z
                ld   a,(hp_body)
                cp   T_PLATE_DOWN
                ld   a,MSG_TAKE
                ret  z
                ld   a,(hp_body)
                cp   T_PLATE
                ld   a,MSG_PLATE
                ret  z
                ld   a,(hp_body)
                cp   T_GATE_OPEN
                ld   a,MSG_GATE
                ret  z

                ; ΚΛΕΙΣΤΗ ΠΥΛΗ: είναι στερεή, οπότε δεν στέκεσαι ποτέ ΜΕΣΑ της
                ; — ή την πατάς από πάνω (είναι πάτωμα) ή την ακουμπάς μπροστά
                ; σου. Και στις δύο περιπτώσεις το μήνυμα λέει ΤΙ την ανοίγει,
                ; που είναι το μόνο που δεν φαίνεται κοιτάζοντάς την.
                ld   a,(hp_sup)
                cp   T_GATE
                jr   nz,hp_gahead
                ld   a,(hp_scol)
                ld   b,a
                ld   a,(hp_srow)
                ld   c,a
                jr   hp_gmsg

hp_gahead:      call h_ahead
                cp   T_GATE
                jr   nz,hp_none
                ld   a,(cell_col)
                ld   b,a
                ld   a,(cell_row)
                ld   c,a
hp_gmsg:        call cell_attr
                and  7
                ld   (hp_chan),a
                jr   z,hp_gdrv          ; κανάλι 0: κανένα κλειδί δεν ταιριάζει
                ld   e,a
                ld   d,0
                ld   hl,hero_keys
                add  hl,de
                ld   a,(hl)
                or   a
                ld   a,MSG_GKEY
                ret  nz                 ; το κρατάς: πες πώς ανοίγει ΤΩΡΑ
hp_gdrv:        ld   a,(hp_chan)
                call gate_drivers       ; A: bit0 = διακόπτης, bit1 = πλάκα
                or   a
                ld   a,MSG_GDEAD
                ret  z
                ld   a,b
                cp   3
                ld   a,MSG_GBOTH
                ret  z
                ld   a,b
                dec  a
                ld   a,MSG_GSW
                ret  z
                ld   a,MSG_GPLATE
                ret

hp_chan         db 0

hp_none:        ld   a,MSG_NONE
                ret

; gate_drivers — τι οδηγεί το κανάλι A
;   OUT: B = A = bit0 διακόπτης, bit1 πλάκα· Z αν τίποτα
;   ΑΛΛΟΙΩΝΕΙ: τα πάντα
gate_drivers:   ld   (gd_chan),a
                xor  a
                ld   (gd_found),a
                ld   hl,(room_attrs)
gd_lp:          ld   a,(hl)
                cp   #FF
                jr   z,gd_done
                ld   c,a
                inc  hl
                ld   b,(hl)
                inc  hl
                ld   a,(hl)
                inc  hl
                push hl
                ld   hl,gd_chan
                cp   (hl)
                jr   nz,gd_next
                push bc
                call cell_addr
                pop  bc
                ld   a,(hl)
                cp   T_SWITCH
                jr   nz,gd_pl
                ld   a,1
                jr   gd_mark
gd_pl:          cp   T_PLATE
                jr   z,gd_plate
                cp   T_PLATE_DOWN
                jr   nz,gd_next
gd_plate:       ld   a,2
gd_mark:        ld   hl,gd_found
                or   (hl)
                ld   (hl),a
gd_next:        pop  hl
                jr   gd_lp

gd_done:        ld   a,(gd_found)
                ld   b,a
                or   a
                ret

gd_chan         db 0
gd_found        db 0

; hint_row — σε ποια γραμμή πλέγματος μπαίνει· ΜΑΚΡΙΑ από τον ήρωα, ώστε να
;   μη σκεπάζει αυτό που περιγράφει.
hint_row:       ld   a,(hero_y)
                sub  LVL_Y0
                rrca                    ; /8 -> γραμμή πλέγματος
                rrca
                rrca
                and  #1F
                cp   12
                ld   a,MSG_ROW_LO
                ret  c
                ld   a,MSG_ROW_HI
                ret

; hint_erase — ξαναζωγραφίζει τα πλακίδια κάτω από το μήνυμα που φαίνεται
hint_erase:     ld   a,(msg_cur)
                cp   MSG_NONE
                ret  z
                ld   a,(msg_row)
                ld   b,a
                ld   a,(msg_col)
                dec  a                  ; οι στήλες κειμένου ξεκινούν από 1
                ld   c,a
                ld   a,(msg_len)
                ld   (hm_n),a
he_lp:          push bc
                call draw_tile
                pop  bc
                inc  c
                ld   hl,hm_n
                dec  (hl)
                jr   nz,he_lp
                ld   a,MSG_NONE
                ld   (msg_cur),a
                ret

; hint_draw — τυπώνει το μήνυμα (msg_cur), κεντραρισμένο
hint_draw:      ld   a,(msg_cur)        ; δείκτης -> διεύθυνση κειμένου
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,hint_ptr
                add  hl,de
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                ld   a,(de)             ; πρώτο byte = μήκος
                ld   (msg_len),a
                inc  de
                ld   (hm_txt),de

                ld   b,a                ; στήλη = (40 - μήκος) / 2 + 1
                ld   a,40
                sub  b
                srl  a
                inc  a
                ld   (msg_col),a
                call hint_row
                ld   (msg_row),a

                ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   a,(msg_row)
                add  a,2                ; γραμμή πλέγματος -> γραμμή κειμένου
                ld   l,a
                ld   a,(msg_col)
                ld   h,a
                ld   de,(hm_txt)
                ld   a,(msg_len)
                ld   b,a
                jp   menu_puts          ; ίδια ρουτίνα με το μενού

hm_n            db 0
hm_txt          dw 0
hp_sup          db 0
hp_scol         db 0
hp_srow         db 0
hp_body         db 0
msg_cur         db MSG_NONE     ; ποιο μήνυμα φαίνεται· #FF = κανένα
msg_row         db 0
msg_col         db 0
msg_len         db 0
msg_force       db 0            ; μήνυμα-γεγονός που δείχνεται με χρονόμετρο
msg_left        db 0            ; frames που του μένουν

; Τα μηνύματα. Πρώτο byte το μήκος, ώστε να μη χρειάζεται τερματικό ούτε
; γέμισμα σε σταθερό πλάτος — τα μήκη διαφέρουν πολύ.
hint_ptr:       dw hs_exit, hs_unlock, hs_nokey, hs_tp
                dw hs_drop, hs_take, hs_plate, hs_gate
                dw hs_gsw, hs_gplate, hs_gboth, hs_gdead
                dw hs_autokey, hs_gkey

; Το μήκος το μετράει ο ASSEMBLER, όχι εγώ: μια χειρόγραφη αρίθμηση κατά ένα
; παραπάνω τυπώνει ένα byte σκουπίδι στο τέλος — και δεν φαίνεται με το μάτι.
hs_exit:        db hs_exit_e-hs_exit-1
                db "Up or down to exit room"
hs_exit_e:
hs_unlock:      db hs_unlock_e-hs_unlock-1
                db "Up or down to unlock"
hs_unlock_e:
hs_nokey:       db hs_nokey_e-hs_nokey-1
                db "You need the matching key"
hs_nokey_e:
hs_tp:          db hs_tp_e-hs_tp-1
                db "Up or down to teleport"
hs_tp_e:
hs_drop:        db hs_drop_e-hs_drop-1
                db "Up or down to drop crate"
hs_drop_e:
hs_take:        db hs_take_e-hs_take-1
                db "Up or down to pick up crate"
hs_take_e:
hs_plate:       db hs_plate_e-hs_plate-1
                db "A crate here keeps gates opened"
hs_plate_e:
hs_gate:        db hs_gate_e-hs_gate-1
                db "This gate is open"
hs_gate_e:
hs_gsw:         db hs_gsw_e-hs_gsw-1
                db "Find its switch to open this"
hs_gsw_e:
hs_gplate:      db hs_gplate_e-hs_gplate-1
                db "Weigh down its plate to open"
hs_gplate_e:
hs_gboth:       db hs_gboth_e-hs_gboth-1
                db "A switch or a plate opens this"
hs_gboth_e:
hs_gdead:       db hs_gdead_e-hs_gdead-1
                db "This gate has nothing to open it"
hs_gdead_e:
hs_autokey:     db hs_autokey_e-hs_autokey-1
                db "This key unlocks on touch"
hs_autokey_e:
hs_gkey:        db hs_gkey_e-hs_gkey-1
                db "Up or down to open with key"
hs_gkey_e:

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
                include "roomfile.asm"
                include "menu.asm"
                include "score.asm"
                include "hiscore.asm"
                include "musicplay.asm"
                include "sfx.asm"
                include "endings.asm"

;--- δεδομένα ---------------------------------------------------------
                include "gfx_hero.asm"
                include "gfx_hero45.asm"
                include "gfx_para.asm"
                include "gfx_para45.asm"
                include "gfx_objects.asm"
                include "rooms.asm"
                include "music.asm"

;--- κώδικας που ΠΡΕΠΕΙ να ζει πάνω από το #8000 ----------------------
; Εναλλάσσει το #4000..#7FFF, όπου βρίσκεται όλος ο υπόλοιπος κώδικας. Μπαίνει
; τελευταίο επίτηδες: εδώ οι διευθύνσεις έχουν ξεπεράσει το #8000. Το ίδιο το
; αρχείο κάνει assert γι' αυτό — δεν είναι σύμβαση, είναι απαίτηση.
                include "bank.asm"

prog_end
                save 'build/main.bin', #4000, prog_end-#4000

;--- buffers ΜΟΝΟ στη μνήμη -------------------------------------------
; Δηλώνονται ΜΕΤΑ το save, οπότε δεν μπαίνουν στο MAIN.BIN: είναι ~10 KB
; μηδενικών που δεν έχει νόημα να ταξιδεύουν στη δισκέτα και να φορτώνονται.
cell_buf        ds   LVL_CELLS          ; το ξεδιπλωμένο πλέγμα που παίζεται
journal         ds   JOURNAL_MAX*4      ; (αίθουσα, offset lo, offset hi, τύπος)

; Το σετ αιθουσών παίρνει ΟΛΟ ό,τι περισσεύει, χωρίς δηλωμένο μέγεθος: είναι
; τελευταίο και τίποτα δεν ακολουθεί. Έτσι κάθε γραμμή κώδικα που προσθέτουμε
; μικραίνει απλώς τη χωρητικότητα σε αίθουσες, αντί να σπάει το build και να
; ζητά χειροκίνητο ξανασυντονισμό ενός SET_MAX.
;
; Με ενεργό AMSDOS η μνήμη ΔΕΝ φτάνει ως το firmware: ο δίσκος κρατά δικό του
; χώρο εργασίας και το ταβάνι πέφτει στο #A67B.
set_buf
set_capacity    equ  MEM_CEIL-set_buf   ; το διαβάζει το tools/roomfile.py
                assert set_capacity > 0
                ; Ο buffer πρέπει να χωράει ΟΛΟΚΛΗΡΗ μία θέση τράπεζας, γιατί
                ; τόσα φέρνει το slot_copy. ΔΕΝ ελέγχεται εδώ: το rasm αποτιμά
                ; τα assert σε πρώιμο πέρασμα, όπου το set_buf δεν έχει ακόμα
                ; την τελική του θέση και ο έλεγχος σκάει ψευδώς. Ο έλεγχος
                ; ζει στο tools/roomfile.py, που διαβάζει το ΤΕΛΙΚΟ σύμβολο.
