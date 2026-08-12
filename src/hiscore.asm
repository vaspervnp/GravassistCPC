;=====================================================================
;  GRAVASSIST — οι πέντε μεγαλύτερες βαθμολογίες, στη δισκέτα
;
;  ΠΡΩΤΗ ΕΓΓΡΑΦΗ ΣΕ ΔΙΣΚΟ που κάνει το παιχνίδι. Ως τώρα μόνο διάβαζε, οπότε
;  εδώ μπαίνουν και οι τρεις κλήσεις CAS_OUT_*.
;
;  Η ΛΟΓΙΚΗ ΕΙΝΑΙ ΧΩΡΙΣΤΑ ΑΠΟ ΤΟΝ ΔΙΣΚΟ επίτηδες: το hs_place και το
;  hs_insert δουλεύουν πάνω στον πίνακα στη μνήμη και δοκιμάζονται στον
;  προσομοιωτή. Ο δίσκος δεν δοκιμάζεται από εδώ — στο tools/z80run.py όλο
;  το jumpblock του firmware είναι RET.
;
;  Η δισκέτα μπορεί να είναι προστατευμένη ή γεμάτη. Η αποτυχία εγγραφής ΔΕΝ
;  είναι σφάλμα του παιχνιδιού: ο πίνακας μένει σωστός στη μνήμη για αυτή τη
;  συνεδρία και απλώς δεν επιβιώνει. Καμία διακοπή, κανένα μήνυμα λάθους.
;=====================================================================

CAS_OUT_OPEN    equ  #BC8C      ; HL=όνομα, B=μήκος, DE=buffer 2K
CAS_OUT_DIRECT  equ  #BC98      ; HL=δεδομένα, DE=μήκος, BC=exec, A=τύπος
CAS_OUT_CLOSE   equ  #BC8F
CAS_OUT_ABANDON equ  #BC92

HS_VERSION      equ  1
HS_ENTRY        equ  2+HISCORE_NAME     ; dw σκορ + τρία γράμματα
HS_HDR_SZ       equ  4                  ; υπογραφή + έκδοση
HS_BYTES        equ  HS_HDR_SZ+HISCORE_MAX*HS_ENTRY
AMSDOS_BINARY   equ  2

;---------------------------------------------------------------------
; hs_reset — άδειος πίνακας: πέντε μηδενικά με όνομα NUL
;
;   ΜΗΔΕΝ ΚΑΙ ΟΧΙ ΑΡΝΗΤΙΚΟ: το μηδέν είναι ήδη αδύνατο να το πετύχεις (το
;   παιχνίδι τελειώνει μόλις το σκορ γίνει αρνητικό), οπότε κάθε πραγματική
;   παρτίδα μπαίνει στον πίνακα — που είναι το σωστό για άδεια δισκέτα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_reset:       ld   ix,hs_table
                ld   b,HISCORE_MAX
hr_lp:          ld   (ix+0),0
                ld   (ix+1),0
                push bc
                push ix
                pop  de
                inc  de                 ; DE -> τα γράμματα της εγγραφής
                inc  de
                ld   hl,hs_nul
                ld   bc,HISCORE_NAME
                ldir
                pop  bc
                ld   de,HS_ENTRY
                add  ix,de
                djnz hr_lp
                ret

;---------------------------------------------------------------------
; hs_gt — CF=1 αν HL > DE, ΠΡΟΣΗΜΑΣΜΕΝΑ
;
;   Το sbc hl,de αφήνει carry για ΑΠΡΟΣΗΜΑ. Για προσημασμένα η απάντηση είναι
;   «πρόσημο XOR υπερχείλιση», και η υπερχείλιση διαβάζεται ΜΟΝΟ αμέσως μετά
;   το sbc — γι' αυτό το ld a,h (που δεν πειράζει flags) μπαίνει πρώτο.
;
; IN:  HL, DE      OUT: CF=1 αν HL > DE
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
hs_gt:          or   a
                sbc  hl,de
                ret  z                  ; ίσα: το sbc άφησε CF=0
                ld   a,h                ; κρατά S και P/V του sbc
                jp   po,hg_nov          ; P/V=0: καμία υπερχείλιση
                xor  #80                ; με υπερχείλιση το πρόσημο λέει ψέματα
hg_nov:         rla                     ; bit 7 -> CF· 1 = αρνητικό = HL < DE
                ccf
                ret

;---------------------------------------------------------------------
; hs_place — σε ποια θέση μπαίνει το σκορ HL;
; IN:  HL = σκορ
; OUT: CF=1 και A = δείκτης θέσης (0..HISCORE_MAX-1)· CF=0 δεν μπαίνει
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_place:       ld   (hs_score),hl
                ld   ix,hs_table
                ld   b,0
hp_lp:          ld   hl,(hs_score)
                ld   e,(ix+0)
                ld   d,(ix+1)
                call hs_gt
                jr   nc,hp_next
                ld   a,b
                scf
                ret
hp_next:        ld   de,HS_ENTRY
                add  ix,de
                inc  b
                ld   a,b
                cp   HISCORE_MAX
                jr   c,hp_lp
                or   a                  ; CF=0: δεν φτάνει για τον πίνακα
                ret

;---------------------------------------------------------------------
; hs_insert — βάζει το hs_score / hs_name στη θέση A, σπρώχνοντας κάτω
;
;   Η μετακίνηση γίνεται με LDDR από το ΤΕΛΟΣ: με LDIR προς τα εμπρός κάθε
;   εγγραφή θα έγραφε πάνω στην επόμενη πριν διαβαστεί, και ο πίνακας θα
;   γέμιζε με αντίγραφα της πρώτης.
;
; IN:  A = θέση, hs_score = σκορ, hs_name = τρία γράμματα
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_insert:      push af
                ; πόσες εγγραφές σπρώχνονται: (HISCORE_MAX-1) - θέση
                ld   b,a
                ld   a,HISCORE_MAX-1
                sub  b
                jr   z,hi_put           ; τελευταία θέση: τίποτα να σπρωχτεί
                ld   c,a                ; C = πλήθος εγγραφών
                ; BC = πλήθος bytes = εγγραφές x HS_ENTRY
                ld   hl,0
                ld   de,HS_ENTRY
hi_mul:         add  hl,de
                dec  c
                jr   nz,hi_mul
                ld   b,h
                ld   c,l
                ; HL = τελευταίο byte της ΠΗΓΗΣ, DE = του ΠΡΟΟΡΙΣΜΟΥ
                ld   hl,hs_table+(HISCORE_MAX-1)*HS_ENTRY-1
                ld   de,hs_table+HISCORE_MAX*HS_ENTRY-1
                lddr

hi_put:         pop  af
                ld   de,HS_ENTRY        ; IX -> η εγγραφή της θέσης A
                ld   b,a
                ld   hl,hs_table
                inc  b
hi_off:         dec  b
                jr   z,hi_got
                add  hl,de
                jr   hi_off
hi_got:         push hl
                pop  ix
                ld   de,(hs_score)
                ld   (ix+0),e
                ld   (ix+1),d
                push ix
                pop  de
                inc  de
                inc  de
                ld   hl,hs_name
                ld   bc,HISCORE_NAME
                ldir
                ret

;---------------------------------------------------------------------
; hs_load — διαβάζει το SCORES.BIN· ό,τι στραβώσει, άδειος πίνακας
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_load:        ld   hl,hs_fname
                ld   b,hs_fname_end-hs_fname
                ld   de,cas_buffer
                call CAS_IN_OPEN
                jr   nc,hl_bad
                ld   hl,hs_hdr
                call CAS_IN_DIRECT
                push af
                call CAS_IN_CLOSE
                pop  af
                jr   nc,hl_bad

                ld   hl,hs_hdr          ; υπογραφή 'GRH' + έκδοση
                ld   a,(hl)
                cp   'G'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   'R'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   'H'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   HS_VERSION
                ret  z
                ; ΛΑΘΟΣ Ή ΑΝΥΠΑΡΚΤΟ ΑΡΧΕΙΟ: άδειος πίνακας, χωρίς μήνυμα. Μια
                ; καινούρια δισκέτα δεν έχει SCORES.BIN και αυτό είναι το
                ; φυσιολογικό, όχι σφάλμα.
hl_bad:         jp   hs_reset

;---------------------------------------------------------------------
; hs_save — γράφει το SCORES.BIN
;
;   Ο buffer των 2 KB είναι η ΟΘΟΝΗ, όπως και στο διάβασμα των αιθουσών. Η
;   εγγραφή γίνεται στο τέλος της παρτίδας, ακριβώς πριν ξαναζωγραφιστεί το
;   μενού, οπότε το μόνο ορατό είναι ένα τρεμόπαιγμα.
;
;   ΑΠΟΤΥΧΙΑ ΔΕΝ ΕΙΝΑΙ ΣΦΑΛΜΑ: προστατευμένη ή γεμάτη δισκέτα σημαίνει απλώς
;   ότι ο πίνακας δεν επιβιώνει. Το CAS_OUT_ABANDON καθαρίζει το μισογραμμένο
;   αρχείο ώστε να μη μείνει σκουπίδι στον κατάλογο.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_save:        ld   hl,hs_fname
                ld   b,hs_fname_end-hs_fname
                ld   de,cas_buffer
                call CAS_OUT_OPEN
                ret  nc
                ld   hl,hs_hdr
                ld   de,HS_BYTES
                ld   bc,0               ; χωρίς διεύθυνση εκτέλεσης
                ld   a,AMSDOS_BINARY
                call CAS_OUT_DIRECT
                jr   nc,hv_bad
                jp   CAS_OUT_CLOSE
hv_bad:         jp   CAS_OUT_ABANDON

;---------------------------------------------------------------------
; hs_submit — το σκορ της παρτίδας στον πίνακα, αν φτάνει
; IN:  hs_name = τα τρία γράμματα (ή NUL)
; OUT: CF=1 αν μπήκε
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_submit:      ld   hl,(score)
                call hs_place
                ret  nc
                call hs_insert
                call hs_save
                scf
                ret

hs_nul:         db   "NUL"              ; όνομα όταν ο παίκτης δεν δώσει
hs_fname:       db   "SCORES.BIN"
hs_fname_end:

hs_score        dw   0                  ; το σκορ που κατατίθεται
hs_name         ds   HISCORE_NAME       ; τα γράμματά του

; ΚΕΦΑΛΗ ΚΑΙ ΠΙΝΑΚΑΣ ΣΥΝΕΧΟΜΕΝΑ, με αυτή τη σειρά: έτσι το αρχείο γράφεται
; και διαβάζεται ΕΠΙΤΟΠΟΥ, χωρίς δεύτερο buffer των 29 bytes και χωρίς
; αντιγραφή πριν από κάθε σώσιμο. Μην τα χωρίσεις.
hs_hdr:         db   'G','R','H',HS_VERSION
hs_table        ds   HISCORE_MAX*HS_ENTRY
