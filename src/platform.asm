; ---------------------------------------------------------------------------
; platform.asm — κινούμενες πλατφόρμες
;
; ΤΟ ΜΟΝΟ ΑΝΤΙΚΕΙΜΕΝΟ ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ ΠΟΥ ΔΕΝ ΕΙΝΑΙ ΚΕΛΙ. Όλα τα άλλα ζουν στο
; πλέγμα: το solid_at ρωτάει «τι τύπος είναι εδώ» και ήρωας, κιβώτια και βέλη
; παίρνουν την απάντηση δωρεάν. Η πλατφόρμα κινείται ΑΝΑ PIXEL, οπότε δεν
; χωράει σε κελί — ζει σε δικό της πίνακα, με θέση σε pixel.
;
; Μεταγραφή του tools/physics.py (Room._build_platforms, plat_step, plat_riding)
; και ελεγμένη απέναντί του: tools/test_platform.py.
;
; ΓΙΑΤΙ Ο ΕΛΕΓΧΟΣ ΜΠΑΙΝΕΙ ΜΕΣΑ ΣΤΟ solid_at: ένα δεύτερο σύστημα σύγκρουσης θα
; έπρεπε να το ρωτήσει κάθε probe του ήρωα, κάθε κιβώτιο και κάθε βέλος —
; δεκάδες σημεία, και το πρώτο που θα ξεχνιόταν θα ήταν κάτι που περνάει μέσα
; από την πλατφόρμα. Το τίμημα είναι μία σύγκριση στην πιο καυτή ρουτίνα του
; παιχνιδιού· με plat_n = 0 βγαίνει αμέσως, δηλαδή σχεδόν τζάμπα στις αίθουσες
; χωρίς πλατφόρμα, που είναι σχεδόν όλες.
;
; ΣΤΕΡΕΗ ΜΟΝΟ ΑΠΟ ΠΑΝΩ, με τον ίδιο κανόνα που κρίνει τις μονόδρομες: η
; βαρύτητα του ελέγχου πρέπει να είναι PLAT_GRAV. Είναι ανελκυστήρας, όχι
; κουτί.
; ---------------------------------------------------------------------------

; --- διάταξη εγγραφής ------------------------------------------------
PL_X            equ  0          ; dw  τρέχον x σε pixel (ως 319)
PL_Y            equ  2          ; db  τρέχον y
PL_W            equ  3          ; db  πλάτος σε pixel
PL_H            equ  4          ; db  ύψος σε pixel
PL_AX           equ  5          ; dw  άκρο A
PL_AY           equ  7          ; db
PL_BX           equ  8          ; dw  άκρο B
PL_BY           equ  10         ; db
PL_CH           equ  11         ; db  κανάλι διακόπτη· 0 = κανείς
PL_SPD          equ  12         ; db  pixel ανά δευτερόλεπτο
PL_FLG          equ  13         ; db  bit0 κινείται, bit1 φορά προς A
PL_ACC          equ  14         ; dw  συσσωρευμένα speed x παλμοί
PL_WAIT         equ  16         ; dw  παλμοί ακινησίας στο άκρο
PL_RID          equ  18         ; db  τύπος επιβάτη-διακόπτη· 0 = κανένας
PL_RDX          equ  19         ; db  μετατόπισή του από το x της πλατφόρμας
PL_RCH          equ  20         ; db  το κανάλι ΤΟΥ
PL_SIZE         equ  21

PLF_MOVE        equ  1          ; bit0
PLF_BACK        equ  2          ; bit1: κινείται προς το άκρο A

;---------------------------------------------------------------------
; plat_load — χτίζει τον πίνακα από τον έκτο πίνακα της αίθουσας
;
;   Καλείται ΜΕΤΑ το jr_apply, όπως και το turret_load: το ημερολόγιο μπορεί
;   να έχει αλλάξει κελιά και ο επιβάτης πρέπει να διαβαστεί από την ΤΕΛΙΚΗ
;   αίθουσα.
;
;   ΣΒΗΝΕΙ ΤΑ ΚΕΛΙΑ ΤΗΣ από το cell_buf, όπως κάνει και το μοντέλο: δείχνουν
;   πού ξεκινάει, δεν είναι υλικό. Αν έμεναν, θα υπήρχε μόνιμο στερεό στην
;   αφετηρία της ενώ εκείνη θα είχε φύγει.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_load:      xor  a
                ld   (plat_n),a
                call clock_now
                ld   (plat_last),hl
                ld   hl,(room_plat)
                ld   ix,plat_tab
pl_next:        ld   a,(hl)
                cp   #FF
                ret  z
                ld   a,(plat_n)
                cp   PLAT_MAX           ; ό,τι περισσεύει αγνοείται· το
                jp   nc,pl_skip         ; tools/roomfile.py σπάει το build
                inc  a
                ld   (plat_n),a

                ld   c,(hl)             ; C = στήλη
                inc  hl
                ld   b,(hl)             ; B = γραμμή
                inc  hl
                push hl
                call pl_pix             ; DE = x σε pixel, A = y
                ld   (ix+PL_X),e
                ld   (ix+PL_X+1),d
                ld   (ix+PL_AX),e
                ld   (ix+PL_AX+1),d
                ld   (ix+PL_Y),a
                ld   (ix+PL_AY),a
                pop  hl

                ld   a,(hl)             ; πλάτος σε κελιά -> pixel
                inc  hl
                add  a,a
                add  a,a
                add  a,a
                ld   (ix+PL_W),a
                ld   a,(hl)             ; ύψος
                inc  hl
                add  a,a
                add  a,a
                add  a,a
                ld   (ix+PL_H),a

                ld   c,(hl)             ; δεύτερο άκρο
                inc  hl
                ld   b,(hl)
                inc  hl
                push hl
                call pl_pix
                ld   (ix+PL_BX),e
                ld   (ix+PL_BX+1),d
                ld   (ix+PL_BY),a
                pop  hl

                ; ΤΟ ΚΑΝΑΛΙ ΚΑΙ Η ΣΗΜΑΙΑ ΜΑΖΙ: bit 7 = ξεκινά σταματημένη. Ο
                ; τύπος του κελιού («M» ή «m») δεν υπάρχει πια εδώ — σβήνεται
                ; από το πλέγμα πριν γραφτεί το RLE — οπότε ταξιδεύει έτσι.
                ld   a,(hl)
                inc  hl
                ld   (ix+PL_FLG),PLF_MOVE
                bit  7,a
                jr   z,pl_moving
                ld   (ix+PL_FLG),0
pl_moving:      and  7
                ld   (ix+PL_CH),a
                ld   a,(hl)             ; ταχύτητα
                inc  hl
                ld   (ix+PL_SPD),a

                xor  a
                ld   (ix+PL_ACC),a
                ld   (ix+PL_ACC+1),a
                ld   (ix+PL_WAIT),a
                ld   (ix+PL_WAIT+1),a
                ld   (ix+PL_RID),a
                ld   (ix+PL_RDX),a
                ld   (ix+PL_RCH),a
                push hl
                call pl_clear           ; τα κελιά της φεύγουν από το πλέγμα
                call pl_rider           ; και ο διακόπτης από πάνω της
                pop  hl
                ld   de,PL_SIZE
                add  ix,de
                jp   pl_next

pl_skip:        ld   de,8
                add  hl,de
                jp   pl_next

;---------------------------------------------------------------------
; pl_pix — κελί (C=στήλη, B=γραμμή) -> DE = x σε pixel, A = y
;
;   ΣΕ 16 BIT ΤΟ X: η γραμμή είναι 320 pixel και από τη στήλη 32 και πέρα το
;   col*8 δεν χωράει σε byte. Ο πυργίσκος πλήρωσε ακριβώς αυτό.
; ΑΛΛΟΙΩΝΕΙ: AF, DE, HL
;---------------------------------------------------------------------
pl_pix:         ld   l,c
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ex   de,hl
                ld   a,b
                add  a,a
                add  a,a
                add  a,a
                add  a,LVL_Y0
                ret

;---------------------------------------------------------------------
; pl_clear — αδειάζει τα κελιά της πλατφόρμας IX από το cell_buf
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
pl_clear:       call pl_cells           ; B=γραμμή, C=στήλη, D=γραμμές, E=στήλες
pc_row:         push bc
                push de
                ; ΤΟ DE ΦΥΛΑΓΕΤΑΙ: το cell_addr το χαλάει (γραπτό συμβόλαιο),
                ; και εδώ είναι ο μετρητής στηλών — χωρίς αυτό ο βρόχος δεν
                ; τελείωνε ποτέ και η φόρτωση της αίθουσας κρεμούσε.
pc_col:         push bc
                push de
                call cell_addr          ; HL -> το κελί
                ld   (hl),0
                pop  de
                pop  bc
                inc  c
                dec  e
                jr   nz,pc_col
                pop  de
                pop  bc
                inc  b
                dec  d
                jr   nz,pc_row
                ret

;---------------------------------------------------------------------
; pl_cells — η πλατφόρμα IX σε κελιά: B=γραμμή, C=στήλη, D=πλήθος γραμμών,
;            E=πλήθος στηλών
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
pl_cells:       ld   l,(ix+PL_AX)
                ld   h,(ix+PL_AX+1)
                srl  h
                rr   l
                srl  l
                srl  l
                ld   c,l                ; C = στήλη
                ld   a,(ix+PL_AY)
                sub  LVL_Y0
                srl  a
                srl  a
                srl  a
                ld   b,a                ; B = γραμμή
                ld   a,(ix+PL_W)
                srl  a
                srl  a
                srl  a
                ld   e,a                ; E = στήλες
                ld   a,(ix+PL_H)
                srl  a
                srl  a
                srl  a
                ld   d,a                ; D = γραμμές
                ret

; Το cell_addr ζει στο src/level.asm — ίδια σύμβαση (C=στήλη, B=γραμμή).

;---------------------------------------------------------------------
; pl_rider — διακόπτης ακριβώς ΠΑΝΩ από την πλατφόρμα γίνεται επιβάτης της
;
;   ΔΕΝ ΧΡΕΙΑΖΕΤΑΙ ΔΗΛΩΣΗ: ο διακόπτης μένει κανονικό κελί με το κανονικό του
;   κανάλι, και η σχέση βγαίνει από τη ΓΕΩΜΕΤΡΙΑ. Ο editor απορρίπτει ό,τι
;   άλλο κάθεται εκεί, γιατί κάθε άλλο αντικείμενο θα έμενε καρφωμένο στο κελί
;   του ενώ η πλατφόρμα φεύγει από κάτω του.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
pl_rider:       call pl_cells
                ld   a,b
                or   a
                ret  z                  ; στην πάνω γραμμή: δεν υπάρχει «πάνω»
                dec  b                  ; η σειρά από πάνω της
pr_col:         push bc
                push de
                push bc
                call cell_rc            ; A = τύπος κελιού
                pop  bc
                ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                and  F_SWITCH
                jr   z,pr_no
                ld   (ix+PL_RID),e      ; ο τύπος του
                pop  de
                pop  bc
                push bc
                ld   a,c                ; μετατόπιση = (στήλη - στήλη0) x 8
                push af
                ld   l,(ix+PL_AX)
                ld   h,(ix+PL_AX+1)
                srl  h
                rr   l
                srl  l
                srl  l
                pop  af
                sub  l
                add  a,a
                add  a,a
                add  a,a
                ld   (ix+PL_RDX),a
                pop  bc
                ; ΟΙ ΔΥΟ ΡΟΥΤΙΝΕΣ ΘΕΛΟΥΝ ΑΝΤΙΘΕΤΗ ΣΕΙΡΑ: το cell_rc παίρνει
                ; B=γραμμή C=στήλη, το cell_attr B=στήλη C=γραμμή. Χωρίς την
                ; εναλλαγή το κανάλι έβγαινε 0 και ο διακόπτης του επιβάτη δεν
                ; άνοιγε τίποτα.
                ld   a,b
                ld   b,c
                ld   c,a
                call cell_attr          ; A = το κανάλι του
                ld   (ix+PL_RCH),a
                ld   a,b                ; πίσω, για το cell_rc από κάτω
                ld   b,c
                ld   c,a
                call cell_rc            ; ξανά, για τη διεύθυνση
                call cell_addr
                ld   (hl),0             ; φεύγει από το πλέγμα
                ret
pr_no:          pop  de
                pop  bc
                inc  c
                dec  e
                jr   nz,pr_col
                ret

;---------------------------------------------------------------------
; plat_at — είναι το pixel (BC = x, DE = y) μέσα σε πλατφόρμα;
;
;   ΔΕΝ ΚΡΙΝΕΙ ΤΗ ΒΑΡΥΤΗΤΑ — αυτό το κάνει ο καλών, όπως και με τις μονόδρομες.
; OUT: CF=1 μέσα
; ΔΙΑΤΗΡΕΙ: BC, DE, IX   ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
plat_at:        ld   a,(plat_n)
                or   a
                ret  z                  ; CF=0: καμία πλατφόρμα, φύγε αμέσως
                push bc
                push de
                push ix
                ld   ix,plat_tab
                ; Ο ΜΕΤΡΗΤΗΣ ΣΕ ΜΝΗΜΗ ΚΑΙ ΟΧΙ ΣΕ ΚΑΤΑΧΩΡΗΤΗ: το BC κρατά το x,
                ; το DE το y, και το pa_one γράφει στο HL. Με τον μετρητή στο H
                ; γινόταν σκουπίδι στην πρώτη κιόλας σύγκριση, ο βρόχος διάβαζε
                ; τυχαία μνήμη ως εγγραφή πλατφόρμας και το solid_at έλεγε
                ; «στερεό» παντού.
                ld   (pa_left),a
pa_lp:          call pa_one
                jr   c,pa_yes
                push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                ld   hl,pa_left
                dec  (hl)
                jr   nz,pa_lp
                pop  ix
                pop  de
                pop  bc
                or   a
                ret
pa_yes:         pop  ix
                pop  de
                pop  bc
                scf
                ret

;---------------------------------------------------------------------
; pa_one — μία πλατφόρμα. BC = x, DE = y (D=0). OUT: CF=1 μέσα
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
pa_one:         ld   a,e                ; ΤΟ Y ΦΥΛΑΓΕΤΑΙ ΠΡΩΤΑ: ο υπολογισμός του
                ld   (pa_y),a           ; x το περνάει από HL και DE, και ένα
                                        ; ex de,hl το έσβηνε πριν προλάβει να
                                        ; συγκριθεί — η πλατφόρμα ήταν στερεή
                                        ; σε λάθος ύψος και δεν κουβαλούσε ποτέ.
                ld   e,(ix+PL_X)
                ld   d,(ix+PL_X+1)
                ld   h,b
                ld   l,c                ; HL = x
                or   a
                sbc  hl,de              ; HL = x - PL_X
                bit  7,h
                jr   nz,pa_no           ; αριστερά της
                ld   a,h
                or   a
                jr   nz,pa_no           ; πάνω από 255 δεξιά της
                ld   a,l
                cp   (ix+PL_W)
                jr   nc,pa_no
                ld   a,(pa_y)
                sub  (ix+PL_Y)
                jr   c,pa_no            ; πάνω από αυτήν
                cp   (ix+PL_H)
                jr   nc,pa_no           ; κάτω από αυτήν
                scf
                ret
pa_no:          or   a
                ret

;---------------------------------------------------------------------
; plat_solid — ο κρίκος για το solid_at
;
;   ΣΤΕΡΕΗ ΜΟΝΟ ΑΠΟ ΠΑΝΩ, με τον ίδιο κανόνα που κρίνει τις μονόδρομες: η
;   βαρύτητα του ήρωα πρέπει να είναι PLAT_GRAV. Είναι ανελκυστήρας, όχι κουτί.
; IN:  BC = x, DE = y     OUT: CF=1 στερεό
; ΔΙΑΤΗΡΕΙ: BC, DE, IX   ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
plat_solid:     ld   a,(plat_n)
                or   a
                ret  z
                ld   a,(hero_g)
                cp   PLAT_GRAV
                jr   nz,ps_no
                jp   plat_at
ps_no:          or   a
                ret

plat_n          db   0                  ; πόσες πλατφόρμες στην αίθουσα
plat_last       dw   0                  ; ρολόι στο προηγούμενο βήμα

;---------------------------------------------------------------------
; plat_step — ένα πέρασμα: κίνηση κάθε πλατφόρμας, σε pixel
;
;   ΤΟ ΡΟΛΟΙ ΚΑΙ ΟΧΙ ΤΑ ΠΕΡΑΣΜΑΤΑ, όπως και η φόρτιση του πυργίσκου: ένα
;   πέρασμα κοστίζει 3 ως 7 vsync ανάλογα με το τι κάνει ο παίκτης, οπότε
;   πλατφόρμα που κινείται «ανά πέρασμα» θα επιτάχυνε μόλις έτρεχε — δηλαδή ο
;   γρίφος θα άλλαζε ανάλογα με το πώς περπατάς.
;
;   Η ταχύτητα είναι pixel ΑΝΑ ΔΕΥΤΕΡΟΛΕΠΤΟ και το ρολόι μετράει 1/300, οπότε
;   συσσωρεύουμε speed x παλμούς και βγάζουμε ένα pixel κάθε 300.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_step:      ld   a,(plat_n)
                or   a
                ret  z
                call clock_now          ; HL = τώρα
                ld   de,(plat_last)
                ld   (plat_last),hl
                or   a
                sbc  hl,de              ; HL = παλμοί από το προηγούμενο βήμα
                bit  7,h
                jr   z,ps_dtok
                ld   hl,0               ; γύρισε το ρολόι: χάσε ένα βήμα
ps_dtok:        ld   (pl_dt),hl
                ld   ix,plat_tab
                ld   a,(plat_n)
                ld   b,a
pst_lp:          push bc
                call ps_one
                pop  bc
                push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                djnz pst_lp
                ret

; --- μία πλατφόρμα ---------------------------------------------------
ps_one:         bit  0,(ix+PL_FLG)      ; PLF_MOVE
                ret  z

                ld   l,(ix+PL_WAIT)     ; σταματημένη στο άκρο;
                ld   h,(ix+PL_WAIT+1)
                ld   a,h
                or   l
                jr   z,ps_move
                ld   de,(pl_dt)
                or   a
                sbc  hl,de
                jr   nc,ps_wset
                ld   hl,0
ps_wset:        ld   (ix+PL_WAIT),l
                ld   (ix+PL_WAIT+1),h
                ret

                ; ACC += ταχύτητα x παλμοί
ps_move:        ld   a,(ix+PL_SPD)
                ld   de,(pl_dt)
                call pl_mul             ; HL = A * DE
                ld   e,(ix+PL_ACC)
                ld   d,(ix+PL_ACC+1)
                add  hl,de
                ld   (ix+PL_ACC),l
                ld   (ix+PL_ACC+1),h

                ; ...και ένα pixel ανά 300
ps_pix:         ld   l,(ix+PL_ACC)
                ld   h,(ix+PL_ACC+1)
                ld   de,300
                or   a
                sbc  hl,de
                ret  c                  ; λιγότερα από 300: τέλος
                ld   (ix+PL_ACC),l
                ld   (ix+PL_ACC+1),h
                call ps_1px
                ld   l,(ix+PL_WAIT)     ; έφτασε σε άκρο μέσα στο βήμα;
                ld   h,(ix+PL_WAIT+1)
                ld   a,h
                or   l
                jr   z,ps_pix
                xor  a                  ; ναι: ξέχνα ό,τι περίσσεψε
                ld   (ix+PL_ACC),a
                ld   (ix+PL_ACC+1),a
                ret

;---------------------------------------------------------------------
; ps_1px — ένα pixel, ΜΑΖΙ με ό,τι στέκεται πάνω της
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
ps_1px:         call ps_dir             ; D = dx, E = dy (προσημασμένα)
                ld   (pl_dx),de
                call ps_riding          ; ΠΡΙΝ κουνηθεί: μετά το έδαφος έφυγε
                ld   a,0
                jr   nc,ps_nride
                inc  a
ps_nride:       ld   (pl_ride),a

                ld   l,(ix+PL_X)        ; x += dx
                ld   h,(ix+PL_X+1)
                ld   a,(pl_dx)
                ld   e,a
                call sign_ext
                add  hl,de
                ld   (ix+PL_X),l
                ld   (ix+PL_X+1),h
                ld   a,(pl_dy)          ; y += dy
                add  a,(ix+PL_Y)
                ld   (ix+PL_Y),a

                ld   a,(pl_ride)
                or   a
                call nz,ps_carry
                jp   ps_ends

;---------------------------------------------------------------------
; ps_carry — ο ήρωας ταξιδεύει μαζί της
;
;   ΤΟΝ ΚΟΥΒΑΛΑΕΙ, ΑΛΛΑ ΔΕΝ ΤΟΝ ΧΩΝΕΙ ΣΕ ΤΟΙΧΟ: αν η νέα θέση είναι μέσα σε
;   υλικό, η πλατφόρμα γλιστράει από κάτω του. Προτιμότερο από ήρωα σφηνωμένο,
;   όπου το solid_at λέει «είσαι παντού» και η φυσική δεν έχει πού να τον βγάλει.
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
ps_carry:       ld   hl,(hero_x)
                push hl
                ld   a,(hero_y)
                push af
                ld   a,(pl_dx)
                ld   e,a
                call sign_ext
                ld   hl,(hero_x)
                add  hl,de
                ld   (hero_x),hl
                ld   a,(pl_dy)
                ld   hl,hero_y
                add  a,(hl)
                ld   (hl),a

                ld   bc,(hero_x)        ; χώθηκε σε υλικό;
                ld   a,(hero_y)
                ld   e,a
                ld   d,0
                call solid_at
                jr   c,ps_undo
                ld   bc,(hero_x)
                ld   a,(hero_y)
                sub  4
                ld   e,a
                ld   d,0
                call solid_at
                jr   c,ps_undo
                pop  af
                pop  hl
                ret
ps_undo:        pop  af
                ld   (hero_y),a
                pop  hl
                ld   (hero_x),hl
                ret

;---------------------------------------------------------------------
; ps_riding — πατάει ο ήρωας ΑΥΤΗ την πλατφόρμα;
;
;   ΤΑ ΙΔΙΑ ΕΝΝΕΑ ΣΗΜΕΙΑ ΜΕ ΤΟ ΜΟΝΤΕΛΟ: πέλματα -FOOT_A/0/+FOOT_A, βάθος
;   FEET_B..FEET_B+2. Το βάθος είναι όσο ανέχεται και το stable(): ο ήρωας
;   ισορροπεί ως δύο pixel ΠΑΝΩ από το έδαφος, και με στενότερη ανίχνευση
;   στεκόταν ολοφάνερα πάνω της ενώ εκείνη έφευγε από κάτω του.
;
;   Με τη βαρύτητα PLAT_GRAV το off(g,a,b) είναι σκέτο (a,b), οπότε δεν
;   χρειάζεται πίνακας — και με κάθε άλλη φορά περνάς από μέσα της ούτως ή
;   άλλως, οπότε δεν κουβαλιέσαι.
; OUT: CF=1 πατάει     ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
ps_riding:      ld   a,(hero_g)
                cp   PLAT_GRAV
                jr   nz,pr_none
                ld   a,-FOOT_A
                ld   (pr_a),a
pr_acol:        ld   a,FEET_B
                ld   (pr_k),a
pr_krow:        ld   hl,(hero_x)
                ld   a,(pr_a)
                ld   e,a
                call sign_ext
                add  hl,de
                ld   b,h
                ld   c,l
                ld   a,(hero_y)
                ld   hl,pr_k
                add  a,(hl)
                ld   e,a
                ld   d,0
                call pa_one             ; μέσα στο ορθογώνιο της IX;
                ret  c
                ld   hl,pr_k
                inc  (hl)
                ld   a,(hl)
                cp   FEET_B+3
                jr   c,pr_krow
                ld   hl,pr_a
                ld   a,(hl)
                add  a,FOOT_A
                ld   (hl),a
                cp   FOOT_A+1
                jr   c,pr_acol
pr_none:        or   a
                ret

;---------------------------------------------------------------------
; ps_dir — η φορά της κίνησης: E = dx, D = dy, προσημασμένα -1/0/+1
;
;   ΤΟ E ΕΙΝΑΙ ΤΟ dx ΕΠΙΤΗΔΕΣ: ο καλών τα φυλάει με `ld (pl_dx),de`, που γράφει
;   ΠΡΩΤΑ το E. Με το dx στο D, μια οριζόντια πλατφόρμα κινούνταν κάθετα.
; ΑΛΛΟΙΩΝΕΙ: AF, DE, HL
;---------------------------------------------------------------------
ps_dir:         ld   l,(ix+PL_BX)
                ld   h,(ix+PL_BX+1)
                ld   e,(ix+PL_AX)
                ld   d,(ix+PL_AX+1)
                or   a
                sbc  hl,de
                call pl_sgn16
                ld   c,a                ; C = dx προσωρινά
                ld   a,(ix+PL_BY)
                sub  (ix+PL_AY)
                call pl_sgn8
                ld   d,a                ; D = dy
                ld   e,c                ; E = dx
                bit  1,(ix+PL_FLG)      ; PLF_BACK: ανάποδα
                ret  z
                ld   a,d
                neg
                ld   d,a
                ld   a,e
                neg
                ld   e,a
                ret

; --- πρόσημο του HL (16 bit) και του A (8 bit) -> A = -1/0/+1
pl_sgn16:       ld   a,h
                or   l
                ret  z
                bit  7,h
                ld   a,1
                ret  z
                ld   a,-1
                ret
pl_sgn8:        or   a
                ret  z
                bit  7,a
                ld   a,1
                ret  z
                ld   a,-1
                ret

;---------------------------------------------------------------------
; ps_ends — στα άκρα γυρίζει, και περιμένει PLAT_PAUSE
;
;   Η σύγκριση είναι ισότητα και όχι «πέρασε»: το βήμα είναι ακριβώς ένα pixel
;   και τα άκρα πέφτουν σε ακέραια κελιά.
; ΑΛΛΟΙΩΝΕΙ: AF, DE, HL
;---------------------------------------------------------------------
ps_ends:        ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   e,(ix+PL_BX)
                ld   d,(ix+PL_BX+1)
                or   a
                sbc  hl,de
                jr   nz,pe_a
                ld   a,(ix+PL_Y)
                cp   (ix+PL_BY)
                jr   nz,pe_a
                set  1,(ix+PL_FLG)      ; προς το A από δω και πέρα
                jr   pe_wait
pe_a:           ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   e,(ix+PL_AX)
                ld   d,(ix+PL_AX+1)
                or   a
                sbc  hl,de
                ret  nz
                ld   a,(ix+PL_Y)
                cp   (ix+PL_AY)
                ret  nz
                res  1,(ix+PL_FLG)
pe_wait:        ld   hl,PLAT_PAUSE
                ld   (ix+PL_WAIT),l
                ld   (ix+PL_WAIT+1),h
                ret

;---------------------------------------------------------------------
; pl_mul — HL = A * DE  (8x16 χωρίς πολλαπλασιαστή)
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
pl_mul:         ld   hl,0
                or   a
                ret  z
                ld   b,8
pm_lp:          rra
                jr   nc,pm_skip
                add  hl,de
pm_skip:        ex   de,hl
                add  hl,hl
                ex   de,hl
                djnz pm_lp
                ret

pl_dt           dw   0                  ; παλμοί αυτού του περάσματος
pl_dx           db   0                  ; φορά του τρέχοντος βήματος
pl_dy           db   0
pl_ride         db   0                  ; ο ήρωας πατούσε πριν το βήμα;
pr_a            db   0                  ; μετρητές του ps_riding
pr_k            db   0

;---------------------------------------------------------------------
; ΣΧΕΔΙΑΣΗ
;
; ΑΝΑ PIXEL ΚΑΙ ΟΧΙ ΑΝΑ BYTE. Στο MODE 1 ένα byte κρατά τέσσερα pixel και το
; draw_tile γράφει ΣΤΟΙΧΙΣΜΕΝΑ — η πλατφόρμα όμως στέκεται σε αυθαίρετο x, και
; τα pixel της πέφτουν στη μέση των bytes. Η εναλλακτική ήταν να κινείται ανά
; τέσσερα pixel· θα ήταν δέκα φορές φθηνότερη και θα έσπαγε τη συμφωνία με το
; μοντέλο και τον browser, που κινούνται ανά ένα.
;---------------------------------------------------------------------

;---------------------------------------------------------------------
; pl_pen — το pen του pixel (D = u, E = v) του πλακιδίου τύπου A
;
;   Τα πλακίδια είναι πακεταρισμένα MODE 1: 2 bytes ανά γραμμή, 4 pixel ανά
;   byte, τα δύο bits του pen μοιρασμένα στα δύο επίπεδα.
; OUT: A = pen 0..3      ΑΛΛΟΙΩΝΕΙ: AF, BC, HL
;---------------------------------------------------------------------
pl_pen:         ld   l,a                ; HL = tile_gfx + τύπος*16
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl
                push de
                ld   bc,tile_gfx
                add  hl,bc
                ld   a,e                ; + γραμμή*2
                add  a,a
                ld   c,a
                ld   b,0
                add  hl,bc
                ld   a,d                ; + (u >= 4 ; δεύτερο byte)
                cp   4
                jr   c,plp_first
                inc  hl
                sub  4
plp_first:       ld   c,a                ; C = θέση μέσα στο byte 0..3
                ld   a,(hl)
                pop  de
                ; ΤΟ ΞΕΠΑΚΕΤΑΡΙΣΜΑ: ίδιο με του spr_unpack. Τα δύο bits ενός
                ; pen κάθονται στα bits (3-c) και (7-c) του byte.
                ld   b,c
                inc  b
plp_rot:         rlca
                djnz plp_rot             ; φέρε το bit 7-c στη θέση 7... (c+1 φορές)
                ld   c,a
                and  #10                ; bit 4 = το ψηλό επίπεδο μετά τη στροφή
                jr   z,plp_hi0
                ld   a,2
                jr   plp_lo
plp_hi0:         xor  a
plp_lo:          bit  0,c
                ret  z
                inc  a
                ret

;---------------------------------------------------------------------
; px_put — ένα pixel: BC = x (0..319), A = y, (pl_pen_v) = pen
;   Έξω από την οθόνη αγνοείται σιωπηλά.
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
px_put:         cp   200
                ret  nc
                ld   d,a                ; D = y
                ld   a,b
                or   a
                jr   z,px_ok
                dec  a
                ret  nz                 ; x >= 512
                ld   a,c
                cp   LVL_COLS*LVL_CELL-256
                ret  nc                 ; x >= 320
px_ok:          ld   a,c
                and  3
                ld   (px_slot),a
                ld   h,b                ; στήλη byte = x >> 2
                ld   l,c
                srl  h
                rr   l
                srl  l
                ld   c,l
                ld   b,d
                call scr_addr
                push hl
                ld   a,(px_slot)
                ld   e,a
                ld   d,0
                ld   hl,spr_andtab
                add  hl,de
                ld   c,(hl)
                ld   a,(pl_pen_v)       ; pixtab[pen*4 + slot]
                add  a,a
                add  a,a
                ld   e,a
                ld   a,(px_slot)
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

;---------------------------------------------------------------------
; plat_save — φύλαξε ΠΟΥ ΕΙΝΑΙ ΤΩΡΑ, πριν κουνηθούν
;   Ίδιος λόγος με το arrow_save: το σβήσιμο θέλει την ΠΑΛΙΑ θέση αλλά πρέπει
;   να γίνει κολλητά στο νέο σχέδιο, αλλιώς η πλατφόρμα τρεμοπαίζει.
; ΑΛΛΟΙΩΝΕΙ: BC, DE, HL
;---------------------------------------------------------------------
plat_save:      ld   hl,plat_tab
                ld   de,plat_old
                ld   bc,PL_SIZE*PLAT_MAX
                ldir
                ret

;---------------------------------------------------------------------
; plat_erase — ΜΟΝΟ Η ΛΩΡΙΔΑ ΠΟΥ ΕΛΕΥΘΕΡΩΣΕ, όχι ολόκληρη η πλατφόρμα
;
;   ΓΙΑΤΙ ΟΧΙ ΟΛΟΚΛΗΡΗ: ανάμεσα στο σβήσιμο και τη σχεδίασή της μεσολαβεί το
;   draw_hero. Με ολόκληρο σβήσιμο η πλατφόρμα έλειπε από την οθόνη όσο κρατά
;   εκείνο, ΚΑΘΕ πέρασμα — αυτό ήταν το τρεμόπαιγμα. Δεν γίνεται να ζωγραφιστεί
;   πριν από τον ήρωα: εκείνος συνθέτει το φόντο του από τα δεδομένα της ΠΙΣΤΑΣ,
;   όπου η πλατφόρμα δεν υπάρχει, και θα την έσβηνε σε όλο του το ορθογώνιο.
;   Μένει ο άλλος δρόμος — να μη σβηστεί ποτέ το σώμα της. Σβήνεται μόνο η
;   λωρίδα που άφησε πίσω της (1 ως 2 pixel) και το υπόλοιπο ξαναγράφεται από
;   πάνω του.
;
;   Σε ακίνητη πλατφόρμα δεν αγγίζει τίποτα: μηδέν λωρίδα, μηδέν κόστος.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_erase:     ld   a,(plat_n)
                or   a
                ret  z
                ld   ix,plat_old
                ld   b,a
pe_lp:          push bc
                call pe_one
                pop  bc
                push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                djnz pe_lp
                ret

; --- μία πλατφόρμα: ό,τι είχε μελάνι και δεν θα το ξαναβάψει η νέα θέση
;
;   ΑΥΤΟ ΕΙΝΑΙ ΤΟ ΜΕΤΡΟ, όχι «η λωρίδα που ελευθέρωσε»: τα ΔΙΑΦΑΝΑ pixel της
;   πλατφόρμας (η αραιή κάτω ακμή της, και σχεδόν όλο το κελί του επιβάτη) δεν
;   ξαναγράφονται από τη σχεδίαση, οπότε το προηγούμενο μελάνι έμενε μέσα στο
;   ΙΔΙΟ της το ορθογώνιο και μουτζούρωνε. Η λωρίδα δεν το έπιανε ποτέ.
pe_one:         ld   l,(ix+PL_X)        ; --- η παλιά της θέση
                ld   h,(ix+PL_X+1)
                ld   (pe_ox),hl
                ld   a,(ix+PL_Y)
                ld   (pe_oy),a
                ld   a,(ix+PL_W)
                ld   (pe_w),a
                ld   a,(ix+PL_H)
                ld   (pe_h),a
                call pe_body
                ld   (pe_ot),a
                ld   a,(ix+PL_RID)
                ld   (pe_or),a
                ld   a,(ix+PL_RDX)
                ld   (pe_ordx),a

                push ix                 ; --- η ΙΔΙΑ θέση στον ζωντανό πίνακα
                ld   bc,plat_tab-plat_old
                add  ix,bc
                ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   (pe_nx),hl
                ld   a,(ix+PL_Y)
                ld   (pe_ny),a
                call pe_body
                ld   (pe_nt),a
                ld   a,(ix+PL_RID)
                ld   (pe_nr),a
                ld   a,(ix+PL_RDX)
                ld   (pe_nrdx),a
                pop  ix

                ; ΑΚΙΝΗΤΗ ΚΑΙ ΙΔΙΑ: τίποτα να σβηστεί, μηδέν κόστος. Η μισή
                ; ώρα της πλατφόρμας περνά έτσι — κινείται ένα pixel κάθε δύο
                ; περάσματα περίπου.
                ld   hl,(pe_ox)
                ld   de,(pe_nx)
                or   a
                sbc  hl,de
                jr   nz,pe_scan
                ld   a,(pe_oy)
                ld   hl,pe_ny
                cp   (hl)
                jr   nz,pe_scan
                ld   a,(pe_ot)
                ld   hl,pe_nt
                cp   (hl)
                jr   nz,pe_scan
                ld   a,(pe_or)
                ld   hl,pe_nr
                cp   (hl)
                ret  z

pe_scan:        ld   a,(pe_ot)          ; --- το σώμα της
                ld   (pe_st),a
                ld   a,(pe_nt)
                ld   (pe_dt),a
                ld   hl,(pe_ox)
                ld   (pe_sx),hl
                ld   a,(pe_oy)
                ld   (pe_sy),a
                ld   hl,(pe_nx)
                ld   (pe_dx2),hl
                ld   a,(pe_ny)
                ld   (pe_dy2),a
                call pe_wipe

                ld   a,(pe_or)          ; --- ο επιβάτης, ένα κελί πιο πάνω
                or   a
                ret  z
                ld   (pe_st),a
                ld   a,(pe_nr)
                ld   (pe_dt),a
                ld   hl,(pe_ox)
                ld   a,(pe_ordx)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   (pe_sx),hl
                ld   a,(pe_oy)
                sub  LVL_CELL
                ld   (pe_sy),a
                ld   hl,(pe_nx)
                ld   a,(pe_nrdx)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   (pe_dx2),hl
                ld   a,(pe_ny)
                sub  LVL_CELL
                ld   (pe_dy2),a
                ld   a,LVL_CELL
                ld   (pe_w),a
                ld   (pe_h),a
                jp   pe_wipe

; --- pe_body: ποιο πλακίδιο δείχνει η εγγραφή στο IX (κινούμενη ή σταματημένη)
pe_body:        ld   a,T_PLATFORM
                bit  0,(ix+PL_FLG)
                ret  nz
                ld   a,T_PLATFORM_OFF
                ret

;---------------------------------------------------------------------
; pe_wipe — σβήνει το μελάνι του ΠΑΛΙΟΥ καρέ που το νέο δεν θα ξαναβάψει
;   IN: (pe_sx,pe_sy,pe_st) παλιό, (pe_dx2,pe_dy2,pe_dt) νέο, (pe_w,pe_h)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
pe_wipe:        xor  a
                ld   (pe_v),a
pew_row:        xor  a
                ld   (pe_u),a
pew_col:        ld   a,(pe_u)           ; είχε μελάνι εκεί το παλιό καρέ;
                and  7
                ld   d,a
                ld   a,(pe_v)
                and  7
                ld   e,a
                ld   a,(pe_st)
                call pl_pen
                or   a
                jp   z,pew_next
                ld   hl,(pe_sx)         ; το pixel σε συντεταγμένες οθόνης
                ld   a,(pe_u)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   (pe_px),hl
                ld   a,(pe_sy)
                ld   e,a
                ld   a,(pe_v)
                add  a,e
                ld   (pe_py),a
                ld   de,(pe_dx2)        ; μέσα στο ΝΕΟ ορθογώνιο;
                or   a
                sbc  hl,de
                jr   c,pew_paint
                ld   a,h
                or   a
                jr   nz,pew_paint
                ld   a,l
                ld   hl,pe_w
                cp   (hl)
                jr   nc,pew_paint
                and  7
                ld   d,a
                ld   a,(pe_py)
                ld   hl,pe_dy2
                sub  (hl)
                jr   c,pew_paint
                ld   hl,pe_h
                cp   (hl)
                jr   nc,pew_paint
                and  7
                ld   e,a
                ld   a,(pe_dt)          ; …και το νέο καρέ βάζει μελάνι εκεί;
                call pl_pen
                or   a
                jr   nz,pew_next        ; ναι: άσ' το, θα το γράψει εκείνο
pew_paint:      ld   bc,(pe_px)
                ld   a,(pe_py)
                call pe_bg
pew_next:       ld   hl,pe_u
                inc  (hl)
                ld   a,(hl)
                ld   hl,pe_w
                cp   (hl)
                jp   c,pew_col
                ld   hl,pe_v
                inc  (hl)
                ld   a,(hl)
                ld   hl,pe_h
                cp   (hl)
                jp   c,pew_row
                ret

;---------------------------------------------------------------------
; pe_bg — ένα pixel του φόντου, από το κελί που κάθεται από κάτω
;   IN: BC = x, A = y     ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
pe_bg:          ld   (pe_py),a
                ld   (pe_px),bc
                sub  LVL_Y0
                ret  c                  ; στο HUD δεν ακουμπάμε
                srl  a
                srl  a
                srl  a
                ld   b,a                ; B = γραμμή κελιού
                ld   hl,(pe_px)
                srl  h
                rr   l
                srl  l
                srl  l
                ld   c,l                ; C = στήλη κελιού
                call cell_rc            ; A = ο τύπος που κάθεται από κάτω
                push af
                ld   a,(pe_px)
                and  7
                ld   d,a                ; D = u μέσα στο κελί
                ld   a,(pe_py)
                and  7
                ld   e,a                ; E = v
                pop  af
                call pl_pen
                ld   (pl_pen_v),a
                ld   bc,(pe_px)
                ld   a,(pe_py)
                jp   px_put

;---------------------------------------------------------------------
; plat_draw — η πλατφόρμα και ο επιβάτης της, σε θέση PIXEL
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_draw:      ld   a,(plat_n)
                or   a
                ret  z
                ld   ix,plat_tab
                ld   b,a
pd_lp:          push bc
                call pd_one
                pop  bc
                push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                djnz pd_lp
                ret

pd_one:         ld   a,T_PLATFORM       ; ποιο πλακίδιο: κινούμενη ή σταματημένη
                bit  0,(ix+PL_FLG)
                jr   nz,pd_tile
                ld   a,T_PLATFORM_OFF
pd_tile:        ld   (pd_type),a
                xor  a
                ld   (pd_v),a
pd_row:         xor  a
                ld   (pd_u),a
pd_col:         call pd_pen             ; pen του (u mod 8, v mod 8)
                ld   (pl_pen_v),a
                or   a
                jr   z,pd_next          ; pen 0 = διαφανές
                ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   a,(pd_u)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   b,h
                ld   c,l
                ld   a,(pd_v)
                add  a,(ix+PL_Y)
                call px_put
pd_next:        ld   hl,pd_u
                inc  (hl)
                ld   a,(hl)
                cp   (ix+PL_W)
                jr   c,pd_col
                ld   hl,pd_v
                inc  (hl)
                ld   a,(hl)
                cp   (ix+PL_H)
                jp   c,pd_row
                ; --- Ο ΕΠΙΒΑΤΗΣ, ένα κελί από πάνω της.
                ;     Έφυγε από το πλέγμα στη φόρτωση ώστε να κινείται μαζί
                ;     της· χωρίς αυτό δούλευε κανονικά και ήταν ΑΟΡΑΤΟΣ.
                ld   a,(ix+PL_RID)
                or   a
                ret  z
                ld   (pd_type),a
                xor  a
                ld   (pd_v),a
prd_row:         xor  a
                ld   (pd_u),a
prd_col:         call pd_pen
                ld   (pl_pen_v),a
                or   a
                jr   z,prd_next
                ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   a,(ix+PL_RDX)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   a,(pd_u)
                ld   e,a
                add  hl,de
                ld   b,h
                ld   c,l
                ld   a,(ix+PL_Y)
                sub  LVL_CELL           ; μία σειρά πιο πάνω
                ld   e,a
                ld   a,(pd_v)
                add  a,e
                call px_put
prd_next:        ld   hl,pd_u
                inc  (hl)
                ld   a,(hl)
                cp   LVL_CELL
                jp   c,prd_col
                ld   hl,pd_v
                inc  (hl)
                ld   a,(hl)
                cp   LVL_CELL
                jr   c,prd_row
                ret

; --- pl_pen με τα ορίσματα στη σειρά που βολεύει το pd_one
;     IN: (pd_type) τύπος, (pd_u) u, (pd_v) v
pd_pen:         ld   a,(pd_u)
                and  7
                ld   d,a
                ld   a,(pd_v)
                and  7
                ld   e,a
                ld   a,(pd_type)
                jp   pl_pen

plat_old        ds   PL_SIZE*PLAT_MAX
pl_pen_v        db   0
px_slot         db   0
pa_y            db   0
pa_left         db   0
pe_ox           dw   0
pe_oy           db   0
pe_nx           dw   0
pe_ny           db   0
pe_w            db   0
pe_h            db   0
pe_ot           db   0
pe_nt           db   0
pe_or           db   0
pe_nr           db   0
pe_ordx         db   0
pe_nrdx         db   0
pe_sx           dw   0
pe_sy           db   0
pe_st           db   0
pe_dx2          dw   0
pe_dy2          db   0
pe_dt           db   0
pe_u            db   0
pe_v            db   0
pe_px           dw   0
pe_py           db   0
pd_type         db   0
pd_u            db   0
pd_v            db   0

;---------------------------------------------------------------------
; plat_toggle — ο διακόπτης του καναλιού A σταματά ή ξεκινά τις πλατφόρμες του
;
;   «ΑΝΟΙΧΤΟ» ΣΗΜΑΙΝΕΙ ΑΚΙΝΗΤΗ, με την ίδια λογική που σημαίνει τραβηγμένα
;   αγκάθια και σβηστό πυργίσκο: ο διακόπτης αφαιρεί τον κίνδυνο.
; IN: A = κανάλι     ΑΛΛΟΙΩΝΕΙ: AF, BC, HL, IX
;---------------------------------------------------------------------
plat_toggle:    ld   c,a
                ld   a,(plat_n)
                or   a
                ret  z
                ld   b,a
                ld   ix,plat_tab
pt_lp:          ld   a,(ix+PL_CH)
                or   a
                jr   z,pt_next          ; ακαλωδίωτη
                cp   c
                jr   nz,pt_next
                ld   a,(ix+PL_FLG)      ; γύρισε ΜΟΝΟ το bit κίνησης
                xor  PLF_MOVE
                ld   (ix+PL_FLG),a
pt_next:        push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                djnz pt_lp
                ret

;---------------------------------------------------------------------
; plat_touch — ο διακόπτης που ταξιδεύει πάνω στην πλατφόρμα
;
;   ΞΕΧΩΡΙΣΤΟΣ ΕΛΕΓΧΟΣ ΓΙΑΤΙ ΔΕΝ ΕΙΝΑΙ ΚΕΛΙ: το h_touch κοιτάζει το ΚΕΛΙ του
;   σώματος, και ο επιβάτης έχει φύγει από το πλέγμα ώστε να κινείται ανά pixel
;   μαζί της. Δική του ΑΚΜΗ, αλλιώς θα γύριζε πενήντα φορές το δευτερόλεπτο.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_touch:     ld   a,(plat_n)
                or   a
                ret  z
                ld   ix,plat_tab
                ld   a,(plat_n)
                ld   (pt_left),a
                ld   c,0                ; C = δείκτης πλατφόρμας
pu_lp:          ld   a,(ix+PL_RID)
                or   a
                jr   z,pu_next
                ld   b,(ix+PL_RDX)      ; το κουτί του επιβάτη
                ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                ld   e,b
                ld   d,0
                add  hl,de
                ld   e,l                ; DE = x του επιβάτη
                ld   d,h
                ld   hl,(hero_x)
                or   a
                sbc  hl,de
                bit  7,h
                jr   nz,pu_next
                ld   a,h
                or   a
                jr   nz,pu_next
                ld   a,l
                cp   LVL_CELL
                jr   nc,pu_next
                ld   a,(ix+PL_Y)
                sub  LVL_CELL
                ld   e,a
                ld   a,(hero_y)
                sub  e
                jr   c,pu_next
                cp   LVL_CELL
                jr   nc,pu_next
                jr   pu_on
pu_next:        inc  c
                push bc
                ld   bc,PL_SIZE
                add  ix,bc
                pop  bc
                ld   hl,pt_left
                dec  (hl)
                jr   nz,pu_lp
                ld   a,#FF              ; πάνω σε κανέναν
                ld   (pt_prev),a
                ret

pu_on:          ld   a,(pt_prev)        ; ΑΚΜΗ: ήδη πάνω του;
                cp   c
                ret  z
                ld   a,c
                ld   (pt_prev),a
                ld   a,(hero_g)         ; και από τη μεριά που κοιτάει
                ld   e,a
                ld   a,(ix+PL_RID)
                ld   l,a
                ld   h,0
                push de
                ld   de,tile_facing
                add  hl,de
                pop  de
                ld   a,(hl)
                add  a,4
                and  7
                cp   e
                ret  nz
                ; ΜΟΝΟ ΤΟ ΖΕΥΓΑΡΙ, ΟΧΙ ΤΟ sw_flip: εκείνο γράφει τον νέο τύπο
                ; σε ΚΕΛΙ, και ο επιβάτης έχει φύγει από το πλέγμα.
                ld   a,(ix+PL_RID)
                call sw_pair
                ret  nc
                ld   (ix+PL_RID),a
                ld   a,(ix+PL_RCH)
                jp   gate_toggle

pt_left         db   0
pt_prev         db   #FF                ; σε ποιον επιβάτη ήμασταν πάνω
