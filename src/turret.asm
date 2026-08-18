;=====================================================================
;  GRAVASSIST — πυργίσκοι και βέλη
;
;  Μεταγραφή του turret_step/arrows_step του tools/physics.py. Η σειρά μέσα
;  στον βρόχο είναι η ΙΔΙΑ: τα βέλη κινούνται πρώτα και οι πυργίσκοι ρίχνουν
;  μετά, και τα δύο ΠΑΝΩ από την πρόωρη έξοδο στην πτώση — ένα βέλος σε βρίσκει
;  και στον αέρα, και ο πυργίσκος φορτίζει είτε στέκεσαι είτε πέφτεις.
;
;  ΓΙΑΤΙ ΠΙΝΑΚΑΣ ΚΑΙ ΟΧΙ ΣΑΡΩΣΗ: το πλέγμα είναι 960 κελιά και ο έλεγχος βολής
;  γίνεται σε κάθε καρέ. Ο πίνακας χτίζεται ΜΙΑ φορά, στη φόρτωση της αίθουσας.
;
;  ΤΑ ΠΕΝΤΕ ΔΕΥΤΕΡΟΛΕΠΤΑ ΕΡΧΟΝΤΑΙ ΑΠΟ ΤΟ ΡΟΛΟΙ, όχι από μετρητή καρέ. Ένα
;  πέρασμα του βρόχου κοστίζει 3 vsync ακίνητος και 7 τρέχοντας, οπότε ένας
;  μετρητής περασμάτων θα φόρτιζε σε 5 δευτερόλεπτα όταν στέκεσαι και σε 11
;  όταν τρέχεις — ο πυργίσκος θα άραζε ακριβώς όταν τον αποφεύγεις. Το ίδιο
;  λάθος έχει ήδη γίνει τρεις φορές σε αυτό το repo· δες CLAUDE.md.
;=====================================================================

; --- πίνακας πυργίσκων της αίθουσας ---------------------------------
TS_COL          equ  0
TS_ROW          equ  1
TS_TYPE         equ  2
TS_READY        equ  3          ; dw: ρολόι από το οποίο ξαναρίχνει
TS_COOL         equ  5          ; δευτερόλεπτα φόρτισης
TS_AUTO         equ  6          ; 0 = μόνο όταν βλέπει· αλλιώς ρυθμός σε δευτ.
TS_SIZE         equ  7

; --- βέλη στον αέρα --------------------------------------------------
AR_ON           equ  0          ; 0 = ελεύθερη θέση
AR_X            equ  1          ; dw — το x φτάνει ως 319
AR_Y            equ  3          ; db
AR_DX           equ  4          ; προσημασμένο, -1 / 0 / +1
AR_DY           equ  5
AR_GONE         equ  6          ; pixel που διανύθηκαν
AR_SIZE         equ  7

;---------------------------------------------------------------------
; turret_load — χτίζει τον πίνακα από το cell_buf. Στη φόρτωση αίθουσας.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
turret_load:    call turret_reset
                ld   hl,cell_buf
                ld   ix,turret_tab
                ld   b,0                ; B = γραμμή
tl_row:         ld   c,0                ; C = στήλη
                ; ΚΑΙ ΟΙ ΣΒΗΣΤΟΙ ΜΠΑΙΝΟΥΝ ΣΤΟΝ ΠΙΝΑΚΑ. Ο διακόπτης τους ανάβει
                ; και σβήνει μέσα στην παρτίδα, ενώ ο πίνακας χτίζεται μόνο στη
                ; φόρτωση της αίθουσας — αν κρατούσε μόνο τους αναμμένους, ένας
                ; πυργίσκος που ξεκινά σβηστός δεν θα ξανάριχνε ποτέ.
tl_col:         ld   a,(hl)
                cp   T_TURRET_V
                jr   z,tl_add
                cp   T_TURRET_H
                jr   z,tl_add
                cp   T_TURRET_V_OFF
                jr   z,tl_add
                cp   T_TURRET_H_OFF
                jr   nz,tl_next
tl_add:         ld   d,a
                ld   a,(turret_n)
                cp   TURRET_SLOTS       ; ό,τι περισσεύει αγνοείται σιωπηλά:
                jr   nc,tl_next         ; μια αίθουσα με εννιά πυργίσκους δεν
                inc  a                  ; είναι λόγος να μη φορτώσει
                ld   (turret_n),a
                ld   (ix+TS_COL),c
                ld   (ix+TS_ROW),b
                ld   (ix+TS_TYPE),d
                ld   (ix+TS_READY),0    ; φορτισμένος από την πρώτη στιγμή
                ld   (ix+TS_READY+1),0
                push hl                 ; οι δύο χρόνοι από τον πέμπτο πίνακα
                push bc
                ld   b,c                ; B = στήλη, C = γραμμή
                ld   a,(ix+TS_ROW)
                ld   c,a
                call turret_arg         ; D = φόρτιση, E = ρυθμός
                ld   a,d
                or   a
                jr   nz,tl_cool         ; αδήλωτος: η προεπιλογή
                ld   a,TURRET_COOL_DEF
tl_cool:        ld   (ix+TS_COOL),a
                ld   (ix+TS_AUTO),e
                ; Ο ΡΥΘΜΙΚΟΣ ΞΕΚΙΝΑ ΦΟΡΤΙΖΟΝΤΑΣ: η πρώτη βολή έρχεται ένα
                ; διάστημα μετά την είσοδο στην αίθουσα, όχι στο πρώτο πέρασμα.
                ; Αλλιώς περνάς την πόρτα και σε βρίσκει βέλος πριν προλάβεις να
                ; δεις πού είσαι — και δεν είναι δική σου επιλογή, όπως είναι με
                ; τον πυργίσκο που περιμένει να μπεις στην ευθεία του.
                ld   a,e
                or   a
                jr   z,tl_done
                call tf_ticks           ; HL = δευτερόλεπτα x 300
                push hl
                call clock_now          ; HL = τώρα (χαλάει AF, DE)
                pop  de
                add  hl,de
                ld   (ix+TS_READY),l
                ld   (ix+TS_READY+1),h
tl_done:        pop  bc
                pop  hl
                ld   de,TS_SIZE
                add  ix,de
tl_next:        inc  hl
                inc  c
                ld   a,c
                cp   LVL_COLS
                jr   c,tl_col
                inc  b
                ld   a,b
                cp   LVL_ROWS
                jr   c,tl_row
                ret

;---------------------------------------------------------------------
; turret_reset — καμία βολή στον αέρα, κανένας πυργίσκος. Και στο game_reset.
;---------------------------------------------------------------------
turret_reset:   xor  a
                ld   (turret_n),a
                ld   hl,arrow_tab
                ld   b,TURRET_MAX
tr_lp:          ld   (hl),0             ; AR_ON
                ld   de,AR_SIZE
                add  hl,de
                djnz tr_lp
                ; ΚΑΙ ΤΟ ΑΝΤΙΓΡΑΦΟ: μια παλιά θέση που επιβίωσε θα έσβηνε ένα
                ; ορθογώνιο σε καθαρή αίθουσα, πάνω σε ό,τι έχει ζωγραφιστεί.
                ld   hl,arrow_old
                ld   b,TURRET_MAX
tr_old:         ld   (hl),0
                ld   de,AR_SIZE
                add  hl,de
                djnz tr_old
                ret

;---------------------------------------------------------------------
; arrow_save — φύλαξε ΠΟΥ ΕΙΝΑΙ ΤΩΡΑ τα βέλη, πριν κουνηθούν
; ΑΛΛΟΙΩΝΕΙ: BC,DE,HL
;
; ΓΙΑΤΙ ΧΩΡΙΣΤΑ ΑΠΟ ΤΟ ΣΒΗΣΙΜΟ: το σβήσιμο θέλει την ΠΑΛΙΑ θέση, αλλά πρέπει να
; γίνει ΔΙΠΛΑ στο νέο σχέδιο. Όσο τα δύο ήταν μαζί, το βέλος έσβηνε νωρίς μέσα
; στο hero_update και ξαναζωγραφιζόταν μετά το flyback: ανάμεσά τους έτρεχε όλη
; η φυσική, το prep_hero και η ΑΝΑΜΟΝΗ του flyback, δηλαδή το βέλος έλειπε από
; την οθόνη για το μεγαλύτερο μέρος κάθε περάσματος. Αυτό ήταν το τρεμόπαιγμα.
;
; Ο ήρωας δεν τρεμόπαιζε ποτέ γιατί το draw_hero βάζει φόντο και sprite σε ΜΙΑ
; πέραση, χωρίς ενδιάμεση φάση σβησίματος. Το βέλος δεν μπορεί να κάνει το ίδιο
; — με βήμα 6 pixel η παλιά και η νέα θέση είναι δύο ορθογώνια — αλλά μπορεί να
; τα φέρει το ένα δίπλα στο άλλο, μετά το flyback.
;---------------------------------------------------------------------
arrow_save:     ld   hl,arrow_tab
                ld   de,arrow_old
                ld   bc,AR_SIZE*TURRET_MAX
                ldir
                ret

;---------------------------------------------------------------------
; turret_step — ένα καρέ: κινούνται τα βέλη, μετά ρίχνουν οι πυργίσκοι
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
turret_step:    call ar_move
                ; πέφτει μέσα στο tu_fire

;---------------------------------------------------------------------
; tu_fire — ποιος πυργίσκος ρίχνει τώρα
;---------------------------------------------------------------------
tu_fire:        ld   a,(turret_n)
                or   a
                ret  z
                call ar_free            ; υπάρχει ελεύθερη θέση βέλους;
                ret  nc

                call clock_now          ; HL = ρολόι 1/300, χαμηλή λέξη
                ld   (tu_now),hl
                ld   ix,turret_tab
                ld   a,(turret_n)
                ld   b,a
tu_lp:          push bc
                call tf_one
                pop  bc
                ld   de,TS_SIZE
                add  ix,de
                djnz tu_lp
                ret

; --- ένας πυργίσκος -------------------------------------------------
                ; ΣΒΗΣΤΟΣ ΤΩΡΑ; Ο τύπος του κελιού είναι η μόνη αλήθεια: ο
                ; διακόπτης γράφει εκεί, όχι στον πίνακα.
tf_one:         ld   b,(ix+TS_ROW)
                ld   c,(ix+TS_COL)
                call cell_rc
                cp   T_TURRET_V_OFF
                ret  z
                cp   T_TURRET_H_OFF
                ret  z
                ld   (ix+TS_TYPE),a     ; μπορεί να άναψε ξανά
                ld   l,(ix+TS_READY)    ; φορτισμένος;
                ld   h,(ix+TS_READY+1)
                ex   de,hl
                ld   hl,(tu_now)
                or   a
                sbc  hl,de
                ret  c                  ; τώρα < ready -> ακόμα φορτίζει

                ; κέντρο του κελιού σε pixel
                ld   a,(ix+TS_COL)
                add  a,a
                add  a,a
                add  a,a
                add  a,LVL_CELL/2
                ld   l,a
                ld   h,0
                ld   (tu_cx),hl
                ld   a,(ix+TS_ROW)
                add  a,a
                add  a,a
                add  a,a
                add  a,LVL_Y0+LVL_CELL/2
                ld   (tu_cy),a

                ld   a,(ix+TS_TYPE)
                cp   T_TURRET_V
                jr   z,tf_vert

                ld   hl,(hero_x)        ; --- οριζόντιος: d = hero_x - cx ---
                ld   de,(tu_cx)
                or   a
                sbc  hl,de
                ld   (tu_d),hl
                call tf_sign
                ld   (tu_dx),a
                xor  a
                ld   (tu_dy),a
                jr   tf_muzzle

tf_vert:        ld   a,(hero_y)         ; --- κατακόρυφος: d = hero_y - cy ---
                ld   l,a
                ld   h,0
                ld   a,(tu_cy)
                ld   e,a
                ld   d,0
                or   a
                sbc  hl,de
                ld   (tu_d),hl
                call tf_sign
                ld   (tu_dy),a
                xor  a
                ld   (tu_dx),a

                ; --- στόμιο: κέντρο + φορά x (μισό κελί + 1) ---
tf_muzzle:      ld   a,(tu_dx)
                ld   e,a
                call sign_ext
                ld   hl,0
                ld   b,LVL_CELL/2+1
tf_sx:          add  hl,de
                djnz tf_sx
                ld   de,(tu_cx)
                add  hl,de
                ld   (tu_sx),hl

                ld   a,(tu_dy)
                ld   b,a
                add  a,a                ; 5*dy, με το dy να είναι -1 ή +1
                add  a,a
                add  a,b
                ld   b,a
                ld   a,(tu_cy)
                add  a,b
                ld   (tu_sy),a

                ; ΔΥΟ ΤΡΟΠΟΙ. Με ρυθμό ο πυργίσκος δεν ρωτάει τίποτα: ρίχνει
                ; στην ώρα του, είτε τον βλέπεις είτε όχι, είτε είσαι κοντά
                ; είτε στην άλλη άκρη. Φτιάχνει ρυθμό αντί να αντιδρά.
                ld   a,(ix+TS_AUTO)
                or   a
                jr   nz,tf_fire
                ld   hl,(tu_d)
                call tf_inrange
                ret  nc
                call tu_los             ; βλέπει τον ήρωα;
                ret  nc

                ; --- βολή ---
tf_fire:        call ar_free
                ret  nc                 ; γέμισε ενδιάμεσα
                ld   hl,(tu_sx)
                ld   (iy+AR_X),l
                ld   (iy+AR_X+1),h
                ld   a,(tu_sy)
                ld   (iy+AR_Y),a
                ld   a,(tu_dx)
                ld   (iy+AR_DX),a
                ld   a,(tu_dy)
                ld   (iy+AR_DY),a
                ld   (iy+AR_GONE),0
                ld   (iy+AR_ON),1

                ld   a,(ix+TS_AUTO)     ; ο ρυθμός αν υπάρχει, αλλιώς η φόρτιση
                or   a
                jr   nz,tf_secs
                ld   a,(ix+TS_COOL)
tf_secs:        call tf_ticks           ; HL = δευτερόλεπτα x 300
                ld   de,(tu_now)
                add  hl,de
                ld   (ix+TS_READY),l
                ld   (ix+TS_READY+1),h
                ret

;---------------------------------------------------------------------
; tf_sign — HL προσημασμένο -> A = +1 ή -1 (το μηδέν μετράει θετικό)
;
;   ΧΩΡΙΣΤΑ ΑΠΟ ΤΟΝ ΕΛΕΓΧΟ ΕΜΒΕΛΕΙΑΣ: ο πυργίσκος με ρυθμό χρειάζεται τη φορά
;   αλλά ΟΧΙ τα φίλτρα. Όσο ήταν μία ρουτίνα, το ένα δεν γινόταν χωρίς το άλλο.
;---------------------------------------------------------------------
tf_sign:        bit  7,h
                ld   a,1
                ret  z
                ld   a,-1
                ret

;---------------------------------------------------------------------
; tf_inrange — HL προσημασμένο· 0 < |HL| <= TURRET_RANGE ;
; OUT: CF=1 μέσα
;---------------------------------------------------------------------
tf_inrange:     call abs_hl
                ld   a,h
                or   a
                jr   nz,ti_no
                ld   a,l
                or   a
                jr   z,ti_no            ; ακριβώς πάνω του
                cp   TURRET_RANGE+1
                jr   nc,ti_no
                scf
                ret
ti_no:          or   a
                ret

;---------------------------------------------------------------------
; tu_los — ελεύθερη ευθεία από το ΣΤΟΜΙΟ ως τον ήρωα;
;
;   ΑΠΟ ΤΟ ΣΤΟΜΙΟ και όχι από το κέντρο, ώστε ο έλεγχος και η πτήση να
;   ξεκινούν από το ίδιο σημείο και να μη διαφωνούν ποτέ.
; OUT: CF=1 τον βλέπει
;---------------------------------------------------------------------
tu_los:         ld   hl,(tu_sx)
                ld   (los_x),hl
                ld   a,(tu_sy)
                ld   (los_y),a
                ld   b,TURRET_RANGE
los_lp:         push bc
                ld   bc,(los_x)
                ld   a,(los_y)
                ld   e,a
                ld   d,0
                call hit_hero
                jr   c,los_yes
                ld   bc,(los_x)
                ld   a,(los_y)
                ld   e,a
                ld   d,0
                call ar_solid
                jr   c,los_no
                ld   hl,(los_x)         ; ένα pixel παρακάτω
                ld   a,(tu_dx)
                ld   e,a
                call sign_ext
                add  hl,de
                ld   (los_x),hl
                ld   a,(los_y)
                ld   hl,tu_dy
                add  a,(hl)
                ld   (los_y),a
                pop  bc
                djnz los_lp
                or   a
                ret
los_yes:        pop  bc
                scf
                ret
los_no:         pop  bc
                or   a
                ret

;---------------------------------------------------------------------
; ar_move — τα βέλη, ΕΝΑ PIXEL ΤΗ ΦΟΡΑ
;
;   Ποτέ πήδημα των έξι: ο ίδιος κανόνας με την πτώση και το βάδισμα. Με βήμα
;   έξι, ένα βέλος περνάει μέσα από τοίχο λεπτότερο από έξι pixel και
;   προσπερνά τον ήρωα όταν η φάση δεν ταιριάζει.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
ar_move:        ld   iy,arrow_tab
                ld   c,TURRET_MAX
am_slot:        ld   a,(iy+AR_ON)
                or   a
                jr   z,am_next
                ld   b,ARROW_STEP
am_px:          push bc
                call am_one             ; CF=1 -> πέθανε
                pop  bc
                jr   c,am_next
                djnz am_px
am_next:        ld   de,AR_SIZE
                add  iy,de
                dec  c
                jr   nz,am_slot
                ret

; --- ένα pixel ενός βέλους. OUT: CF=1 αν έσβησε ---------------------
am_one:         ld   l,(iy+AR_X)
                ld   h,(iy+AR_X+1)
                ld   a,(iy+AR_DX)
                ld   e,a
                call sign_ext
                add  hl,de
                ld   (iy+AR_X),l
                ld   (iy+AR_X+1),h
                ld   a,(iy+AR_Y)
                add  a,(iy+AR_DY)
                ld   (iy+AR_Y),a

                inc  (iy+AR_GONE)
                ld   a,(iy+AR_GONE)
                cp   TURRET_RANGE
                jr   nc,am_kill         ; εξάντλησε την εμβέλεια

                ld   c,(iy+AR_X)
                ld   b,(iy+AR_X+1)
                ld   a,(iy+AR_Y)
                ld   e,a
                ld   d,0
                call hit_hero
                jr   c,am_hit
                ld   c,(iy+AR_X)
                ld   b,(iy+AR_X+1)
                ld   a,(iy+AR_Y)
                ld   e,a
                ld   d,0
                call ar_solid
                jr   c,am_kill
                or   a                  ; ζει
                ret

am_hit:         ld   a,(iy+AR_GONE)
                call ar_hurt
am_kill:        ld   (iy+AR_ON),0
                scf
                ret

;---------------------------------------------------------------------
; ar_hurt — ζημιά κατά ΔΙΑΝΥΘΕΙΣΑ απόσταση: όσο πιο κοντά, τόσο πιο πολύ
;   IN: A = pixel που διανύθηκαν
;---------------------------------------------------------------------
ar_hurt:        ld   c,ARROW_DMG_FAR
                cp   TURRET_RANGE/3
                jr   nc,ah_mid
                ld   c,ARROW_DMG_NEAR
                jr   ah_do
ah_mid:         cp   2*(TURRET_RANGE/3)
                jr   nc,ah_do
                ld   c,ARROW_DMG_MID
ah_do:          ld   a,(hero_hurt)      ; άτρωτος: το χτύπημα αγνοείται ΕΝΤΕΛΩΣ
                or   a
                ret  nz
                ld   a,(hero_energy)
                sub  c
                jr   nc,ah_set
                xor  a                  ; 0 = θάνατος
ah_set:         ld   (hero_energy),a
                ld   a,1
                ld   (hud_dirty),a
                ld   a,HURT_FRAMES
                ld   (hero_hurt),a
                ld   a,SFXID_HURT
                jp   sfx_play

;---------------------------------------------------------------------
; hit_hero — είναι το pixel (BC,DE) μέσα στο σώμα του ήρωα;
;
;   Το σώμα είναι ράβδος 7x12 κατά τη βαρύτητα, οπότε το ορθογώνιο γυρίζει
;   μαζί της. Στις διαγώνιες παίρνουμε το μεγαλύτερο και στις δύο διαστάσεις —
;   το sprite εκεί είναι ούτως ή άλλως 13x13.
; OUT: CF=1 τον βρήκε      ΑΛΛΟΙΩΝΕΙ: AF, HL   (BC, DE διατηρούνται)
;---------------------------------------------------------------------
hit_hero:       push bc
                push de
                ld   a,(hero_g)
                and  1
                jr   nz,hh_diag         ; μονή φορά -> διαγώνιο σώμα
                ld   a,(hero_g)
                and  2
                jr   nz,hh_side         ; 2 ή 6 -> ξαπλωμένο
                ld   a,WALL_A
                ld   (hh_hw),a
                ld   a,FEET_B
                jr   hh_set
hh_side:        ld   a,FEET_B
                ld   (hh_hw),a
                ld   a,WALL_A
                jr   hh_set
hh_diag:        ld   a,FEET_B
                ld   (hh_hw),a
                ld   a,FEET_B
hh_set:         ld   (hh_hh),a

                ld   hl,(hero_x)        ; |x - hero_x| <= hw ;
                or   a
                sbc  hl,bc
                call abs_hl
                ld   a,h
                or   a
                jr   nz,hh_no
                ld   a,(hh_hw)
                cp   l
                jr   c,hh_no

                ld   a,(hero_y)         ; |y - hero_y| <= hh ;
                ld   l,a
                ld   h,0
                or   a
                sbc  hl,de
                call abs_hl
                ld   a,h
                or   a
                jr   nz,hh_no
                ld   a,(hh_hh)
                cp   l
                jr   c,hh_no
                pop  de
                pop  bc
                scf
                ret
hh_no:          pop  de
                pop  bc
                or   a
                ret

;---------------------------------------------------------------------
; ar_solid — σταματά εδώ το βέλος;
;
;   ΟΙ ΜΟΝΟΔΡΟΜΕΣ ΜΕΤΡΑΝΕ ΠΑΝΤΑ ΣΤΕΡΕΕΣ, σε αντίθεση με το solid_at που τις
;   κρίνει από τη φορά της βαρύτητας — για ένα βέλος η βαρύτητα δεν σημαίνει
;   τίποτα, και μια πλατφόρμα που την περνάς πηδώντας δεν έχει λόγο να αφήνει
;   βέλη να τη διαπερνούν πλάγια.
;   IN: BC = x, DE = y     OUT: CF=1 στερεό
;---------------------------------------------------------------------
ar_solid:       push bc
                push de
                call cell_at
                or   a
                jr   z,as_no            ; κενό
                cp   T_RAMP_UL+1
                jr   nc,as_game
                pop  de                 ; γεωμετρία 1..5: το solid_at ξέρει το
                pop  bc                 ; υπο-κελιακό σχήμα των ραμπών
                jp   solid_at
as_game:        ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                and  F_SOLID|F_ONEWAY
                jr   z,as_no
                pop  de
                pop  bc
                scf
                ret
as_no:          pop  de
                pop  bc
                or   a
                ret

;---------------------------------------------------------------------
; arrow_erase / arrow_draw — τα βέλη στην οθόνη
;
;   ΔΥΟ ΞΕΧΩΡΙΣΤΕΣ ΦΑΣΕΙΣ, ΚΑΙ ΟΧΙ ΜΙΑ όπως στον ήρωα. Ο ήρωας σβήνεται και
;   ζωγραφίζεται σε ένα πέρασμα γιατί η περιοχή του είναι μία και γνωστή· τα
;   βέλη κινούνται 6 pixel ανά καρέ, οπότε η ένωση παλιάς και νέας θέσης είναι
;   δύο ξεχωριστά ορθογώνια.
;
;   Η ΣΕΙΡΑ ΜΕΣΑ ΣΤΟ ΠΕΡΑΣΜΑ:
;
;       hero_update -> arrow_save (η θέση ΠΡΙΝ κουνηθούν), turret_step
;       ...υπόλοιπη φυσική, prep_hero, MC_WAIT_FLYBACK...
;       arrow_erase (από το αντίγραφο), draw_hero, arrow_draw
;
;   ΟΙ ΔΥΟ ΦΑΣΕΙΣ ΕΙΝΑΙ ΚΟΛΛΗΤΕΣ ΕΠΙΤΗΔΕΣ. Το σβήσιμο γινόταν μέσα στο
;   hero_update: ανάμεσα σε αυτό και τη σχεδίαση έτρεχε όλη η φυσική, ο
;   μετασχηματισμός του sprite και η αναμονή του flyback, οπότε το βέλος έλειπε
;   από την οθόνη το μεγαλύτερο μέρος κάθε περάσματος και τρεμόπαιζε.
;
;   Το σβήσιμο έρχεται ΠΡΙΝ τον ήρωα ώστε βέλος που τον ακουμπά να μη σβήνει
;   κομμάτι του, και η σχεδίαση ΜΕΤΑ ώστε ένα βέλος από πάνω του να φαίνεται.
;   Βέλος που πέθανε μέσα στο πέρασμα σβήνεται κι αυτό: στο αντίγραφο ήταν
;   ακόμα αναμμένο.
;
;   ΤΟ ΣΧΗΜΑ: βελάκι έντεκα pixel σε συντεταγμένες «κατά μήκος / εγκάρσια»,
;   ώστε μια λίστα να εξυπηρετεί και τις τέσσερις φορές — η φορά είναι το
;   (dx,dy) και η εγκάρσια το (dy,dx).
;
;   ΔΥΟ ΧΡΩΜΑΤΑ, ΚΑΙ ΟΧΙ ΓΙΑ ΟΜΟΡΦΙΑ. Ήταν επτά pixel όλα σε pen 3, το
;   πορτοκαλί που το concept art ορίζει για τους κινδύνους — αλλά πορτοκαλί
;   είναι ΚΑΙ οι ακμές κάθε πλακιδίου, οπότε η σφαίρα χανόταν πάνω τους. Τώρα η
;   ουρά είναι pen 1 (λευκό, ό,τι και ο ήρωας: το πιο ευδιάκριτο της παλέτας)
;   και η μύτη μένει πορτοκαλί, γιατί αυτή είναι το επικίνδυνο άκρο.
;   Τεκμηριωμένο στο docs/concept-art.md.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
ARROW_PIX       equ  11
PEN_TAIL        equ  1          ; λευκό: φαίνεται πάνω σε ό,τι κι αν περνά
PEN_HEAD        equ  3          ; πορτοκαλί: το χρώμα του κινδύνου

; (κατά μήκος, εγκάρσια, pen)
arrow_shape:    db   -3,0,PEN_TAIL,  -2,0,PEN_TAIL
                db   -1,0,PEN_TAIL,   0,0,PEN_TAIL
                db    1,0,PEN_HEAD,   2,0,PEN_HEAD,  3,0,PEN_HEAD
                db    1,-1,PEN_HEAD,  1,1,PEN_HEAD
                db    2,-1,PEN_HEAD,  2,1,PEN_HEAD

                ; ΑΠΟ ΤΟ ΑΝΤΙΓΡΑΦΟ, όχι από τον ζωντανό πίνακα: τη στιγμή που
                ; τρέχει αυτό, τα βέλη έχουν ήδη κουνηθεί. Σβήνει και όποιο
                ; πέθανε μέσα στο πέρασμα — στο αντίγραφο ήταν ακόμα αναμμένο.
arrow_erase:    ld   iy,arrow_old
                ld   c,TURRET_MAX
ae_slot:        ld   a,(iy+AR_ON)
                or   a
                call nz,ae_one
                ld   de,AR_SIZE
                add  iy,de
                dec  c
                jr   nz,ae_slot
                ret

; --- ξαναζωγραφίζει τα κελιά που κάλυπτε ένα βέλος (το πολύ 2x2) ------
ae_one:         push bc
                ld   l,(iy+AR_X)        ; στήλες κελιών: (x-2)>>3 ως (x+2)>>3
                ld   h,(iy+AR_X+1)
                ld   de,-3
                add  hl,de
                bit  7,h                ; αριστερά από την οθόνη
                jr   z,ae_c0ok
                ld   hl,0
ae_c0ok:        srl  h
                rr   l
                srl  l
                srl  l
                ld   a,l
                ld   (ae_c0),a
                ld   l,(iy+AR_X)
                ld   h,(iy+AR_X+1)
                ld   de,3
                add  hl,de
                srl  h
                rr   l
                srl  l
                srl  l
                ld   a,l
                cp   LVL_COLS
                jr   c,ae_c1ok
                ld   a,LVL_COLS-1
ae_c1ok:        ld   (ae_c1),a

                ld   a,(iy+AR_Y)        ; γραμμές κελιών, με το HUD από πάνω
                sub  LVL_Y0+3
                jr   nc,ae_r0ok
                xor  a
ae_r0ok:        srl  a
                srl  a
                srl  a
                ld   (ae_r0),a
                ld   a,(iy+AR_Y)
                add  a,3
                sub  LVL_Y0
                srl  a
                srl  a
                srl  a
                cp   LVL_ROWS
                jr   c,ae_r1ok
                ld   a,LVL_ROWS-1
ae_r1ok:        ld   (ae_r1),a

ae_rlp:         ld   a,(ae_c0)
                ld   (ae_c),a
ae_clp:         ld   a,(ae_r0)
                ld   b,a
                ld   a,(ae_c)
                ld   c,a
                push iy
                call draw_tile
                pop  iy
                ld   hl,ae_c
                inc  (hl)
                ld   a,(hl)
                ld   hl,ae_c1
                cp   (hl)
                jr   c,ae_clp
                jr   z,ae_clp
                ld   hl,ae_r0
                inc  (hl)
                ld   a,(hl)
                ld   hl,ae_r1
                cp   (hl)
                jr   c,ae_rlp
                jr   z,ae_rlp
                pop  bc
                ret

arrow_draw:     ld   iy,arrow_tab
                ld   c,TURRET_MAX
ad_slot:        ld   a,(iy+AR_ON)
                or   a
                call nz,ad_one
                ld   de,AR_SIZE
                add  iy,de
                dec  c
                jr   nz,ad_slot
                ret

ad_one:         push bc
                ld   hl,arrow_shape
                ld   b,ARROW_PIX
ad_lp:          push bc
                push hl
                inc  hl                 ; τριάδα: κατά μήκος, εγκάρσια, pen
                inc  hl
                ld   a,(hl)
                ld   (ad_pen),a
                dec  hl
                ld   b,(hl)
                dec  hl
                ld   a,(hl)
                call ad_pix
                pop  hl
                ld   de,3
                add  hl,de
                pop  bc
                djnz ad_lp
                pop  bc
                ret

; --- ένα pixel: (x,y) = θέση + a*(dx,dy) + c*(dy,dx) -----------------
;   Τα a και c ζουν σε μνήμη και όχι σε καταχωρητές: χρειάζονται και για το x
;   και για το y, και το ad_mul χαλάει ό,τι βρει.
ad_pix:         ld   (ad_a),a           ; κατά μήκος
                ld   a,b
                ld   (ad_c),a           ; εγκάρσια

                ld   a,(ad_a)           ; x = AR_X + a*dx + c*dy
                ld   e,(iy+AR_DX)
                call ad_mul
                push hl
                ld   a,(ad_c)
                ld   e,(iy+AR_DY)
                call ad_mul
                pop  de
                add  hl,de
                ld   e,(iy+AR_X)
                ld   d,(iy+AR_X+1)
                add  hl,de
                ld   (ad_x),hl

                ld   a,(ad_a)           ; y = AR_Y + a*dy + c*dx
                ld   e,(iy+AR_DY)
                call ad_mul
                push hl
                ld   a,(ad_c)
                ld   e,(iy+AR_DX)
                call ad_mul
                pop  de
                add  hl,de
                ld   a,(iy+AR_Y)
                add  a,l
                ld   (ad_y),a

                ld   hl,(ad_x)          ; έξω από το playfield;
                bit  7,h
                ret  nz
                ld   de,LVL_COLS*LVL_CELL
                or   a
                sbc  hl,de
                ret  nc
                ld   a,(ad_y)
                cp   LVL_Y0
                ret  c
                cp   LVL_Y0+LVL_ROWS*LVL_CELL
                ret  nc

                ld   hl,(ad_x)          ; byte και θέση pixel μέσα του
                ld   a,l
                and  3
                ld   (ad_slot_i),a
                srl  h
                rr   l
                srl  l
                ld   c,l
                ld   a,(ad_y)
                ld   b,a
                call scr_addr
                push hl
                ld   a,(ad_slot_i)      ; μάσκα: σβήσε τα δύο bits του pixel
                ld   e,a
                ld   d,0
                ld   hl,spr_andtab
                add  hl,de
                ld   c,(hl)
                ld   a,(ad_pen)         ; pixtab[pen*4 + slot]
                add  a,a
                add  a,a
                ld   e,a
                ld   a,(ad_slot_i)
                add  a,e
                ld   e,a
                ld   d,0
                ld   hl,spr_pixtab
                add  hl,de
                ld   b,(hl)
                pop  hl
                ld   a,(hl)
                and  c
                or   b
                ld   (hl),a
                ret

; ad_mul — HL = A * E, όπου το E είναι ΜΟΝΟ -1, 0 ή +1
;   Δεν είναι γενικός πολλαπλασιασμός και δεν πρέπει να γίνει: οι φορές είναι
;   τρεις τιμές, και ένας βρόχος πρόσθεσης εδώ έσπασε ήδη μια φορά επειδή
;   χαλούσε τον καταχωρητή που κρατούσε τον έναν από τους δύο όρους.
ad_mul:         ld   c,a
                ld   a,e
                or   a
                jr   z,am_zero
                bit  7,a
                ld   a,c
                jr   z,am_ext
                neg
am_ext:         ld   l,a
                ld   h,0
                bit  7,a
                ret  z
                dec  h
                ret
am_zero:        ld   hl,0
                ret

ad_a            db   0
ad_c            db   0
ad_pen          db   0
ae_c0           db   0
ae_c1           db   0
ae_r0           db   0
ae_r1           db   0
ae_c            db   0
ad_x            dw   0
ad_y            db   0
ad_slot_i       db   0

;--- βοηθητικά --------------------------------------------------------
; ar_free — IY -> ελεύθερη θέση βέλους. OUT: CF=1 βρέθηκε
ar_free:        ld   iy,arrow_tab
                ld   b,TURRET_MAX
af_lp:          ld   a,(iy+AR_ON)
                or   a
                jr   z,af_yes
                ld   de,AR_SIZE
                add  iy,de
                djnz af_lp
                or   a
                ret
af_yes:         scf
                ret

; tf_ticks — HL = A * 300, δηλαδή δευτερόλεπτα σε παλμούς του 1/300
tf_ticks:       ld   hl,0
                or   a
                ret  z
                ld   de,300
tk_lp:          add  hl,de
                dec  a
                jr   nz,tk_lp
                ret

; sign_ext — DE = προσημασμένη επέκταση του E
sign_ext:       ld   d,0
                bit  7,e
                ret  z
                dec  d
                ret

; abs_hl — HL = |HL|
abs_hl:         bit  7,h
                ret  z
                ld   a,h
                cpl
                ld   h,a
                ld   a,l
                cpl
                ld   l,a
                inc  hl
                ret

; cell_rc — ο τύπος του κελιού (B,C) = (γραμμή, στήλη)
;   Απευθείας στο cell_buf: το cell_at θέλει pixel και θα ξανάκανε τη διαίρεση
;   που μόλις κάναμε ανάποδα.
cell_rc:        ld   l,b
                ld   h,0
                add  hl,hl              ; γραμμή * 40 = *32 + *8
                add  hl,hl
                add  hl,hl              ; HL = *8
                ld   d,h
                ld   e,l                ; DE = *8, κρατημένο
                add  hl,hl              ; *16
                add  hl,hl              ; *32
                add  hl,de              ; *40
                ld   e,c
                ld   d,0
                add  hl,de
                ld   de,cell_buf
                add  hl,de
                ld   a,(hl)
                ret

; clock_now — HL = χαμηλή λέξη του μετρητή 1/300 του firmware
clock_now:      jp   KL_TIME_PLEASE

;--- κατάσταση --------------------------------------------------------
turret_n        db   0          ; πόσοι πυργίσκοι στην αίθουσα
tu_now          dw   0
tu_d            dw   0
tu_cx           dw   0
tu_cy           db   0
tu_sx           dw   0
tu_sy           db   0
tu_dx           db   0
tu_dy           db   0
los_x           dw   0
los_y           db   0
hh_hw           db   0
hh_hh           db   0
