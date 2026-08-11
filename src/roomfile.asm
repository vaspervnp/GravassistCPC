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
; OUT: A = ΩΜΗ τιμή (0 αν δεν έχει δηλωθεί)
;      Τα χαμηλά 3 bits είναι η ταυτότητα/κανάλι, το bit 3 η σημαία «ανοίγει
;      μόνη της». Ο καλών κάνει το AND που του χρειάζεται.
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
                and  7                  ; ΜΟΝΟ η ταυτότητα: το bit 3 είναι η
                push hl                 ; σημαία «ανοίγει μόνη της»
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
gt_put:         push af                 ; το γύρισμα πάντα αλλάζει κάτι
                ld   a,1
                ld   (sfx_gatechg),a
                pop  af
                call cell_set
                push bc
                call draw_tile          ; φαίνεται αμέσως, χωρίς να περιμένει
                pop  bc                 ; ξαναζωγράφισμα όλης της αίθουσας
gt_next:        pop  hl
                jr   gt_lp

gt_chan         db 0

;---------------------------------------------------------------------
; lock_open_all — ανοίγει ΚΑΘΕ κλειδαριά με την ταυτότητα A
;
;   Ίδιο σχήμα με το gate_toggle: ο σύνδεσμος είναι ο ΑΡΙΘΜΟΣ, οπότε ένα
;   κλειδί ξεκλειδώνει όσες κλειδαριές μοιράζονται την ταυτότητά του, όπου κι
;   αν βρίσκονται μέσα στην αίθουσα.
;
;   Η ταυτότητα 0 σημαίνει ΑΚΑΛΩΔΙΩΤΗ κλειδαριά: ο καλών την έχει ήδη ανοίξει
;   μόνη της και εδώ γυρίζουμε αμέσως. Αλλιώς κάθε πίστα με πολλές απλές
;   κλειδαριές θα ξεκλείδωνε ολόκληρη με ένα κλειδί — η προεπιλογή θα άλλαζε
;   νόημα σε όποιον δεν καλωδίωσε τίποτα.
;
; IN:  A = ταυτότητα
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
lock_open_all:  or   a
                ret  z
                ld   (lo_id),a
                ld   hl,(room_attrs)
lo_lp:          ld   a,(hl)
                cp   #FF
                ret  z
                ld   c,a                ; C = στήλη (έτσι τα θέλουν τα
                inc  hl                 ; cell_addr και draw_tile)
                ld   b,(hl)             ; B = γραμμή
                inc  hl
                ld   a,(hl)
                inc  hl
                and  7
                push hl
                ld   hl,lo_id
                cp   (hl)
                jr   nz,lo_next

                push bc                 ; ίδια ταυτότητα: είναι κλειδαριά;
                call cell_addr
                pop  bc
                ld   a,(hl)
                cp   T_LOCK
                jr   nz,lo_next
                ld   a,T_LOCK_OPEN
                call cell_set
                push bc
                call draw_tile          ; φαίνεται αμέσως
                pop  bc
lo_next:        pop  hl
                jr   lo_lp

lo_id           db 0

;---------------------------------------------------------------------
; plate_step — οι πλάκες πίεσης κρατούν ανοιχτές τις πύλες τους
;
;   ΣΤΙΓΜΙΑΙΕΣ, σε αντίθεση με τον διακόπτη: η πύλη ανοίγει όσο η πλάκα
;   πατιέται και ξανακλείνει μόλις φύγεις. Το κιβώτιο είναι ο τρόπος να την
;   κρατήσεις πατημένη — γι' αυτό υπάρχει ο τύπος T_PLATE_DOWN.
;
;   Οι πύλες γράφονται ΜΟΝΟ όταν αλλάζει η κατάσταση του καναλιού: το
;   plate_prev κρατά μάσκα οκτώ καναλιών και συγκρίνεται με τη νέα. Αλλιώς
;   κάθε πλάκα θα ξανάγραφε τις πύλες της πενήντα φορές το δευτερόλεπτο.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
plate_step:     ld   bc,(hero_x)        ; ποιο κελί πατάει το ΣΩΜΑ
                ld   de,(hero_y)
                call cell_at
                ld   a,(cell_col)
                ld   (ps_bcol),a
                ld   a,(cell_row)
                ld   (ps_brow),a

                xor  a
                ld   (ps_mask),a
                ld   hl,(room_attrs)
ps_lp:          ld   a,(hl)
                cp   #FF
                jr   z,ps_done
                ld   c,a                ; στήλη
                inc  hl
                ld   b,(hl)             ; γραμμή
                inc  hl
                ld   a,(hl)             ; κανάλι
                inc  hl
                and  7
                ld   (ps_chan),a
                push hl

                push bc                 ; είναι πλάκα;
                call cell_addr
                pop  bc
                ld   a,(hl)
                cp   T_PLATE_DOWN
                jr   z,ps_hold          ; με κιβώτιο: πατημένη μόνη της
                cp   T_PLATE
                jr   nz,ps_next

                ld   a,(ps_bcol)        ; αλλιώς: την πατάει ο ήρωας;
                cp   c
                jr   nz,ps_next
                ld   a,(ps_brow)
                cp   b
                jr   nz,ps_next

ps_hold:        ld   a,(ps_chan)
                call ps_bit
                ld   hl,ps_mask
                or   (hl)
                ld   (hl),a

ps_next:        pop  hl
                jr   ps_lp

                ; Μόνο τα κανάλια που ΑΛΛΑΞΑΝ ξαναγράφουν πύλες.
ps_done:        ld   a,(ps_mask)
                ld   hl,plate_prev
                xor  (hl)
                ret  z                  ; τίποτα δεν άλλαξε
                ld   (ps_diff),a
                ld   a,(ps_mask)
                ld   (plate_prev),a

                xor  a
                ld   (ps_ch),a
ps_chlp:        ld   a,(ps_ch)
                call ps_bit
                ld   hl,ps_diff
                and  (hl)
                jr   z,ps_chnext
                ld   a,(ps_ch)
                call ps_bit
                ld   hl,ps_mask
                and  (hl)
                ld   c,0                ; Z = κλειστές, NZ = ανοιχτές
                jr   z,ps_set
                ld   c,1
ps_set:         ld   a,c                ; C=1 πατήθηκε, 0 ελευθερώθηκε
                or   a
                jr   z,ps_noplate
                push bc                 ; το gate_set θέλει το C
                ld   a,SFXID_PLATE
                call sfx_play
                pop  bc
ps_noplate:     ld   a,(ps_ch)
                call gate_set
ps_chnext:      ld   hl,ps_ch
                inc  (hl)
                ld   a,(hl)
                cp   ATTR_MAX
                jr   c,ps_chlp
                jp   sfx_gate           ; ΜΙΑ φορά, όχι μία ανά πύλη

; ps_bit — A = κανάλι (0..7) -> A = η μάσκα του bit του
; ΑΛΛΟΙΩΝΕΙ: AF, C
ps_bit:         and  7
                ld   c,a
                inc  c
                ld   a,1
psb_lp:         dec  c
                ret  z
                add  a,a
                jr   psb_lp

ps_bcol         db 0
ps_brow         db 0
ps_chan         db 0
ps_ch           db 0
ps_mask         db 0
ps_diff         db 0
plate_prev      db 0

;---------------------------------------------------------------------
; gate_set — βάζει ΟΛΕΣ τις πύλες του καναλιού A σε κατάσταση C
;   C = 1 ανοιχτές, C = 0 κλειστές. Ίδια σάρωση με το gate_toggle, αλλά με
;   επιβολή αντί για εναλλαγή: η πλάκα δεν «γυρίζει», ΚΡΑΤΑΕΙ.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
gate_set:       ld   (gs_chan),a
                ld   a,c
                ld   (gs_open),a
                ld   hl,(room_attrs)
gs_lp:          ld   a,(hl)
                cp   #FF
                ret  z
                ld   c,a
                inc  hl
                ld   b,(hl)
                inc  hl
                ld   a,(hl)
                inc  hl
                and  7
                push hl
                ld   hl,gs_chan
                cp   (hl)
                jr   nz,gs_next

                push bc
                call cell_addr
                pop  bc
                ld   a,(hl)
                cp   T_GATE
                jr   z,gs_isgate
                cp   T_GATE_OPEN
                jr   nz,gs_next
gs_isgate:      ld   (gs_cur),a         ; τι είναι ΤΩΡΑ η πύλη
                ld   a,(gs_open)
                or   a
                ld   a,T_GATE
                jr   z,gs_put
                ld   a,T_GATE_OPEN
gs_put:         push hl                 ; ίδια κατάσταση; τότε δεν «άνοιξε»
                ld   hl,gs_cur
                cp   (hl)
                pop  hl
                jr   z,gs_next
                push af
                ld   a,1
                ld   (sfx_gatechg),a
                pop  af
                call cell_set
                push bc
                call draw_tile
                pop  bc
gs_next:        pop  hl
                jr   gs_lp

gs_chan         db 0
gs_open         db 0
gs_cur          db 0

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
; trail_enter — ενημερώνει τη στοίβα διαδρομής μπαίνοντας στο δωμάτιο A
;
;   Πόρτα προς δωμάτιο ΤΗΣ ΣΤΟΙΒΑΣ = ανοιχτή (γυρνάς πίσω). Πόρτα προς δωμάτιο
;   που ΞΕΧΕΙΛΙΣΕ από τη στοίβα = μπλοκ. Πόρτα προς δωμάτιο που δεν έχεις δει
;   = πάντα ανοιχτή, προχωράς.
;
;   ΤΟ ΛΕΠΤΟ ΣΗΜΕΙΟ: σφραγίζονται μόνο όσα ΞΕΧΕΙΛΙΣΑΝ, όχι όσα απλώς λείπουν
;   από τη στοίβα. Γυρνώντας 6->5 το 6 φεύγει από τη στοίβα αλλά είναι ΜΠΡΟΣΤΑ
;   σου· αν το σφραγίζαμε, δύο δωμάτια θα κλείδωναν το ένα το άλλο μόλις
;   πηγαινοερχόσουν.
;
; IN:  A = δωμάτιο στο οποίο μπαίνεις, (from_room) = από πού
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
trail_enter:    ld   b,a                ; ψάξε το A μέσα στη στοίβα
                ld   hl,trail
                ld   c,0
te_find:        ld   a,(trail_n)
                cp   c
                jr   z,te_push          ; δεν είναι μέσα: προχωράς
                ld   a,(hl)
                cp   b
                jr   z,te_back
                inc  hl
                inc  c
                jr   te_find

                ; ΓΥΡΙΣΜΑ ΠΙΣΩ: η στοίβα ξετυλίγεται ως εκείνο το σημείο.
te_back:        ld   a,(trail_n)
                sub  c
                dec  a
                ld   (trail_n),a
                or   a
                ret  z
                ld   b,a                ; μετακίνησε τα υπόλοιπα στην αρχή
                ld   de,trail
                inc  hl                 ; HL -> μία θέση μετά το δωμάτιο
te_shift:       ld   a,(hl)
                ld   (de),a
                inc  hl
                inc  de
                djnz te_shift
                ret

                ; ΜΠΡΟΣΤΑ: το τρέχον δωμάτιο μπαίνει στην κορυφή.
te_push:        ld   a,(from_room)
                or   a
                ret  z                  ; πρώτη αίθουσα: δεν ήρθες από πουθενά
                call seal_clear         ; ξαναμπήκε στη στοίβα -> ξανανοίγει

                ; Σπρώξε τα υπάρχοντα μία θέση. Αντιγράφουμε ΟΛΕΣ τις θέσεις,
                ; ώστε ό,τι ξεχειλίζει να καταλήξει στην έξτρα θέση trail[MAX]
                ; και να μπορεί το te_full να το σφραγίσει.
                ld   hl,trail+TRAIL_MAX-1
                ld   de,trail+TRAIL_MAX
                ld   bc,TRAIL_MAX
                lddr
                ld   a,(from_room)
                ld   (trail),a

                ld   a,(trail_n)
                cp   TRAIL_MAX
                jr   nc,te_full
                inc  a
                ld   (trail_n),a
                ret

                ; Γεμάτη στοίβα: ό,τι ξεχείλισε σφραγίζεται.
te_full:        ld   a,(te_spill)
                or   a
                ret  z
                jp   seal_set

; Το byte που έπεσε έξω από τη στοίβα το κρατάει το lddr στην τελευταία θέση.
te_spill        equ trail+TRAIL_MAX

;---------------------------------------------------------------------
; seal_set / seal_clear / seal_test — bitmask 256 δωματίων (32 bytes)
;   Ο αριθμός δωματίου είναι ΕΝΑ byte στους πίνακες εξόδου, οπότε 256 είναι
;   ακριβώς όσα μπορούν να υπάρξουν — ο πίνακας δεν ξεχειλίζει ποτέ.
; IN:  A = δωμάτιο          OUT (seal_test): CF=1 αν είναι σφραγισμένο
; ΑΛΛΟΙΩΝΕΙ: AF, BC, HL
;---------------------------------------------------------------------
seal_set:       call seal_bit
                or   (hl)
                ld   (hl),a
                ret

seal_clear:     call seal_bit
                cpl
                and  (hl)
                ld   (hl),a
                ret

seal_test:      call seal_bit
                and  (hl)
                ret  z                  ; CF=0: δεν είναι σφραγισμένο
                scf
                ret

; Επιστρέφει HL = byte του bitmask, A = η μάσκα του bit.
seal_bit:       ld   b,a
                and  7
                inc  a
                ld   c,a
                ld   a,1
sb_shift:       dec  c
                jr   z,sb_done
                add  a,a
                jr   sb_shift
sb_done:        push af
                ld   a,b
                rrca                    ; /8 χωρίς carry-in: το B < 256
                rrca
                rrca
                and  #1F
                ld   l,a
                ld   h,0
                ld   de,sealed
                add  hl,de
                pop  af
                ret

;---------------------------------------------------------------------
; seal_doors — κάνει ΣΤΕΡΕΑ τα κελιά των πορτών που έχουν σφραγιστεί
;
;   Γράφει ΚΑΤΕΥΘΕΙΑΝ στο cell_buf και ΟΧΙ μέσω cell_set: η σφράγιση δεν
;   είναι αλλαγή του δωματίου αλλά της διαδρομής σου, και ξαναϋπολογίζεται σε
;   κάθε είσοδο. Στο ημερολόγιο θα ήταν μόνιμη — και ο κανόνας λέει ότι η
;   πόρτα ξανανοίγει αν το δωμάτιο ξαναμπεί στη στοίβα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
seal_doors:     ld   hl,(room_exits)
sd_lp:          ld   a,(hl)
                cp   #FF
                ret  z
                ld   c,a                ; στήλη
                inc  hl
                ld   b,(hl)             ; γραμμή
                inc  hl
                ld   a,(hl)             ; δωμάτιο προορισμού
                inc  hl
                inc  hl                 ; προσπέρασε τη σημαία
                push hl
                push bc
                call seal_test
                pop  bc
                jr   nc,sd_next
                call cell_addr
                ld   (hl),T_SOLID
sd_next:        pop  hl
                jr   sd_lp

;---------------------------------------------------------------------
set_fname:      db  "ROOMS"
set_digit0:     db  "0"
set_digit1:     db  "1"
                db  ".BIN"
set_fname_end:

room_attrs      dw  0                   ; ιδιότητες κελιών της αίθουσας
set_cur         db  0                   ; ποιο σετ είναι φορτωμένο (0 = κανένα)
; Η στοίβα διαδρομής έχει ΜΙΑ θέση παραπάνω: εκεί πέφτει ό,τι ξεχειλίζει και
; από εκεί το διαβάζει το te_full για να το σφραγίσει.
trail           ds  TRAIL_MAX+1
trail_n         db  0
sealed          ds  32                  ; bitmask 256 δωματίων
jr_count        db  0                   ; πόσες εγγραφές έχει το ημερολόγιο
