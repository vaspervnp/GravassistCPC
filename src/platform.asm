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
; ΣΤΕΡΕΗ ΑΠΟ ΠΑΝΤΟΥ, ΣΑΝ ΤΟΙΧΟΣ: πατάς πάνω της με όποια φορά κι αν έχεις, και
; σε κουβαλάει. Ήταν μονόδρομη — στερεή μόνο από πάνω — και αυτό την έκανε
; ανελκυστήρα ενός άξονα.
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
;   ΣΤΕΡΕΗ ΑΠΟ ΠΑΝΤΟΥ, ΣΑΝ ΤΟΙΧΟΣ. Ήταν μονόδρομη — στερεή μόνο με βαρύτητα
;   PLAT_GRAV — και αυτό την έκανε ανελκυστήρα ενός άξονα: ανάποδα ο ήρωας την
;   περνούσε σαν να μην υπήρχε, ενώ ο τοίχος δίπλα της γινόταν πάτωμα.
; IN:  BC = x, DE = y     OUT: CF=1 στερεό
; ΔΙΑΤΗΡΕΙ: BC, DE, IX   ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
plat_solid:     ld   a,(plat_n)
                or   a
                ret  z
                jp   plat_at

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

                ; ...και ένα ΒΗΜΑ ανά PLAT_TICK. Οριζόντια το βήμα είναι 4
                ; pixel (ένα byte του MODE 1) και το κατώφλι τετραπλάσιο, ώστε
                ; η ταχύτητα να βγαίνει η ίδια.
                call ps_dir
                ld   a,e
                or   a
                ld   hl,PLAT_TICK
                jr   z,ps_thr
                ld   hl,PLAT_TICK_X
ps_thr:         ld   (pl_thr),hl
ps_pix:         ld   l,(ix+PL_ACC)
                ld   h,(ix+PL_ACC+1)
                ld   de,(pl_thr)
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
ps_1px:         call ps_dir             ; E = dx, D = dy (προσημασμένα)
                ld   a,e                ; οριζόντια συνιστώσα -> βήμα 4 pixel
                or   a
                jr   z,ps_1st
                add  a,a
                add  a,a
                ld   e,a
                ld   a,d
                add  a,a
                add  a,a
                ld   d,a
ps_1st:         ld   (pl_dx),de
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
;   ΜΕΣΑ ΑΠΟ ΤΟ h_point, ΟΧΙ ΜΕ ΠΡΟΣΘΕΣΗ: τώρα που είναι στερεή από παντού, ο
;   ήρωας μπορεί να πατάει και ανάποδα και πλάγια. Το h_point μετράει προς ΤΑ
;   ΔΙΚΑ ΤΟΥ πόδια, με τους ίδιους πίνακες που χρησιμοποιεί όλη η φυσική.
; OUT: CF=1 πατάει     ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
ps_riding:      ld   a,-FOOT_A
                ld   (pr_a),a
pr_acol:        ld   a,FEET_B
                ld   (pr_k),a
pr_krow:        ld   a,(pr_a)
                ld   hl,pr_k
                ld   b,(hl)
                call h_point            ; BC = x, DE = y στη φορά του ήρωα
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
; ΣΧΕΔΙΑΣΗ — ΑΝΑ BYTE, ΟΧΙ ΑΝΑ PIXEL
;
; Η ΜΕΤΡΗΣΗ ΠΟΥ ΤΟ ΕΠΙΒΑΛΕ: με κίνηση ανά pixel η πλατφόρμα στεκόταν σε
; αυθαίρετο x, τα pixel της έπεφταν στη μέση των bytes και το καθένα ήθελε
; read-modify-write. Το plat_draw κόστιζε ~150.000 κύκλους και το plat_erase
; ~175.000 — μαζί ΤΕΣΣΕΡΑ καρέ των 50 Hz ανά πέρασμα, δηλαδή η δέσμη την
; προλάβαινε πάντα μισοσχεδιασμένη. Αυτό ήταν το τρεμόπαιγμα, και ΔΕΝ
; διορθωνόταν με σειρά σχεδίασης: ήταν σκέτο κόστος.
;
; Με το x κλειδωμένο σε πολλαπλάσιο του 4 (PLAT_XSTEP, δες tools/physics.py) η
; πλατφόρμα κάθεται σε όριο byte και γράφεται με ΟΛΟΚΛΗΡΑ bytes, όπως το
; draw_tile. Το σώμα της είναι αδιαφανές, οπότε γράφεται σκέτο. Ο επιβάτης
; είναι διάφανος και συντίθεται με το φόντο μέσω μάσκας.
;---------------------------------------------------------------------

;---------------------------------------------------------------------
; pl_bcol — η στήλη byte της εγγραφής στο IX (x / 4)
; OUT: A = στήλη 0..79   ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
pl_bcol:        ld   l,(ix+PL_X)
                ld   h,(ix+PL_X+1)
                srl  h
                rr   l
                srl  l
                ld   a,l
                ret

;---------------------------------------------------------------------
; pl_bgbyte — το byte του ΦΟΝΤΟΥ (πλακίδιο της πίστας) σε μια θέση οθόνης
;   IN:  B = στήλη byte, C = γραμμή σάρωσης
;   OUT: A = το byte· 0 πάνω από το playfield (ζώνη HUD)
;   ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
pl_bgbyte:      ld   a,c
                sub  LVL_Y0
                jr   nc,pbg_in
                xor  a                  ; στο HUD δεν υπάρχει πλακίδιο
                ret
pbg_in:         ld   c,a                ; C = y μέσα στο πλέγμα
                and  7
                add  a,a
                ld   (pb_line),a        ; γραμμή μέσα στο πλακίδιο, x2 bytes
                ld   a,b
                and  1
                ld   (pb_half),a        ; αριστερό ή δεξί μισό του πλακιδίου
                srl  b                  ; στήλη byte -> στήλη κελιού
                ld   a,c
                srl  a
                srl  a
                srl  a
                ld   c,b
                ld   b,a                ; B = γραμμή, C = στήλη — έτσι τα θέλει
                ; ΤΟ ΙΔΙΟ ΚΕΛΙ ΞΑΝΑ; Ο επιβάτης είναι δύο bytes επί οκτώ γραμμές
                ; και σχεδόν όλα πέφτουν στο ίδιο κελί· η αναζήτηση κόστιζε τα
                ; δύο τρίτα της σχεδίασης.
                ld   a,(pb_cell)
                cp   c
                jr   nz,pbg_miss
                ld   a,(pb_cell+1)
                cp   b
                jr   nz,pbg_miss
                ld   hl,(pb_base)
                jr   pbg_got
pbg_miss:       ld   a,c
                ld   (pb_cell),a
                ld   a,b
                ld   (pb_cell+1),a
                call cell_rc            ; A = ο τύπος του κελιού
                ld   l,a
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl              ; τύπος * 16
                ld   de,tile_gfx
                add  hl,de
                ld   (pb_base),hl
pbg_got:
                ld   a,(pb_line)
                ld   e,a
                ld   d,0
                add  hl,de
                ld   a,(pb_half)
                ld   e,a
                add  hl,de
                ld   a,(hl)
                ret

;---------------------------------------------------------------------
; pl_mask — ποια bits του φόντου επιβιώνουν κάτω από ένα byte με μελάνι
;
;   ΣΤΟ MODE 1 ΤΑ ΔΥΟ BITS ΕΝΟΣ PEN ΕΙΝΑΙ ΧΩΡΙΣΤΑ: του pixel s κάθονται στα
;   bits (3-s) και (7-s). Διάφανο σημαίνει pen 0, δηλαδή ΚΑΙ ΤΑ ΔΥΟ μηδέν —
;   άρα ενώνουμε τα δύο επίπεδα σε ένα nibble, το απλώνουμε πάλι στα δύο, και
;   παίρνουμε το συμπλήρωμα.
; IN: A = byte μελανιού   OUT: A = μάσκα φόντου   ΑΛΛΟΙΩΝΕΙ: AF, C
;---------------------------------------------------------------------
pl_mask:        ld   c,a
                rrca
                rrca
                rrca
                rrca
                or   c
                and  #0F                ; ένα bit ανά pixel: «έχει μελάνι»
                ld   c,a
                rlca
                rlca
                rlca
                rlca
                or   c
                cpl
                ret

;---------------------------------------------------------------------
; plat_save — φωτογραφία των εγγραφών πριν το βήμα
;   Το plat_erase τη χρειάζεται: όταν τρέχει, ο πίνακας δείχνει ήδη τη ΝΕΑ θέση.
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
plat_save:      ld   hl,plat_tab
                ld   de,plat_old
                ld   bc,PL_SIZE*PLAT_MAX
                ldir
                ret

;---------------------------------------------------------------------
; plat_erase — τα bytes της ΠΑΛΙΑΣ θέσης που η νέα δεν θα ξαναγράψει
;
;   ΜΟΝΟ ΑΥΤΑ: το σώμα της δεν σβήνεται ποτέ, γιατί ανάμεσα στο σβήσιμο και τη
;   σχεδίαση μεσολαβεί το draw_hero — ό,τι λείπει εκεί, τρεμοπαίζει. Και δεν
;   γίνεται να ζωγραφιστεί πριν από τον ήρωα: εκείνος συνθέτει το φόντο του από
;   τα δεδομένα της ΠΙΣΤΑΣ, όπου η πλατφόρμα δεν υπάρχει.
;
;   Ακίνητη πλατφόρμα με αμετάβλητο επιβάτη δεν κοστίζει τίποτα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_erase:     call pb_forget
                ld   a,(plat_n)
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

pe_one:         call pl_bcol            ; --- η παλιά θέση
                ld   (pe_oc),a
                ld   a,(ix+PL_Y)
                ld   (pe_oy),a
                ld   a,(ix+PL_W)
                srl  a
                srl  a
                ld   (pe_bw),a          ; πλάτος σε bytes
                ld   a,(ix+PL_H)
                ld   (pe_bh),a
                ld   a,(ix+PL_RID)
                ld   (pe_or),a
                ld   a,(ix+PL_RDX)
                srl  a
                srl  a
                ld   (pe_ordx),a

                push ix                 ; --- η ΙΔΙΑ θέση στον ζωντανό πίνακα
                ld   bc,plat_tab-plat_old
                add  ix,bc
                call pl_bcol
                ld   (pe_nc),a
                ld   a,(ix+PL_Y)
                ld   (pe_ny),a
                ld   a,(ix+PL_RID)
                ld   (pe_nr),a
                ld   a,(ix+PL_RDX)
                srl  a
                srl  a
                ld   (pe_nrdx),a
                pop  ix

                ld   a,(pe_oc)          ; ίδια θέση; τότε τίποτα
                ld   hl,pe_nc
                cp   (hl)
                jr   nz,pe_go
                ld   a,(pe_oy)
                ld   hl,pe_ny
                cp   (hl)
                ret  z

pe_go:          ld   a,(pe_oc)          ; --- το σώμα
                ld   (pe_sc),a
                ld   a,(pe_oy)
                ld   (pe_sy),a
                ld   a,(pe_nc)
                ld   (pe_dc),a
                ld   a,(pe_ny)
                ld   (pe_dy),a
                call pe_wipe

                ld   a,(pe_or)          ; --- ο επιβάτης, ένα κελί πιο πάνω
                or   a
                ret  z
                ld   a,(pe_oc)
                ld   hl,pe_ordx
                add  a,(hl)
                ld   (pe_sc),a
                ld   a,(pe_oy)
                sub  LVL_CELL
                ld   (pe_sy),a
                ld   a,(pe_nc)
                ld   hl,pe_nrdx
                add  a,(hl)
                ld   (pe_dc),a
                ld   a,(pe_ny)
                sub  LVL_CELL
                ld   (pe_dy),a
                ld   a,LVL_CELL/4       ; 8 pixel = 2 bytes
                ld   (pe_bw),a
                ld   a,LVL_CELL
                ld   (pe_bh),a
                jp   pe_wipe

;---------------------------------------------------------------------
; pe_wipe — ξαναβάφει με το φόντο ό,τι από το (pe_sc, pe_sy) μένει έξω από το
;           (pe_dc, pe_dy). Ίδιο μέγεθος και τα δύο: (pe_bw) x (pe_bh).
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
pe_wipe:        ld   a,(pe_dc)          ; --- η λωρίδα κατά x
                ld   hl,pe_sc
                sub  (hl)
                ld   b,a                ; B = μετατόπιση σε bytes, με πρόσημο
                ld   a,(pe_bw)
                ld   c,a
                call pe_span            ; C = μήκος, B = απόσταση από την αρχή
                ld   a,c
                or   a
                jr   z,pew_vert
                ld   (pe_rw),a
                ld   a,(pe_bh)
                ld   (pe_rh),a
                ld   a,(pe_sc)
                add  a,b
                ld   (pe_rc),a
                ld   a,(pe_sy)
                ld   (pe_ry),a
                call pe_rect

pew_vert:       ld   a,(pe_dy)          ; --- η λωρίδα κατά y
                ld   hl,pe_sy
                sub  (hl)
                ld   b,a
                ld   a,(pe_bh)
                ld   c,a
                call pe_span
                ld   a,c
                or   a
                ret  z
                ld   (pe_rh),a
                ld   a,(pe_bw)
                ld   (pe_rw),a
                ld   a,(pe_sc)
                ld   (pe_rc),a
                ld   a,(pe_sy)
                add  a,b
                ld   (pe_ry),a
                jp   pe_rect

;---------------------------------------------------------------------
; pe_span — τι ελευθερώνει μια μετατόπιση σε έναν άξονα
;   IN:  B = μετατόπιση με πρόσημο, C = μέγεθος
;   OUT: B = απόσταση από την αρχή, C = μήκος (0 = τίποτα)
;---------------------------------------------------------------------
pe_span:        ld   a,b
                or   a
                jr   z,pes_none
                jp   m,pes_neg
                cp   c                  ; προς τα δεξιά/κάτω: από την αρχή
                jr   c,pes_pos
                ld   a,c
pes_pos:        ld   c,a
                ld   b,0
                ret
pes_neg:        neg                     ; προς τα αριστερά/πάνω: από το τέλος
                cp   c
                jr   c,pes_n2
                ld   a,c
pes_n2:         ld   b,a
                ld   a,c
                sub  b
                ld   c,b
                ld   b,a
                ret
pes_none:       ld   c,0
                ret

;---------------------------------------------------------------------
; pe_rect — βάφει με το φόντο το (pe_rc, pe_ry, pe_rw, pe_rh), σε bytes
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX
;---------------------------------------------------------------------
pe_rect:        xor  a
                ld   (pe_v),a
per_row:        xor  a
                ld   (pe_u),a
per_col:        ld   a,(pe_rc)
                ld   hl,pe_u
                add  a,(hl)
                ld   b,a                ; B = στήλη byte
                ld   a,(pe_ry)
                ld   hl,pe_v
                add  a,(hl)
                ld   c,a                ; C = γραμμή σάρωσης
                push bc
                call pl_bgbyte
                pop  bc
                push af
                ld   a,b
                ld   b,c
                ld   c,a                ; scr_addr: B = γραμμή, C = στήλη
                call scr_addr
                pop  af
                ld   (hl),a
                ld   hl,pe_u
                inc  (hl)
                ld   a,(hl)
                ld   hl,pe_rw
                cp   (hl)
                jr   c,per_col
                ld   hl,pe_v
                inc  (hl)
                ld   a,(hl)
                ld   hl,pe_rh
                cp   (hl)
                jr   c,per_row
                ret

;---------------------------------------------------------------------
; plat_bgline — η πλατφόρμα ΜΕΣΑ στο φόντο του ήρωα
;
;   ΤΟ draw_hero ΣΥΝΘΕΤΕΙ ΤΟ ΦΟΝΤΟ ΤΟΥ ΑΠΟ ΤΗΝ ΠΙΣΤΑ, όπου η πλατφόρμα δεν
;   υπάρχει. Όποιος ζωγράφιζε δεύτερος έσβηνε τον πρώτο: ο επιβάτης-διακόπτης
;   ζωγραφιζόταν μετά τον ήρωα και, εκεί που είναι διάφανος, έβαφε φόντο πάνω
;   στα πόδια του — η δέσμη τον έπιανε άλλοτε ζωγραφισμένο κι άλλοτε σβησμένο.
;   Μπαίνοντας εδώ, στο linebuf, ο ήρωας ζωγραφίζεται ΑΠΟ ΠΑΝΩ της μία φορά.
;
; IN: (dh_yy) γραμμή σάρωσης, (dh_c0) πρώτη στήλη byte, (dh_w) πλήθος bytes
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_bgline:    ld   a,(plat_n)
                or   a
                ret  z
                ld   (pbl_left),a
                ld   ix,plat_tab
pbl_lp:         call pbl_one
                ld   bc,PL_SIZE
                add  ix,bc
                ld   hl,pbl_left
                dec  (hl)
                jr   nz,pbl_lp
                ret

pbl_one:        ld   a,(dh_yy)          ; --- το σώμα, αδιαφανές
                sub  (ix+PL_Y)
                jr   c,pbl_rid
                ld   hl,pbl_v
                ld   (hl),a
                cp   (ix+PL_H)
                jr   nc,pbl_rid
                call pe_body
                ld   (pbl_type),a
                call pl_bcol
                ld   (pbl_col),a
                ld   a,(ix+PL_W)
                srl  a
                srl  a
                ld   (pbl_bw),a
                xor  a
                ld   (pbl_op),a
                call pbl_row

pbl_rid:        ld   a,(ix+PL_RID)      ; --- ο επιβάτης, με μάσκα
                or   a
                ret  z
                ld   (pbl_type),a
                ld   a,(ix+PL_Y)
                sub  LVL_CELL
                ld   c,a
                ld   a,(dh_yy)
                sub  c
                ret  c
                cp   LVL_CELL
                ret  nc
                ld   (pbl_v),a
                call pl_bcol
                ld   c,a
                ld   a,(ix+PL_RDX)
                srl  a
                srl  a
                add  a,c
                ld   (pbl_col),a
                ld   a,LVL_CELL/4
                ld   (pbl_bw),a
                ld   a,1
                ld   (pbl_op),a
                ; και πέφτει στο pbl_row

; --- pbl_row: μία γραμμή του (pbl_col, pbl_bw) μέσα στο linebuf
pbl_row:        xor  a
                ld   (pbl_u),a
pbr_lp:         ld   a,(pbl_col)
                ld   hl,pbl_u
                add  a,(hl)
                ld   c,a                ; C = στήλη byte
                ld   hl,dh_c0
                sub  (hl)
                jr   c,pbr_next         ; έξω από το παράθυρο του ήρωα
                ld   hl,dh_w
                cp   (hl)
                jr   nc,pbr_next
                ld   e,a                ; E = θέση μέσα στο linebuf
                ld   d,0
                ld   hl,linebuf
                add  hl,de
                ld   (pbl_dst),hl
                push hl
                ld   a,(pbl_v)          ; το byte μελανιού
                add  a,a
                ld   e,a
                ld   a,(pbl_bw)
                cp   LVL_CELL/4         ; ο επιβάτης: 2 bytes ανά γραμμή
                ld   a,(pbl_u)
                jr   z,pbr_half
                and  1                  ; το σώμα: πλακίδιο που επαναλαμβάνεται
pbr_half:       add  a,e
                ld   e,a
                ld   d,0
                ld   a,(pbl_type)
                call pl_trow
                ld   a,(hl)
                pop  hl
                ld   c,a
                ld   a,(pbl_op)
                or   a
                jr   z,pbr_put          ; αδιαφανές: σκέτη αντικατάσταση
                ld   a,c
                ld   (pbl_ink),a        ; ΤΟ pl_mask ΧΑΛΑΕΙ ΤΟ C
                call pl_mask
                and  (hl)               ; φόντο εκεί που είναι διάφανος
                ld   hl,pbl_ink
                or   (hl)
                ld   hl,(pbl_dst)
                ld   (hl),a
                jr   pbr_next
pbr_put:        ld   (hl),c
pbr_next:       ld   hl,pbl_u
                inc  (hl)
                ld   a,(hl)
                ld   hl,pbl_bw
                cp   (hl)
                jr   c,pbr_lp
                ret

; --- pd_split: πόσα bytes της γραμμής είναι πριν, μέσα και μετά το ορθογώνιο
;     που μόλις ζωγράφισε ο ήρωας.
;     ΑΝΑ ΓΡΑΜΜΗ ΚΑΙ ΟΧΙ ΑΝΑ BYTE: ο ίδιος έλεγχος με κλήση σε κάθε byte
;     κόστιζε 13.000 κύκλους — περισσότερο από όλη την υπόλοιπη σχεδίαση.
; OUT: D = πριν, E = παράλειψη, (pd_after) = μετά
pd_split:       ld   a,(pd_bw)
                ld   d,a                ; προεπιλογή: όλα δικά μας
                ld   e,0
                xor  a
                ld   (pd_after),a
                ld   a,(pd_line)
                ld   hl,dh_top
                cp   (hl)
                ret  c                  ; η γραμμή είναι πάνω από τον ήρωα
                ld   hl,dh_y1
                cp   (hl)
                jr   z,pds_in
                ret  nc                 ; ή κάτω από αυτόν
pds_in:         ld   a,(dh_c0)
                ld   hl,pd_col
                sub  (hl)
                ld   c,a                ; C = αρχή του παραθύρου, προσημασμένη
                ld   a,(dh_w)
                add  a,c
                ld   b,a                ; B = τέλος του
                ld   a,c
                bit  7,a
                jr   z,pds_c1
                xor  a
pds_c1:         ld   hl,pd_bw
                cp   (hl)
                jr   c,pds_c2
                ld   a,(hl)
pds_c2:         ld   c,a
                ld   a,b
                bit  7,a
                jr   z,pds_h1
                xor  a
pds_h1:         ld   hl,pd_bw
                cp   (hl)
                jr   c,pds_h2
                ld   a,(hl)
pds_h2:         ld   b,a
                sub  c
                ld   e,a
                ld   a,(pd_bw)
                sub  b
                ld   (pd_after),a
                ld   d,c
                ret

;---------------------------------------------------------------------
; pl_inhero — πέφτει το byte (B = στήλη, C = γραμμή) μέσα σε ό,τι μόλις
;             ζωγράφισε το draw_hero;
;   OUT: CF=1 μέσα. Εκεί ΔΕΝ ξαναγράφουμε: το plat_bgline το έβαλε ήδη στο
;   φόντο του και ο ήρωας κάθεται από πάνω· δεύτερη εγγραφή θα τον έσβηνε.
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
pl_inhero:      ld   a,b
                ld   hl,dh_c0
                sub  (hl)
                jr   c,pih_no
                ld   hl,dh_w
                cp   (hl)
                jr   nc,pih_no
                ld   a,c
                ld   hl,dh_top
                cp   (hl)
                jr   c,pih_no
                ld   hl,dh_y1
                cp   (hl)
                jr   z,pih_yes
                jr   nc,pih_no
pih_yes:        scf
                ret
pih_no:         or   a
                ret

;---------------------------------------------------------------------
; plat_draw — η πλατφόρμα και ο επιβάτης της, με ολόκληρα bytes
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plat_draw:      call pb_forget
                ld   a,(plat_n)
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

pd_one:         call pe_body            ; ποιο πλακίδιο: κινούμενη ή σταματημένη
                ld   (pd_type),a
                call pl_bcol
                ld   (pd_col),a
                ld   a,(ix+PL_W)
                srl  a
                srl  a
                ld   (pd_bw),a
                ld   a,(ix+PL_H)
                ld   (pd_bh),a
                ld   a,(ix+PL_Y)
                ld   (pd_y),a
                xor  a
                ld   (pd_v),a

                ; --- ΤΟ ΣΩΜΑ: αδιαφανές, σκέτη εγγραφή
pd_row:         ld   a,(pd_v)           ; τα δύο bytes αυτής της γραμμής
                and  7
                add  a,a
                ld   e,a
                ld   d,0
                ld   a,(pd_type)
                call pl_trow            ; HL -> tile_gfx + τύπος*16 + γραμμή
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                push bc
                ld   a,(pd_y)
                ld   e,a
                ld   a,(pd_v)
                add  a,e
                ld   (pd_line),a
                ld   b,a
                ld   a,(pd_col)
                ld   c,a
                ld   (pd_cc),a
                call scr_addr
                pop  bc
                push bc                 ; ΤΟ BC ΕΙΝΑΙ ΤΑ ΔΥΟ BYTES ΤΟΥ ΠΛΑΚΙΔΙΟΥ
                push hl                 ; και το HL η οθόνη: το pd_split τα χαλάει
                call pd_split           ; D = πριν, E = παράλειψη, (pd_after)
                pop  hl
                pop  bc
                ld   a,d
                or   a
                jr   z,pd_gap
pd_w1:          ld   (hl),c             ; ό,τι είναι αριστερά του ήρωα
                inc  hl
                ld   a,b
                ld   b,c
                ld   c,a
                dec  d
                jr   nz,pd_w1
pd_gap:         ld   a,e                ; ΤΟ ΚΟΜΜΑΤΙ ΤΟΥ ΗΡΩΑ ΔΕΝ ΞΑΝΑΓΡΑΦΕΤΑΙ:
                or   a                  ; το plat_bgline το έβαλε ήδη στο φόντο
                jr   z,pd_run2          ; του και εκείνος κάθεται από πάνω
                ld   d,0
                add  hl,de
                bit  0,e                ; μονός αριθμός -> τα μισά εναλλάσσονται
                jr   z,pd_run2
                ld   a,b
                ld   b,c
                ld   c,a
pd_run2:        ld   a,(pd_after)
                or   a
                jr   z,pd_erow
                ld   d,a
pd_w2:          ld   (hl),c             ; και ό,τι είναι δεξιά του
                inc  hl
                ld   a,b
                ld   b,c
                ld   c,a
                dec  d
                jr   nz,pd_w2
pd_erow:        ld   hl,pd_v
                inc  (hl)
                ld   a,(hl)
                ld   hl,pd_bh
                cp   (hl)
                jr   c,pd_row

                ; --- Ο ΕΠΙΒΑΤΗΣ: διάφανος, συντίθεται με το φόντο
                ld   a,(ix+PL_RID)
                or   a
                ret  z
                ld   (pd_type),a
                ld   a,(ix+PL_RDX)
                srl  a
                srl  a
                ld   hl,pd_col
                add  a,(hl)
                ld   (pd_col),a
                ld   a,(pd_y)
                sub  LVL_CELL
                ld   (pd_y),a
                xor  a
                ld   (pd_u),a
                ; ΣΤΗΛΗ-ΣΤΗΛΗ, ΟΧΙ ΓΡΑΜΜΗ-ΓΡΑΜΜΗ: με σταθερή στήλη οι οκτώ
                ; γραμμές πέφτουν στο ίδιο κελί και ο cache του pl_bgbyte
                ; αστοχεί μία φορά αντί για οκτώ.
prd_row:        xor  a
                ld   (pd_v),a
prd_col:        ld   a,(pd_v)           ; το byte μελανιού
                add  a,a
                ld   e,a
                ld   a,(pd_u)
                add  a,e
                ld   e,a
                ld   d,0
                ld   a,(pd_type)
                call pl_trow
                ld   a,(hl)
                ld   (pd_ink),a
                ld   a,(pd_y)           ; …το φόντο από κάτω του
                ld   hl,pd_v
                add  a,(hl)
                ld   c,a
                ld   a,(pd_col)
                ld   hl,pd_u
                add  a,(hl)
                ld   b,a
                push bc
                call pl_bgbyte
                ld   (pd_bg),a
                ld   a,(pd_ink)
                call pl_mask            ; ΧΑΛΑΕΙ ΤΟ C: το φόντο μένει σε μνήμη
                ld   hl,pd_bg
                and  (hl)               ; φόντο εκεί που είναι διάφανος
                ld   hl,pd_ink
                or   (hl)
                ld   (pd_ink),a
                pop  bc                 ; B = στήλη, C = γραμμή
                call pl_inhero          ; μέσα στον ήρωα; τότε δεν το αγγίζουμε
                jr   c,prd_next
                ld   a,b
                ld   b,c
                ld   c,a                ; scr_addr: B = γραμμή, C = στήλη
                call scr_addr
                ld   a,(pd_ink)
                ld   (hl),a
prd_next:
                ld   hl,pd_v
                inc  (hl)
                ld   a,(hl)
                cp   LVL_CELL
                jr   c,prd_col
                ld   hl,pd_u
                inc  (hl)
                ld   a,(hl)
                cp   LVL_CELL/4
                jr   c,prd_row
                ret

; --- pl_trow: HL = tile_gfx + A*16 + DE
pl_trow:        ld   l,a
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,hl
                add  hl,de
                ld   de,tile_gfx
                add  hl,de
                ret

; --- pb_forget: ξεχνά το κελί που θυμόταν το pl_bgbyte
;     ΥΠΟΧΡΕΩΤΙΚΟ ΣΕ ΚΑΘΕ ΚΛΗΣΗ: μια πύλη που άνοιξε ή ένας διακόπτης που
;     γύρισε αλλάζει τον τύπο του κελιού, και ο cache θα ζωγράφιζε τον παλιό.
;     Η στήλη #FF δεν υπάρχει (80 στήλες), οπότε δεν ταιριάζει ποτέ.
pb_forget:      ld   hl,#FFFF
                ld   (pb_cell),hl
                ret

; --- pe_body: ποιο πλακίδιο δείχνει η εγγραφή στο IX
pe_body:        ld   a,T_PLATFORM
                bit  0,(ix+PL_FLG)
                ret  nz
                ld   a,T_PLATFORM_OFF
                ret

plat_old        ds   PL_SIZE*PLAT_MAX
pa_y            db   0
pa_left         db   0
pb_line         db   0
pb_half         db   0
pb_cell         dw   #FFFF   ; τελευταίο (στήλη, γραμμή)
pb_base         dw   0
pe_oc           db   0
pe_oy           db   0
pe_nc           db   0
pe_ny           db   0
pe_bw           db   0
pe_bh           db   0
pe_or           db   0
pe_nr           db   0
pe_ordx         db   0
pe_nrdx         db   0
pe_sc           db   0
pe_sy           db   0
pe_dc           db   0
pe_dy           db   0
pe_u            db   0
pe_v            db   0
pe_rc           db   0
pe_ry           db   0
pe_rw           db   0
pe_rh           db   0
pd_type         db   0
pd_col          db   0
pd_bw           db   0
pd_bh           db   0
pd_y            db   0
pd_ink          db   0
pd_bg           db   0
pl_thr          dw   0
pd_u            db   0
pd_v            db   0
pbl_left        db   0
pbl_type        db   0
pbl_col         db   0
pbl_bw          db   0
pbl_v           db   0
pbl_u           db   0
pbl_op          db   0
pbl_ink         db   0
pbl_dst         dw   0
pd_line         db   0
pd_cc           db   0
pd_after        db   0

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
