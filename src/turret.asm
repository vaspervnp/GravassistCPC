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
TS_SIZE         equ  5

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
tl_col:         ld   a,(hl)
                cp   T_TURRET_V
                jr   z,tl_add
                cp   T_TURRET_H
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
tf_one:         ld   l,(ix+TS_READY)    ; φορτισμένος;
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

                ; --- οριζόντιος: d = hero_x - cx ---
                ld   hl,(hero_x)
                ld   de,(tu_cx)
                or   a
                sbc  hl,de
                call tf_range           ; OUT: A = πρόσημο (1/-1), CF=0 αν άκυρο
                ret  nc
                ld   (tu_dx),a
                xor  a
                ld   (tu_dy),a
                jr   tf_shoot

tf_vert:        ld   a,(hero_y)         ; --- κατακόρυφος: d = hero_y - cy ---
                ld   l,a
                ld   h,0
                ld   a,(tu_cy)
                ld   e,a
                ld   d,0
                or   a
                sbc  hl,de
                call tf_range
                ret  nc
                ld   (tu_dy),a
                xor  a
                ld   (tu_dx),a

                ; --- στόμιο: κέντρο + φορά x (μισό κελί + 1) ---
tf_shoot:       ld   a,(tu_dx)
                ld   e,a
                call sign_ext           ; DE = προσημασμένο dx
                ld   hl,0
                ld   b,LVL_CELL/2+1
tf_sx:          add  hl,de
                djnz tf_sx
                ld   de,(tu_cx)
                add  hl,de
                ld   (tu_sx),hl

                ld   a,(tu_dy)
                ld   b,a
                add  a,a                ; b*(CELL/2+1) χωρίς πολλαπλασιασμό:
                add  a,a                ; το dy είναι -1, 0 ή +1
                add  a,b                ; -> a = 5*dy  (LVL_CELL/2+1 = 5)
                ld   b,a
                ld   a,(tu_cy)
                add  a,b
                ld   (tu_sy),a

                call tu_los             ; βλέπει τον ήρωα;
                ret  nc

                ; --- βολή ---
                call ar_free
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

                ld   hl,(tu_now)        ; ξαναφορτίζει σε 5 δευτερόλεπτα
                ld   de,TURRET_RELOAD
                add  hl,de
                ld   (ix+TS_READY),l
                ld   (ix+TS_READY+1),h
                ret

;---------------------------------------------------------------------
; tf_range — HL = απόσταση με πρόσημο· είναι μέσα στην εμβέλεια;
; OUT: CF=1 και A = +1/-1 (η φορά)· CF=0 αν 0 ή έξω από την εμβέλεια
;---------------------------------------------------------------------
tf_range:       bit  7,h
                jr   nz,tr_neg
                ld   a,h                ; θετική: > 255 σημαίνει σίγουρα έξω
                or   a
                jr   nz,tr_no
                ld   a,l
                or   a
                jr   z,tr_no            ; ακριβώς πάνω του
                cp   TURRET_RANGE+1
                jr   nc,tr_no
                ld   a,1
                scf
                ret
tr_neg:         ld   a,h                ; αρνητική: -HL
                cpl
                ld   h,a
                ld   a,l
                cpl
                ld   l,a
                inc  hl
                ld   a,h
                or   a
                jr   nz,tr_no
                ld   a,l
                cp   TURRET_RANGE+1
                jr   nc,tr_no
                ld   a,-1
                scf
                ret
tr_no:          or   a
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

; clock_now — HL = χαμηλή λέξη του μετρητή 1/300 του firmware
clock_now:      jp   KL_TIME_PLEASE

;--- κατάσταση --------------------------------------------------------
turret_n        db   0          ; πόσοι πυργίσκοι στην αίθουσα
tu_now          dw   0
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
