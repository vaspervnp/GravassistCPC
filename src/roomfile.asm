;=====================================================================
;  GRAVASSIST — σετ αιθουσών από δισκέτα
;
;  Οι αίθουσες δεν ζουν πια μέσα στο MAIN.BIN. Ασυμπίεστες κοστίζουν 960
;  bytes η καθεμία και χωρούσαν μόλις ~10 συνολικά. Τώρα είναι RLE μέσα σε
;  αρχεία ROOMSnn.BIN, ένα σετ των 40, και το σετ μένει ΟΛΟΚΛΗΡΟ στη μνήμη:
;  τα περάσματα από πόρτα σε πόρτα μέσα στο σετ δεν αγγίζουν τον δίσκο.
;
;  Μορφή αρχείου: tools/roomfile.py — εκεί είναι η πηγή αλήθειας και εκεί
;  ελέγχεται ότι κάθε σετ χωράει στον set_buf.
;=====================================================================

CAS_IN_OPEN     equ  #BC77      ; HL=όνομα, B=μήκος, DE=buffer 2K
                                ;   OUT: CF=1 εντάξει
CAS_IN_DIRECT   equ  #BC83      ; HL=διεύθυνση φόρτωσης· OUT: CF=1 εντάξει
CAS_IN_CLOSE    equ  #BC7A

; Το AMSDOS θέλει buffer 2 KB για να διαβάσει. Δεν του δίνουμε δική του
; μνήμη — δανειζόμαστε τα πρώτα 2 KB της ΟΘΟΝΗΣ. Η φόρτωση σετ γίνεται μόνο
; όταν αλλάζει σετ και αμέσως μετά ξαναζωγραφίζεται όλο το δωμάτιο, οπότε το
; μόνο ορατό είναι ένα τρεμόπαιγμα. 2 KB είναι ακριβώς όσα ΔΕΝ περισσεύουν
; κάτω από το #B100.
CAS_BUFFER      equ  #C000

;---------------------------------------------------------------------
; rle_unpack — ξεδιπλώνει ζεύγη (πλήθος, τύπος) σε LVL_CELLS bytes
;
;   Το πλήθος είναι ένα byte, άρα ποτέ 0 και ποτέ >255· ο κωδικοποιητής της
;   tools/roomfile.py σπάει τις μεγάλες σειρές. Πλήθος 0 θα έκανε το djnz να
;   γράψει 256 bytes — γι' αυτό το roomfile.py κάνει assert στο round-trip.
;
; IN:  IX = πηγή RLE, DE = προορισμός
; OUT: DE = μετά το τελευταίο byte
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL, IX
;---------------------------------------------------------------------
rle_unpack:     ld   hl,LVL_CELLS       ; πόσα κελιά μένουν
ru_pair:        ld   a,h
                or   l
                ret  z
                ld   c,(ix+0)           ; πλήθος
                ld   a,(ix+1)           ; τύπος
                inc  ix
                inc  ix
                ld   b,0
                or   a                  ; CF=0 για το sbc· το A μένει ο τύπος
                sbc  hl,bc
                ld   b,c                ; B = πλήθος για το djnz
ru_fill:        ld   (de),a
                inc  de
                djnz ru_fill
                jr   ru_pair

;---------------------------------------------------------------------
; set_load — φορτώνει το ROOMSnn.BIN με δείκτη A (1..99) στον set_buf
;
; IN:  A = δείκτης σετ
; OUT: CF=1 επιτυχία· CF=0 αποτυχία (το σετ μένει ό,τι ήταν)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
set_load:       push af
                ld   b,-1               ; χώρισε σε δεκάδες/μονάδες
sl_tens:        inc  b
                sub  10
                jr   nc,sl_tens
                add  a,10
                add  a,'0'
                ld   (set_digit1),a     ; SMC: το όνομα αρχείου είναι ΔΕΔΟΜΕΝΑ,
                ld   a,b                ; όχι κώδικας — δύο ψηφία επιτόπου
                add  a,'0'
                ld   (set_digit0),a

                ld   hl,set_fname
                ld   b,set_fname_end-set_fname
                ld   de,CAS_BUFFER
                call CAS_IN_OPEN
                jr   nc,sl_fail
                ld   hl,set_buf
                call CAS_IN_DIRECT
                push af
                call CAS_IN_CLOSE
                pop  af
                jr   nc,sl_fail

                ld   hl,set_buf         ; υπογραφή 'GRS': ένα λάθος αρχείο θα
                ld   a,(hl)             ; γινόταν σκουπίδια-αίθουσες
                cp   'G'
                jr   nz,sl_fail
                inc  hl
                ld   a,(hl)
                cp   'R'
                jr   nz,sl_fail
                inc  hl
                ld   a,(hl)
                cp   'S'
                jr   nz,sl_fail

                pop  af
                ld   (set_cur),a        ; μόνο τώρα το σετ θεωρείται φορτωμένο
                scf
                ret

sl_fail:        pop  af
                xor  a
                ld   (set_cur),a        ; ξαναπροσπάθησε την επόμενη φορά
                ret                     ; CF=0

;---------------------------------------------------------------------
; room_find — βρίσκει την εγγραφή της αίθουσας A μέσα στο φορτωμένο σετ
;
; IN:  A = αριθμός αίθουσας
; OUT: CF=1 και HL = εγγραφή· CF=0 αν το σετ δεν την έχει
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
room_find:      ld   b,a
                ld   hl,set_buf+SET_NUMBERS
                ld   c,0
rf_lp:          ld   a,c
                cp   SET_ROOMS
                jr   nc,rf_no
                ld   a,(hl)
                cp   b
                jr   z,rf_got
                inc  hl
                inc  c
                jr   rf_lp

rf_no:          or   a                  ; CF=0
                ret

rf_got:         ld   a,c                ; offs[C] -> δύο bytes ανά θέση
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,set_buf+SET_OFFS
                add  hl,de
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                ld   hl,set_buf         ; τα offsets είναι από την ΑΡΧΗ του
                add  hl,de              ; αρχείου, όχι απόλυτες διευθύνσεις
                scf
                ret

;---------------------------------------------------------------------
; skip_tab — προσπερνά έναν πίνακα τετράδων ως το #FF
; IN/OUT: HL
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
skip_tab:       ld   a,(hl)
                inc  hl
                cp   #FF
                ret  z
                inc  hl
                inc  hl
                inc  hl
                jr   skip_tab

;---------------------------------------------------------------------
; skip_attr — το ίδιο για τον πίνακα ιδιοτήτων, που έχει ΤΡΙΑΔΕΣ
; IN/OUT: HL      ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
skip_attr:      ld   a,(hl)
                inc  hl
                cp   #FF
                ret  z
                inc  hl
                inc  hl
                jr   skip_attr

;---------------------------------------------------------------------
; cell_attr — η ιδιότητα του κελιού (B,C) = (col,row)
;
;   Κανάλι για διακόπτες και πόρτες, ταυτότητα για κλειδιά και κλειδαριές.
;   Ζει σε πίνακα και ΟΧΙ μέσα στο byte του κελιού: το byte είναι ο τύπος και
;   τον διαβάζει η φυσική σε κάθε pixel — μια μάσκα εκεί θα κόστιζε σε κάθε
;   έλεγχο στερεότητας. Εδώ ο πίνακας διαβάζεται μόνο όταν πατάς κάτι.
;
; IN:  B = col, C = row
; OUT: A = τιμή (0 αν δεν έχει δηλωθεί)
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
cell_attr:      ld   hl,(room_attrs)
ca_lp:          ld   a,(hl)
                cp   #FF
                jr   z,ca_none
                cp   b
                jr   nz,ca_next
                inc  hl
                ld   a,(hl)
                cp   c
                jr   nz,ca_next2
                inc  hl
                ld   a,(hl)             ; βρέθηκε
                ret
ca_next2:       dec  hl
ca_next:        inc  hl
                inc  hl
                inc  hl
                jr   ca_lp
ca_none:        xor  a
                ret

;---------------------------------------------------------------------
; gate_toggle — γυρίζει ΚΑΘΕ πόρτα του καναλιού A: κλειστή <-> ανοιχτή
;
;   Ένας διακόπτης οδηγεί όσες πόρτες θέλει ο σχεδιαστής — ο σύνδεσμος είναι
;   το κανάλι, όχι η γειτνίαση. Η ανοιγμένη πόρτα ΔΕΝ εξαφανίζεται: γίνεται
;   T_GATE_OPEN και φαίνεται, όπως και η ξεκλείδωτη κλειδαριά, αλλιώς ο
;   παίκτης πατάει κάτι και δεν βλέπει τι έγινε.
;
;   Περνά από το cell_set, οπότε η αλλαγή μπαίνει στο ημερολόγιο και επιβιώνει
;   όταν ξαναμπείς στην αίθουσα.
;
; IN:  A = κανάλι
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
gate_toggle:    ld   (gt_chan),a
                ld   hl,(room_attrs)
gt_lp:          ld   a,(hl)
                cp   #FF
                ret  z
                ld   c,a                ; C = στήλη — έτσι τη θέλουν το
                inc  hl                 ; cell_addr και το draw_tile
                ld   b,(hl)             ; B = γραμμή
                inc  hl
                ld   a,(hl)             ; κανάλι της εγγραφής
                inc  hl
                push hl
                ld   hl,gt_chan
                cp   (hl)
                jr   nz,gt_next

                push bc                 ; ίδιο κανάλι: είναι πόρτα;
                call cell_addr
                pop  bc
                ld   a,(hl)
                cp   T_GATE
                jr   nz,gt_notshut
                ld   a,T_GATE_OPEN
                jr   gt_put
gt_notshut:     cp   T_GATE_OPEN
                jr   nz,gt_next
                ld   a,T_GATE
gt_put:         call cell_set
                push bc
                call draw_tile          ; φαίνεται αμέσως, χωρίς να περιμένει
                pop  bc                 ; ξαναζωγράφισμα όλης της αίθουσας
gt_next:        pop  hl
                jr   gt_lp

gt_chan         db 0

;---------------------------------------------------------------------
; cell_set — γράφει τύπο σε κελί ΚΑΙ το καταγράφει στο ημερολόγιο
;
;   Χωρίς αυτό, ό,τι αλλάζει ο παίκτης (μαζεμένο κλειδί, ξεκλείδωτο λουκέτο,
;   μετακινημένο κιβώτιο) θα ξαναγύριζε στην αρχική του θέση μόλις έβγαινε
;   και ξανάμπαινε στην αίθουσα — γιατί το πλέγμα ξαναφτιάχνεται από το RLE.
;   Πριν τη συμπίεση, τα δεδομένα της αίθουσας άλλαζαν επιτόπου στη μνήμη και
;   το θέμα δεν υπήρχε. Η ενέργεια ειδικά θα γινόταν άπειρη: μπες, βγες,
;   ξαναμάζεψέ τη.
;
;   Το ημερολόγιο κρατά (αίθουσα, offset, τύπος). Δεύτερη αλλαγή στο ΙΔΙΟ
;   κελί ξαναγράφει την εγγραφή αντί να προσθέτει νέα, αλλιώς ένα κιβώτιο
;   που πέφτει θα το γέμιζε μόνο του.
;
; IN:  HL = δείκτης κελιού (μέσα στον cell_buf), A = τύπος
; ΑΛΛΟΙΩΝΕΙ: AF   (BC, DE, HL διατηρούνται)
;---------------------------------------------------------------------
cell_set:       ld   (hl),a
                push bc
                push de
                push hl
                ld   (js_type),a

                ld   de,cell_buf        ; offset = HL - cell_buf
                or   a
                sbc  hl,de
                ld   (js_off),hl

                ld   a,(jr_count)
                ld   b,a
                ld   hl,journal
                or   a
                jr   z,js_add           ; άδειο ημερολόγιο
js_scan:        ld   a,(cur_room)
                cp   (hl)
                jr   nz,js_next
                inc  hl
                ld   a,(js_off)
                cp   (hl)
                jr   nz,js_next2
                inc  hl
                ld   a,(js_off+1)
                cp   (hl)
                jr   nz,js_next3
                inc  hl
                jr   js_store           ; ίδιο κελί: ξαναγράψ' το
js_next3:       dec  hl
js_next2:       dec  hl
js_next:        inc  hl
                inc  hl
                inc  hl
                inc  hl
                djnz js_scan

js_add:         ld   a,(jr_count)
                cp   JOURNAL_MAX
                jr   nc,js_done         ; γεμάτο: η αλλαγή ισχύει τώρα αλλά
                inc  a                  ; δεν επιβιώνει της επιστροφής
                ld   (jr_count),a
                ld   a,(cur_room)
                ld   (hl),a
                inc  hl
                ld   a,(js_off)
                ld   (hl),a
                inc  hl
                ld   a,(js_off+1)
                ld   (hl),a
                inc  hl
js_store:       ld   a,(js_type)
                ld   (hl),a
js_done:        pop  hl
                pop  de
                pop  bc
                ret

js_off          dw 0
js_type         db 0

;---------------------------------------------------------------------
; jr_apply — ξαναπερνά στο φρέσκο πλέγμα ό,τι έχει αλλάξει σε αυτή την αίθουσα
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
jr_apply:       ld   a,(jr_count)
                or   a
                ret  z
                ld   b,a
                ld   hl,journal
ja_lp:          ld   a,(cur_room)
                cp   (hl)
                jr   nz,ja_next
                push bc
                inc  hl
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                inc  hl
                ld   a,(hl)             ; τύπος
                push hl
                ld   hl,cell_buf
                add  hl,de
                ld   (hl),a
                pop  hl
                inc  hl
                pop  bc
                djnz ja_lp
                ret
ja_next:        inc  hl
                inc  hl
                inc  hl
                inc  hl
                djnz ja_lp
                ret

;---------------------------------------------------------------------
set_fname:      db  "ROOMS"
set_digit0:     db  "0"
set_digit1:     db  "1"
                db  ".BIN"
set_fname_end:

room_attrs      dw  0                   ; ιδιότητες κελιών της αίθουσας
set_cur         db  0                   ; ποιο σετ είναι φορτωμένο (0 = κανένα)
jr_count        db  0                   ; πόσες εγγραφές έχει το ημερολόγιο
