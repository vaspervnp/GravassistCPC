;=====================================================================
;  GRAVASSIST — σκορ
;
;  Ξεκινάς με SCORE_START και ΞΟΔΕΥΕΙΣ: κάθε βήμα και κάθε αλλαγή βαρύτητας
;  κοστίζει, κάθε πρόοδος πληρώνει. Το σκορ δεν μετράει χρόνο αλλά οικονομία
;  κινήσεων — που είναι αυτό που κρίνει ένα puzzle.
;
;  ΔΥΟ ΔΡΟΜΟΙ, ΟΧΙ ΕΝΑΣ:
;    score_award  θετικά — μετράνε ΜΟΝΟ την πρώτη φορά σε κάθε αίθουσα,
;                 αλλιώς ο παίκτης πατάει τον ίδιο διακόπτη σε βρόχο
;    score_cost   αρνητικά — μετράνε ΠΑΝΤΑ, αλλιώς το ξαναπερπάτημα μιας
;                 λυμένης αίθουσας είναι δωρεάν
;
;  ΟΛΕΣ ΟΙ ΔΗΜΟΣΙΕΣ ΕΙΣΟΔΟΙ ΔΙΑΤΗΡΟΥΝ BC, DE, HL, IX. Δεν είναι πολυτέλεια:
;  οι αγκίστρες μπαίνουν μέσα σε ρουτίνες που κρατούν τη διεύθυνση κελιού στο
;  HL και τη στήλη/γραμμή στο BC, και τις καλούν αμέσως μετά. Χωρίς αυτό ο
;  διακόπτης δεν άνοιγε τις πύλες και το κιβώτιο δεν πάταγε την πλάκα — δύο
;  σφάλματα που έφτασαν στον παίκτη.
;
;  Οι εσωτερικές sc_* χαλάνε ό,τι θέλουν· μόνο αυτές κάνουν δουλειά.
;
;  Οι τιμές ζουν στο tools/physics.py και βγαίνουν στο gamedefs.asm.
;=====================================================================

;---------------------------------------------------------------------
; score_reset — νέα παρτίδα
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
score_reset:    ld   hl,SCORE_START
                ld   (score),hl
                xor  a
                ld   (score+2),a
                ld   (score_dead),a
                ld   (score_shown+0),a  ; 0 is not a score the game can show,
                ld   (score_shown+1),a  ; so the HUD redraws on the first frame
                ld   (score_shown+2),a
                ld   hl,visit_map       ; καμία αίθουσα δεν έχει επισκεφθεί
                ld   de,visit_map+1
                ld   bc,VISIT_BYTES-1
                ld   (hl),0
                ldir
                ret

;---------------------------------------------------------------------
; score_add — προσθέτει το ΠΡΟΣΗΜΑΣΜΕΝΟ A στο σκορ
;
;   Η επέκταση προσήμου γίνεται με rlca+sbc a,a: το bit 7 πάει στο carry και
;   το sbc a,a το απλώνει σε ολόκληρο byte (#FF ή #00). Το ίδιο το A έχει
;   ήδη φυλαχτεί στο E — το rlca το χαλάει.
;
; IN:  A = πόντοι, συμπλήρωμα 2
; ΑΛΛΟΙΩΝΕΙ: AF, DE, HL
;---------------------------------------------------------------------
sc_add:         ld   e,a
                rlca                    ; bit 7 -> CF
                sbc  a,a                ; #FF negative, #00 positive
                ld   d,a
                ld   b,a                ; and the same for the third byte
                ld   hl,(score)
                add  hl,de
                ld   (score),hl
                ld   a,(score+2)        ; ld a,(nn) leaves the carry alone
                adc  a,b
                ld   (score+2),a

                ; NEGATIVE = OVER. Not by zeroing the energy: the HUD would
                ; show an empty bar and the player would think the spikes did
                ; it. Bit 7 of the top byte is the sign of the 24-bit value.
                and  #80
                ret  z
                ld   a,1
                ld   (score_dead),a
                ret

;---------------------------------------------------------------------
; score_cost — αρνητικοί πόντοι· μετράνε ΠΑΝΤΑ
; IN:  A = πόντοι (συμπλήρωμα 2)
; ΑΛΛΟΙΩΝΕΙ: AF, DE, HL
;---------------------------------------------------------------------
score_cost:     push bc
                push de
                push hl
                push ix
                call sc_add
                pop  ix
                pop  hl
                pop  de
                pop  bc
                ret

;---------------------------------------------------------------------
; score_award — θετικοί πόντοι· ΜΟΝΟ στην πρώτη επίσκεψη της αίθουσας
; IN:  A = πόντοι
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
score_award:    push bc
                push de
                push hl
                push ix
                call sc_award
                pop  ix
                pop  hl
                pop  de
                pop  bc
                ret

sc_award:       ld   e,a
                ld   a,(room_scored)
                or   a
                ret  z                  ; ξαναμπήκες: τζάμπα δουλειά
                ld   a,e
                jp   sc_add

;---------------------------------------------------------------------
; score_awardn — το ίδιο, A φορές (για «ανά αλεξίπτωτο», «ανά κλειδί»)
; IN:  A = πλήθος, C = πόντοι ανά τεμάχιο
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
score_awardn:   push bc
                push de
                push hl
                push ix
                call sc_awardn
                pop  ix
                pop  hl
                pop  de
                pop  bc
                ret

sc_awardn:      or   a
                ret  z
                ld   b,a
san_lp:         push bc
                ld   a,c
                call sc_award
                pop  bc
                djnz san_lp
                ret

;---------------------------------------------------------------------
; visit_enter — μπήκαμε στην αίθουσα A· πρώτη φορά;
;
;   Θέτει το room_scored, που είναι η μοναδική πύλη για τα θετικά. Ο χάρτης
;   είναι ένα bit ανά αίθουσα και ζει όσο η παρτίδα: το ημερολόγιο αλλαγών
;   κρατά τι έγινε ΜΕΣΑ στην αίθουσα, αυτό κρατά αν την είδες ποτέ.
;
; IN:  A = αριθμός αίθουσας
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
visit_enter:    push bc
                push de
                push hl
                push af
                call visit_bit          ; HL -> byte, A = μάσκα
                ld   b,a
                and  (hl)
                ld   a,0                ; ΟΧΙ xor a: το and άφησε τα flags
                jr   nz,ve_old          ; που θέλουμε
                ld   a,b                ; πρώτη φορά: σημείωσέ τη
                or   (hl)
                ld   (hl),a             ; σημείωσέ τη
                ld   a,1
ve_old:         ld   (room_scored),a
                xor  a                  ; νέα αίθουσα, κανένα είδος πληρωμένο
                ld   (room_awarded),a
                pop  af
                pop  hl
                pop  de
                pop  bc
                ret

;---------------------------------------------------------------------
; visit_bit — η θέση της αίθουσας A στον χάρτη
; IN:  A = αριθμός αίθουσας
; OUT: HL -> byte του χάρτη, A = μάσκα του bit
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
visit_bit:      ld   c,a
                and  7
                inc  a
                ld   b,a
                ld   a,1
vb_sh:          dec  b
                jr   z,vb_got
                add  a,a
                jr   vb_sh
vb_got:         ld   b,a
                ld   a,c
                rrca
                rrca
                rrca
                and  VISIT_BYTES-1      ; VISIT_BYTES είναι δύναμη του 2
                ld   l,a
                ld   h,0
                ld   de,visit_map
                add  hl,de
                ld   a,b
                ret


;---------------------------------------------------------------------
; score_digits — the score as sign + six digits in score_txt
;
;   Fixed width on purpose: a score that shrinks from 1000 to 999 would leave
;   a stray character behind, and the HUD has nothing to erase it with.
;
;   TWENTY-FOUR BIT SUBTRACTION, because 100000 does not fit in HL. Each digit
;   is "subtract the divisor until it goes negative, then add one back" — the
;   same shape as the old 16-bit version, one byte wider.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
SCORE_NDIG      equ  6          ; ΟΧΙ 'SCORE_DIGITS': rasm is case-insensitive

scd_tab:        db   #A0,#86,#01        ; 100000
                db   #10,#27,#00        ;  10000
                db   #E8,#03,#00        ;   1000
                db   #64,#00,#00        ;    100
                db   #0A,#00,#00        ;     10

score_digits:   ld   hl,score
                ; falls through: the high score table formats other values
score_digits_at:
                ld   e,(hl)             ; HL -> a 24-bit value, little endian
                inc  hl
                ld   d,(hl)
                inc  hl
                ld   a,(hl)
                ld   (scd_acc),de       ; working copy, made positive below
                ld   (scd_acc+2),a
                and  #80
                jr   z,scd_pos
                call scd_negate
                ld   a,'-'
                jr   scd_sign
scd_pos:        ld   a,' '
scd_sign:       ld   (score_txt),a

                ld   ix,scd_tab
                ld   de,score_txt+1
                ld   a,SCORE_NDIG-1     ; the last digit is the remainder
                ld   (scd_n),a
                ; THE DIGIT LIVES IN C, NOT A. Wrapping the call in push af /
                ; pop af to save the count restored the carry too — the very
                ; flag scd_sub had just set — so the loop never ended.
scd_dig:        ld   c,'0'-1
scd_lp:         inc  c
                call scd_sub            ; acc -= (ix), CF=1 if it went under
                jr   nc,scd_lp
                ; C is ALREADY the digit: it is bumped BEFORE each subtraction,
                ; so after N tries it holds '0'+N-1, and N-1 is how many
                ; succeeded. Only the value needs the failed one put back.
                call scd_add
                ld   a,c
                ld   (de),a
                inc  de
                push de
                ld   de,3               ; next divisor
                add  ix,de
                pop  de
                ld   hl,scd_n
                dec  (hl)
                jr   nz,scd_dig

                ld   a,(scd_acc)        ; 0..9 left over
                add  a,'0'
                ld   (de),a
                ret

; scd_sub — acc -= (IX); CF=1 if the result went negative
scd_sub:        ld   hl,scd_acc
                ld   a,(hl)
                sub  (ix+0)
                ld   (hl),a
                inc  hl
                ld   a,(hl)
                sbc  a,(ix+1)
                ld   (hl),a
                inc  hl
                ld   a,(hl)
                sbc  a,(ix+2)
                ld   (hl),a
                ret

; scd_add — the inverse, to undo the one subtraction too many
scd_add:        ld   hl,scd_acc
                ld   a,(hl)
                add  a,(ix+0)
                ld   (hl),a
                inc  hl
                ld   a,(hl)
                adc  a,(ix+1)
                ld   (hl),a
                inc  hl
                ld   a,(hl)
                adc  a,(ix+2)
                ld   (hl),a
                ret

; scd_negate — two's complement of the 24-bit working copy
scd_negate:     ld   hl,scd_acc
                ld   b,3
                xor  a
                ld   c,a                ; C = 0, borrow chain starts clear
                scf
scn_lp:         ld   a,(hl)
                cpl
                adc  a,c
                ld   (hl),a
                inc  hl
                ld   c,0
                djnz scn_lp
                ret

scd_n           db   0
scd_acc         ds   3

;---------------------------------------------------------------------
; score_draw — το σκορ στη δεξιά άκρη του HUD
;
;   Κείμενο firmware και όχι πλακίδια: το HUD δεν έχει γραμματοσειρά για
;   ψηφία (γι' αυτό το inventory δείχνει εικονίδια), αλλά η γραμμή 1 είναι
;   κανονική γραμμή κειμένου και το menu_puts γράφει ήδη εκεί τα μηνύματα.
;
;   ΓΡΑΦΕΙ ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΞΕΙ: το TXT_OUTPUT είναι ακριβό και το σκορ αλλάζει
;   λίγες φορές το δευτερόλεπτο, όχι πενήντα.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
score_draw:     ld   hl,(score)         ; changed since the last redraw?
                ld   de,(score_shown)
                or   a
                sbc  hl,de
                jr   nz,scdr_go
                ld   a,(score+2)
                ld   hl,score_shown+2
                cp   (hl)
                ret  z
scdr_go:        ld   hl,(score)
                ld   (score_shown),hl
                ld   a,(score+2)
                ld   (score_shown+2),a

                call score_digits
                ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   h,SCORE_COL
                ld   l,1                ; η γραμμή του HUD
                ld   de,score_txt
                ld   b,1+SCORE_NDIG
                jp   menu_puts

; Είδη θετικών που ΕΠΑΝΑΛΑΜΒΑΝΟΝΤΑΙ: ο διακόπτης γυρίζει όσες φορές θες, η
; πλάκα πατιέται ξανά και ξανά. Χωρίς ένα bit ανά είδος, ο παίκτης στέκεται
; στην πρώτη αίθουσα και μαζεύει άπειρους πόντους. Τα κλειδιά και τα κιβώτια
; ΔΕΝ είναι εδώ: καταναλώνονται, οπότε δεν farmάρονται.
SC_GATE         equ  1
SC_SWITCH       equ  2
SC_LOCK         equ  4
SC_PLATE        equ  8
SC_EXIT         equ  16
SC_PARA         equ  32

;---------------------------------------------------------------------
; score_once — θετικοί πόντοι, ΜΙΑ φορά ανά αίθουσα ανά είδος
; IN:  A = πόντοι, B = μάσκα είδους (SC_*)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
score_once:     push bc
                push de
                push hl
                push ix
                call sc_once
                pop  ix
                pop  hl
                pop  de
                pop  bc
                ret

sc_once:        ld   e,a
                ld   a,(room_awarded)
                and  b
                ret  nz                 ; πληρώθηκε ήδη σε αυτή την αίθουσα
                ld   a,(room_awarded)
                or   b
                ld   (room_awarded),a
                ld   a,e
                jp   sc_award

;---------------------------------------------------------------------
; score_target — πόντοι όταν ένας στόχος καλωδίωσης ΑΝΟΙΓΕΙ
;
;   Η πύλη και το λουκέτο ανοίγουν από τον ίδιο κώδικα (gate_set/gate_toggle
;   μέσω του tgt_want), αλλά αξίζουν διαφορετικά. Ο νέος τύπος του κελιού
;   είναι το μόνο που τα ξεχωρίζει — και τα αγκάθια που τραβιούνται μέσα δεν
;   πληρώνουν καθόλου, γιατί δεν είναι πρόοδος αλλά ασφάλεια.
;
; IN:  A = ο ΝΕΟΣ τύπος του κελιού
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
score_target:   push bc
                push de
                push hl
                push ix
                call sc_target
                pop  ix
                pop  hl
                pop  de
                pop  bc
                ret

sc_target:      cp   T_GATE_OPEN
                jr   nz,st_lock
                ld   a,SCORE_GATE
                ld   b,SC_GATE
                jp   sc_once
st_lock:        cp   T_LOCK_OPEN
                ret  nz
                ld   a,SCORE_LOCK
                ld   b,SC_LOCK
                jp   sc_once

; ΟΧΙ στη δεξιά άκρη: εκεί κάθονται τα δύο βελάκια βαρύτητας, στα bytes
; 68-69 και 72-73 — δηλαδή στήλες κειμένου 35 και 37 (2 bytes ανά χαρακτήρα
; σε MODE 1). Το σκορ ζωγραφιζόταν από πάνω τους. Οι στήλες 30..34 είναι το
; τελευταίο ελεύθερο πεντάρι: το inventory τελειώνει στη 21 και τα βέλη
; αρχίζουν στην 35.
SCORE_COL       equ  30         ; seven characters: sign + six digits

; THREE BYTES, NOT TWO. Six digits do not fit in 16 bits (32767 is five), and
; more to the point a score that passed 32767 wrapped NEGATIVE — which this
; file reads as "you lost". A long game ended itself for doing well.
score           db   SCORE_START&255, SCORE_START>>8, 0
score_shown     db   0,0,0      ; τι δείχνει η οθόνη τώρα
score_dead      db   0          ; 1 = το σκορ βγήκε αρνητικό
room_scored     db   0          ; 1 = πρώτη επίσκεψη· η πύλη των θετικών
room_awarded    db   0          ; ποια είδη πληρώθηκαν ΣΕ ΑΥΤΗ την αίθουσα
score_txt       ds   1+SCORE_NDIG
visit_map       ds   VISIT_BYTES
